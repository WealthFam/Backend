from pydantic import BaseModel, EmailStr, ConfigDict, BeforeValidator
from typing import Optional, Annotated, Any
from uuid import UUID
from datetime import date
from backend.app.modules.auth.models import UserRole

# --- Coercion Utilities (PRACTICES.md Section 11.2) ---
# These functions act as "BeforeValidators" to ensure Pydantic strict mode 
# doesn't reject valid JSON strings (UUIDs/Dates) before they can be parsed.

def coerce_uuid(v: Any) -> Any:
    """Proactively convert string UUIDs into UUID objects for strict-mode compliance."""
    if v is None: return None
    if isinstance(v, str):
        try:
            return UUID(v)
        except ValueError:
            return v
    return v

def coerce_date(v: Any) -> Any:
    """Extract date from datetime strings to prevent strict-mode mismatch."""
    if v is None: return None
    if hasattr(v, 'date'): 
        return v.date() # Convert datetime instance to date
    return v

# Hardened Type Aliases: These ensure data integrity while allowing standard API coercion.
StrictUUID = Annotated[UUID, BeforeValidator(coerce_uuid)]
StrictDate = Annotated[date, BeforeValidator(coerce_date)]

class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    pass

class TenantRead(TenantBase):
    id: StrictUUID
    
    model_config = ConfigDict(from_attributes=True, strict=True)

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    dob: Optional[StrictDate] = None # ISO format YYYY-MM-DD
    pan_number: Optional[str] = None
    phone_number: Optional[str] = None
    role: UserRole = UserRole.ADULT

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: StrictUUID
    tenant_id: StrictUUID
    
    model_config = ConfigDict(from_attributes=True, strict=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    dob: Optional[StrictDate] = None
    pan_number: Optional[str] = None
    phone_number: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[str] = None
