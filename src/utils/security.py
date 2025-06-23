from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import uuid
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_data: dict, correlation_id: Optional[str] = None) -> str:
    """Create JWT access token"""
    settings = get_settings()
    
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    
    # Calculate expiration time
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    
    # Create token payload
    payload = {
        "user_id": str(user_data["id"]),
        "email": user_data["email"],
        "role": user_data["role"],
        "exp": expire,
        "iat": datetime.utcnow(),
        "correlation_id": correlation_id
    }
    
    # Encode JWT token
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    logger.info(
        "JWT token created",
        user_id=payload["user_id"],
        email=payload["email"],
        role=payload["role"],
        correlation_id=correlation_id,
        expires_at=expire.isoformat()
    )
    
    return token

def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode JWT access token"""
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        
        # Check if token is expired
        exp = payload.get("exp")
        if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
            logger.warning("JWT token expired", token_exp=exp)
            return None
        
        # Extract user data
        user_data = {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "role": payload.get("role"),
            "exp": exp,
            "iat": payload.get("iat"),
            "correlation_id": payload.get("correlation_id")
        }
        
        return user_data
        
    except JWTError as e:
        logger.warning("JWT token verification failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error verifying JWT token", error=str(e))
        return None

def extract_token_from_header(authorization: str) -> Optional[str]:
    """Extract JWT token from Authorization header"""
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        return token
    except ValueError:
        return None

def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())

def is_strong_password(password: str) -> tuple[bool, list[str]]:
    """Check if password meets strength requirements"""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors

def mask_sensitive_data(data: dict, fields_to_mask: list = None) -> dict:
    """Mask sensitive data for logging"""
    if fields_to_mask is None:
        fields_to_mask = ["password", "password_hash", "token", "secret"]
    
    masked_data = data.copy()
    
    for field in fields_to_mask:
        if field in masked_data:
            masked_data[field] = "***MASKED***"
    
    return masked_data