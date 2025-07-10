from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, DECIMAL, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime

from src.config.database import Base

class User(Base):
    """User table - stores basic user information"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)  # 'rider', 'driver', 'admin'
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    driver_details = relationship("DriverDetails", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self, include_sensitive=False):
        """Convert user to dictionary"""
        data = {
            "id": str(self.id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data["password_hash"] = self.password_hash
            
        return data

class UserProfile(Base):
    """User profile table - stores additional user information"""
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    profile_image_url = Column(String(500), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    preferred_language = Column(String(10), default="en", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile(id={self.id}, user_id={self.user_id})>"
    
    def to_dict(self):
        """Convert profile to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "profile_image_url": self.profile_image_url,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "address": self.address,
            "city": self.city,
            "country": self.country,
            "preferred_language": self.preferred_language,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class DriverDetails(Base):
    """Driver details table - stores driver-specific information"""
    __tablename__ = "driver_details"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    #user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    vehicle_make = Column(String(50), nullable=True)
    vehicle_model = Column(String(50), nullable=True)
    vehicle_year = Column(Integer, nullable=True)
    vehicle_color = Column(String(30), nullable=True)
    license_plate = Column(String(20), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    rating = Column(DECIMAL(3, 2), default=5.00, nullable=False)
    total_rides = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="driver_details")
    
    def __repr__(self):
        return f"<DriverDetails(id={self.id}, user_id={self.user_id}, license={self.license_number})>"
    
    def to_dict(self):
        """Convert driver details to dictionary"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "license_number": self.license_number,
            "vehicle_make": self.vehicle_make,
            "vehicle_model": self.vehicle_model,
            "vehicle_year": self.vehicle_year,
            "vehicle_color": self.vehicle_color,
            "license_plate": self.license_plate,
            "is_verified": self.is_verified,
            "rating": float(self.rating) if self.rating else 5.0,
            "total_rides": self.total_rides,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

# Create indexes for better performance
Index("idx_users_email", User.email)
Index("idx_users_phone", User.phone)
Index("idx_users_role", User.role)
Index("idx_driver_details_license", DriverDetails.license_number)