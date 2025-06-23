from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import Optional
import structlog
import redis.asyncio as redis
import json

from src.models.user import User, UserProfile
from src.models.schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from src.utils.security import hash_password, verify_password, create_access_token, verify_access_token
from src.config.settings import get_settings

logger = structlog.get_logger()

class AuthService:
    """Authentication service for user registration and login"""
    
    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
    
    async def get_redis_client(self):
        """Get Redis client connection"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.settings.REDIS_URL)
        return self.redis_client
    
    async def register_user(self, user_data: UserCreate, db: AsyncSession, correlation_id: str) -> TokenResponse:
        """Register a new user"""
        try:
            # Check if user already exists
            existing_user = await self._get_user_by_email(user_data.email, db)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this email already exists"
                )
            
            # Check if phone number already exists
            existing_phone = await self._get_user_by_phone(user_data.phone, db)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this phone number already exists"
                )
            
            # Create new user
            hashed_password = hash_password(user_data.password)
            
            new_user = User(
                email=user_data.email,
                password_hash=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone=user_data.phone,
                role=user_data.role,
                is_active=True,
                is_verified=False
            )
            
            db.add(new_user)
            await db.flush()  # Flush to get the user ID
            
            # Create user profile
            user_profile = UserProfile(
                user_id=new_user.id,
                preferred_language="en"
            )
            
            db.add(user_profile)
            await db.commit()
            await db.refresh(new_user)
            
            # Create access token
            user_dict = new_user.to_dict()
            access_token = create_access_token(user_dict, correlation_id)
            
            # Store session in Redis
            await self._store_user_session(str(new_user.id), access_token, user_dict)
            
            logger.info(
                "User registered successfully",
                user_id=str(new_user.id),
                email=new_user.email,
                role=new_user.role,
                correlation_id=correlation_id
            )
            
            # Return response
            user_response = UserResponse(**user_dict)
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "User registration failed",
                error=str(e),
                email=user_data.email,
                correlation_id=correlation_id
            )
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )
    
    async def login_user(self, login_data: UserLogin, db: AsyncSession, correlation_id: str) -> TokenResponse:
        """Authenticate user and return token"""
        try:
            # Get user by email
            user = await self._get_user_by_email(login_data.email, db)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Check if user is active
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated"
                )
            
            # Verify password
            if not verify_password(login_data.password, user.password_hash):
                logger.warning(
                    "Login failed - invalid password",
                    user_id=str(user.id),
                    email=user.email,
                    correlation_id=correlation_id
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Create access token
            user_dict = user.to_dict()
            access_token = create_access_token(user_dict, correlation_id)
            
            # Store session in Redis
            await self._store_user_session(str(user.id), access_token, user_dict)
            
            logger.info(
                "User logged in successfully",
                user_id=str(user.id),
                email=user.email,
                role=user.role,
                correlation_id=correlation_id
            )
            
            # Return response
            user_response = UserResponse(**user_dict)
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "User login failed",
                error=str(e),
                email=login_data.email,
                correlation_id=correlation_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
    
    async def logout_user(self, user_id: str, token: str, correlation_id: str) -> dict:
        """Logout user and invalidate session"""
        try:
            # Remove session from Redis
            redis_client = await self.get_redis_client()
            session_key = f"{self.settings.REDIS_SESSION_PREFIX}{user_id}"
            await redis_client.delete(session_key)
            
            # Also add token to blacklist (optional - for extra security)
            blacklist_key = f"blacklist:{token}"
            await redis_client.setex(blacklist_key, 86400, "1")  # 24 hours
            
            logger.info(
                "User logged out successfully",
                user_id=user_id,
                correlation_id=correlation_id
            )
            
            return {"message": "Successfully logged out"}
            
        except Exception as e:
            logger.error(
                "User logout failed",
                error=str(e),
                user_id=user_id,
                correlation_id=correlation_id
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
    
    async def validate_token(self, token: str) -> Optional[dict]:
        """Validate JWT token and return user data"""
        try:
            # Verify JWT token
            token_data = verify_access_token(token)
            if not token_data:
                return None
            
            # Check if token is blacklisted
            redis_client = await self.get_redis_client()
            blacklist_key = f"blacklist:{token}"
            is_blacklisted = await redis_client.get(blacklist_key)
            if is_blacklisted:
                logger.warning("Blacklisted token used", user_id=token_data.get("user_id"))
                return None
            
            # Check if session exists in Redis
            user_id = token_data.get("user_id")
            session_key = f"{self.settings.REDIS_SESSION_PREFIX}{user_id}"
            session_data = await redis_client.get(session_key)
            
            if not session_data:
                logger.warning("Session not found in Redis", user_id=user_id)
                return None
            
            return token_data
            
        except Exception as e:
            logger.error("Token validation failed", error=str(e))
            return None
    
    async def get_current_user(self, token: str, db: AsyncSession) -> Optional[User]:
        """Get current user from token"""
        try:
            token_data = await self.validate_token(token)
            if not token_data:
                return None
            
            user_id = token_data.get("user_id")
            return await self._get_user_by_id(user_id, db)
            
        except Exception as e:
            logger.error("Get current user failed", error=str(e))
            return None
    
    async def _get_user_by_email(self, email: str, db: AsyncSession) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_user_by_phone(self, phone: str, db: AsyncSession) -> Optional[User]:
        """Get user by phone"""
        stmt = select(User).where(User.phone == phone)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_user_by_id(self, user_id: str, db: AsyncSession) -> Optional[User]:
        """Get user by ID"""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _store_user_session(self, user_id: str, token: str, user_data: dict):
        """Store user session in Redis"""
        try:
            redis_client = await self.get_redis_client()
            session_key = f"{self.settings.REDIS_SESSION_PREFIX}{user_id}"
            
            session_data = {
                "token": token,
                "user_data": user_data,
                "created_at": str(datetime.utcnow())
            }
            
            # Store session with expiration
            expire_seconds = self.settings.JWT_EXPIRE_HOURS * 3600
            await redis_client.setex(
                session_key,
                expire_seconds,
                json.dumps(session_data, default=str)
            )
            
        except Exception as e:
            logger.error("Failed to store user session", error=str(e), user_id=user_id)
            # Don't raise exception here as login should still work

# Global instance
auth_service = AuthService()