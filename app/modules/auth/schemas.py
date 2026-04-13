from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import date
from backend.app.modules.auth.models import UserRole

class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    pass

class TenantRead(TenantBase):
    id: UUID
    
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    dob: Optional[date] = None # ISO format YYYY-MM-DD
    pan_number: Optional[str] = None
    role: UserRole = UserRole.ADULT

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: UUID
    tenant_id: UUID
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    dob: Optional[date] = None
    pan_number: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[str] = None
