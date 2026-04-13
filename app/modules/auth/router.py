from typing import List
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.modules.auth import schemas, services, security, models as auth_models
from backend.app.modules.auth.dependencies import get_current_user

router = APIRouter()

@router.post("/register", response_model=schemas.UserRead)
def register_tenant(
    tenant: schemas.TenantCreate,
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new tenant (family) and the initial owner user.
    """
    return services.AuthService.create_tenant_and_user(db, tenant, user)

from jose import jwt

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = services.AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token, jti = security.create_access_token(
        data={"sub": user.email, "tenant_id": str(user.tenant_id)},
        expires_delta=access_token_expires
    )
    
    # Record token in DB
    from backend.app.core import timezone
    db_token = auth_models.UserToken(
        user_id=user.id,
        token_jti=jti,
        expires_at=timezone.utcnow() + access_token_expires
    )
    db.add(db_token)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(
    token: str = Depends(security.OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")),
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    """Revoke the current session."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")
        if jti:
            db_token = db.query(auth_models.UserToken).filter(auth_models.UserToken.token_jti == jti).first()
            if db_token:
                db_token.is_revoked = True
                db.commit()
    except Exception:
        pass # Already invalid or failed decode
    return {"message": "Logged out successfully"}

@router.post("/logout-all")
def logout_all(
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    """Revoke ALL sessions for the current user."""
    db.query(auth_models.UserToken).filter(
        auth_models.UserToken.user_id == current_user.id,
        auth_models.UserToken.is_revoked == False
    ).update({"is_revoked": True})
    db.commit()
    return {"message": "All sessions revoked successfully"}


@router.get("/me", response_model=schemas.UserRead)
def read_users_me(current_user: auth_models.User = Depends(get_current_user)):
    """
    Get current user profile.
    """
    return current_user

@router.get("/tenants", response_model=List[schemas.TenantRead])
def list_tenants(
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    # For now, return all tenants to allow "tagging" accounts to other tenants as requested
    return db.query(auth_models.Tenant).all()

@router.put("/tenants/{tenant_id}", response_model=schemas.TenantRead)
def update_tenant(
    tenant_id: str,
    payload: schemas.TenantCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    tenant = db.query(auth_models.Tenant).filter(auth_models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.name = payload.name
    db.commit()
    db.refresh(tenant)
    return tenant

@router.get("/users", response_model=List[schemas.UserRead])
def list_family_members(
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    """List all users in the current family circle."""
    return db.query(auth_models.User).filter(auth_models.User.tenant_id == current_user.tenant_id).all()

@router.post("/users", response_model=schemas.UserRead)
def create_family_member(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    """Add a new member (e.g. Wife, Kid) to the family circle."""
    # Check if email exists
    existing = db.query(auth_models.User).filter(auth_models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create user
    new_user = auth_models.User(
        email=payload.email,
        password_hash=security.get_password_hash(payload.password),
        tenant_id=current_user.tenant_id,
        role=payload.role,
        full_name=payload.full_name,
        avatar=payload.avatar,
        dob=payload.dob,
        pan_number=payload.pan_number
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{user_id}", response_model=schemas.UserRead)
def update_family_member(
    user_id: str,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    """Update a family member's profile or permissions."""
    member = db.query(auth_models.User).filter(
        auth_models.User.id == user_id, 
        auth_models.User.tenant_id == current_user.tenant_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if payload.full_name is not None:
        member.full_name = payload.full_name
    if payload.avatar is not None:
        member.avatar = payload.avatar
    if payload.role is not None:
        member.role = payload.role
    if payload.dob is not None:
        member.dob = payload.dob
    if payload.pan_number is not None:
        member.pan_number = payload.pan_number
    if payload.password:
        member.password_hash = security.get_password_hash(payload.password)
        
    db.commit()
    db.refresh(member)
    return member
