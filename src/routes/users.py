from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import structlog

from src.models.schemas import (
    UserResponse, 
    CompleteUserResponse, 
    UserProfileUpdate, 
    UserProfileResponse,
    ErrorResponse
)
from src.services.auth_service import auth_service
from src.config.database import get_db

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()

def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request"""
    return getattr(request.state, 'correlation_id', 'unknown')

async def get_current_user_dependency(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Dependency to get current authenticated user"""
    correlation_id = get_correlation_id(request)
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_TOKEN",
                    "message": "Authorization token required",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )
    
    current_user = await auth_service.get_current_user(credentials.credentials, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid or expired token",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )
    
    return current_user

@router.get(
    "/profile",
    response_model=CompleteUserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "User not found"}
    }
)
async def get_user_profile(
    request: Request,
    current_user = Depends(get_current_user_dependency)
):
    """
    Get current user's complete profile
    
    Returns the authenticated user's profile including:
    - Basic user information
    - Profile details
    - Driver details (if applicable)
    """
    correlation_id = get_correlation_id(request)
    
    try:
        # Convert user to response format
        user_dict = current_user.to_dict()
        user_response = UserResponse(**user_dict)
        
        # Create complete response
        complete_response = CompleteUserResponse(**user_dict)
        
        # Add profile if exists
        if current_user.profile:
            profile_dict = current_user.profile.to_dict()
            complete_response.profile = UserProfileResponse(**profile_dict)
        
        # Add driver details if exists
        if current_user.driver_details:
            from src.models.schemas import DriverDetailsResponse
            driver_dict = current_user.driver_details.to_dict()
            complete_response.driver_details = DriverDetailsResponse(**driver_dict)
        
        logger.info(
            "User profile retrieved",
            user_id=str(current_user.id),
            correlation_id=correlation_id
        )
        
        return complete_response
        
    except Exception as e:
        logger.error(
            "Failed to get user profile",
            user_id=str(current_user.id),
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "PROFILE_FETCH_FAILED",
                    "message": "Failed to retrieve user profile",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )

@router.put(
    "/profile",
    response_model=UserProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        400: {"model": ErrorResponse, "description": "Bad Request"}
    }
)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    request: Request,
    current_user = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile
    
    Updates the authenticated user's profile information.
    Creates a profile if one doesn't exist.
    """
    correlation_id = get_correlation_id(request)
    
    try:
        # Get or create user profile
        if not current_user.profile:
            from src.models.user import UserProfile
            new_profile = UserProfile(
                user_id=current_user.id,
                preferred_language="en"
            )
            db.add(new_profile)
            await db.flush()
            current_user.profile = new_profile
        
        profile = current_user.profile
        
        # Update profile fields
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
        
        await db.commit()
        await db.refresh(profile)
        
        logger.info(
            "User profile updated",
            user_id=str(current_user.id),
            updated_fields=list(update_data.keys()),
            correlation_id=correlation_id
        )
        
        profile_dict = profile.to_dict()
        return UserProfileResponse(**profile_dict)
        
    except Exception as e:
        logger.error(
            "Failed to update user profile",
            user_id=str(current_user.id),
            error=str(e),
            correlation_id=correlation_id
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "PROFILE_UPDATE_FAILED",
                    "message": "Failed to update user profile",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )