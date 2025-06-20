from pydantic import BaseModel, EmailStr, UUID4
from typing import Optional
from datetime import datetime

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None

# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr # Email is required for creation
    password: str   # Password is required for creation

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None # Password update is optional

# Schema for password change
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# Properties stored in DB (inherits from UserBase)
class UserInDBBase(UserBase):
    id: UUID4
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True # Enable Pydantic to read data from ORM models

# Properties to return to client (inherits from UserInDBBase)
# Exclude sensitive fields like hashed_password by default
class User(UserInDBBase):
    pass

# Additional schema for properties stored in DB (including password hash)
class UserInDB(UserInDBBase):
    hashed_password: str

# Schema for the ANON_KEY response
class AnonKeyResponse(BaseModel):
    anon_key: Optional[str] = None
