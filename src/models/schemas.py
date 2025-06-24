from pydantic import BaseModel, EmailStr, field_validator, Field
from typing import Optional, Literal
from datetime import datetime, date
from decimal import Decimal
import uuid
import re

# Base schemas
class BaseResponse(BaseModel):
    """Base response model"""
    model_config = {"from_attributes": True}

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: dict
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User with email user@example.com not found",
                    "correlation_id": "uuid",
                    "timestamp": "2025-01-01T12:00:00Z"
                }
            }
        }
    }

# User schemas
class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    role: Literal["rider", "driver", "admin"]
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format"""
        # Remove any non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^\+?[\d]{10,15}$', cleaned):
            raise ValueError("Invalid phone number format")
        return cleaned
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        """Validate names"""
        if not v.strip():
            raise ValueError("Name cannot be empty")
        # Remove extra whitespace
        return v.strip()

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

class UserResponse(BaseResponse):
    """Schema for user response"""
    id: str
    email: str
    first_name: str
    last_name: str
    phone: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

class TokenResponse(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Profile schemas
class UserProfileCreate(BaseModel):
    """Schema for creating user profile"""
    profile_image_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    preferred_language: Optional[str] = "en"
    
    @field_validator("profile_image_url")
    @classmethod
    def validate_image_url(cls, v):
        """Validate image URL"""
        if v and not re.match(r'^https?://.+\.(jpg|jpeg|png|gif|webp)$', v, re.IGNORECASE):
            raise ValueError("Invalid image URL format")
        return v

class UserProfileUpdate(BaseModel):
    """Schema for updating user profile"""
    profile_image_url: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    preferred_language: Optional[str] = None

class UserProfileResponse(BaseResponse):
    """Schema for user profile response"""
    id: str
    profile_image_url: Optional[str]
    date_of_birth: Optional[date]
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    preferred_language: str
    created_at: datetime
    updated_at: datetime

# Driver schemas
class DriverDetailsCreate(BaseModel):
    """Schema for creating driver details"""
    license_number: str = Field(..., min_length=5, max_length=50)
    vehicle_make: Optional[str] = Field(None, max_length=50)
    vehicle_model: Optional[str] = Field(None, max_length=50)
    vehicle_year: Optional[int] = Field(None, ge=1990, le=2030)
    vehicle_color: Optional[str] = Field(None, max_length=30)
    license_plate: Optional[str] = Field(None, max_length=20)
    
    @field_validator("license_number")
    @classmethod
    def validate_license_number(cls, v):
        """Validate license number format"""
        if not v.strip():
            raise ValueError("License number cannot be empty")
        return v.strip().upper()
    
    @field_validator("license_plate")
    @classmethod
    def validate_license_plate(cls, v):
        """Validate license plate format"""
        if v:
            return v.strip().upper()
        return v

class DriverDetailsUpdate(BaseModel):
    """Schema for updating driver details"""
    vehicle_make: Optional[str] = Field(None, max_length=50)
    vehicle_model: Optional[str] = Field(None, max_length=50)
    vehicle_year: Optional[int] = Field(None, ge=1990, le=2030)
    vehicle_color: Optional[str] = Field(None, max_length=30)
    license_plate: Optional[str] = Field(None, max_length=20)

class DriverDetailsResponse(BaseResponse):
    """Schema for driver details response"""
    id: str
    license_number: str
    vehicle_make: Optional[str]
    vehicle_model: Optional[str]
    vehicle_year: Optional[int]
    vehicle_color: Optional[str]
    license_plate: Optional[str]
    is_verified: bool
    rating: float
    total_rides: int
    created_at: datetime
    updated_at: datetime

# Complete user response with profile and driver details
class CompleteUserResponse(UserResponse):
    """Complete user response with profile and driver details"""
    profile: Optional[UserProfileResponse] = None
    driver_details: Optional[DriverDetailsResponse] = None

# User update schemas
class UserUpdate(BaseModel):
    """Schema for updating user information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format"""
        if v:
            cleaned = re.sub(r'[^\d+]', '', v)
            if not re.match(r'^\+?[\d]{10,15}$', cleaned):
                raise ValueError("Invalid phone number format")
            return cleaned
        return v
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_names(cls, v):
        """Validate names"""
        if v is not None:
            if not v.strip():
                raise ValueError("Name cannot be empty")
            return v.strip()
        return v

class UserProfileUpdateRequest(BaseModel):
    """Schema for updating user and profile together"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    profile: Optional[UserProfileUpdate] = None

# Health check schema
class HealthResponse(BaseModel):
    """Health check response schema"""
    status: str
    service: str
    timestamp: datetime
    dependencies: dict

class ReadinessResponse(BaseModel):
    """Readiness check response schema"""
    status: str
    service: str
    timestamp: datetime
    dependencies: dict
    checks: dict

# JWT Token payload schema
class TokenData(BaseModel):
    """JWT token data schema"""
    user_id: str
    email: str
    role: str
    exp: int
    iat: int
    correlation_id: str