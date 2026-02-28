from sqlalchemy.orm import Session
from backend.app.modules.auth import models, schemas, security
from fastapi import HTTPException

class AuthService:
    @staticmethod
    def create_tenant_and_user(db: Session, tenant: schemas.TenantCreate, user: schemas.UserCreate) -> models.User:
        # 1. Create Tenant
        db_tenant = models.Tenant(name=tenant.name)
        db.add(db_tenant)
        db.flush() # Get ID

        # 2. Check if user exists
        if db.query(models.User).filter(models.User.email == user.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")

        # 3. Create User
        hashed_password = security.get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            password_hash=hashed_password,
            tenant_id=db_tenant.id,
            role=models.UserRole.OWNER # First user is owner
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            return None
        if not security.verify_password(password, user.password_hash):
            return None
        return user
