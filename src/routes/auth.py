from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import structlog

from src.models.schemas import UserCreate, UserLogin, TokenResponse, ErrorResponse
from src.services.auth_service import auth_service
from src.config.database import get_db
from src.utils.security import extract_token_from_header

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer(auto_error=False)

def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request"""
    return getattr(request.state, 'correlation_id', 'unknown')

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    
    Creates a new user account with the provided information.
    Returns an access token for immediate authentication.
    
    - **email**: Valid email address (unique)
    - **password**: Strong password (min 8 chars, uppercase, lowercase, digit, special char)
    - **first_name**: User's first name
    - **last_name**: User's last name
    - **phone**: Phone number (unique)
    - **role**: User role (rider, driver, or admin)
    """
    correlation_id = get_correlation_id(request)
    
    logger.info(
        "User registration attempt",
        email=user_data.email,
        role=user_data.role,
        correlation_id=correlation_id
    )
    
    try:
        result = await auth_service.register_user(user_data, db, correlation_id)
        
        logger.info(
            "User registration successful",
            user_id=result.user.id,
            email=result.user.email,
            correlation_id=correlation_id
        )
        
        return result
        
    except HTTPException as e:
        logger.warning(
            "User registration failed",
            email=user_data.email,
            error=e.detail,
            correlation_id=correlation_id
        )
        raise
    except Exception as e:
        logger.error(
            "User registration error",
            email=user_data.email,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "REGISTRATION_FAILED",
                    "message": "Registration failed due to internal error",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def login_user(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access token
    
    Validates user credentials and returns a JWT access token
    for authenticated requests.
    
    - **email**: User's email address
    - **password**: User's password
    """
    correlation_id = get_correlation_id(request)
    
    logger.info(
        "User login attempt",
        email=login_data.email,
        correlation_id=correlation_id
    )
    
    try:
        result = await auth_service.login_user(login_data, db, correlation_id)
        
        logger.info(
            "User login successful",
            user_id=result.user.id,
            email=result.user.email,
            correlation_id=correlation_id
        )
        
        return result
        
    except HTTPException as e:
        logger.warning(
            "User login failed",
            email=login_data.email,
            error=e.detail,
            correlation_id=correlation_id
        )
        raise
    except Exception as e:
        logger.error(
            "User login error",
            email=login_data.email,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "LOGIN_FAILED",
                    "message": "Login failed due to internal error",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )

@router.post(
    "/logout",
    responses={
        200: {"description": "Successfully logged out"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout user and invalidate session
    
    Invalidates the current session and adds the token to blacklist
    to prevent further use.
    
    Requires valid Bearer token in Authorization header.
    """
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
    
    token = credentials.credentials
    
    try:
        # Validate token and get user data
        token_data = await auth_service.validate_token(token)
        if not token_data:
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
        
        user_id = token_data.get("user_id")
        
        logger.info(
            "User logout attempt",
            user_id=user_id,
            correlation_id=correlation_id
        )
        
        result = await auth_service.logout_user(user_id, token, correlation_id)
        
        logger.info(
            "User logout successful",
            user_id=user_id,
            correlation_id=correlation_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "User logout error",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "LOGOUT_FAILED",
                    "message": "Logout failed due to internal error",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )

@router.post("/verify-token")
async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Verify JWT token validity
    
    This endpoint is used by other services to validate tokens.
    Returns user information if token is valid.
    """
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
    
    token = credentials.credentials
    
    try:
        token_data = await auth_service.validate_token(token)
        if not token_data:
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
        
        return {
            "valid": True,
            "user_id": token_data["user_id"],
            "email": token_data["email"],
            "role": token_data["role"],
            "correlation_id": correlation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Token verification error",
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TOKEN_VERIFICATION_FAILED",
                    "message": "Token verification failed",
                    "correlation_id": correlation_id,
                    "timestamp": str(datetime.utcnow())
                }
            }
        )