from typing import Optional
from fastapi import Depends, HTTPException, status, Query
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.modules.auth import models, schemas, services

from fastapi.security import OAuth2PasswordBearer, HTTPBasic, HTTPBasicCredentials

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)
basic_scheme = HTTPBasic(auto_error=False)

def get_current_user_from_token(db: Session, token: str) -> Optional[models.User]:
    """Synchronous helper for token validation (used by WebSockets)"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        if email is None or tenant_id is None:
            return None
        
        return db.query(models.User).filter(models.User.email == email).first()
    except JWTError:
        return None

def get_current_user(
    token: str = Depends(oauth2_scheme),
    token_query: Optional[str] = Query(None, alias="token"),
    basic_auth: HTTPBasicCredentials = Depends(basic_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Priority 1: Bearer Token (JWT)
    final_token = token or token_query
    if final_token:
        user = get_current_user_from_token(db, final_token)
        if user:
            return user
        raise credentials_exception

    # Priority 2: Basic Auth
    if basic_auth:
        user = services.AuthService.authenticate_user(db, basic_auth.username, basic_auth.password)
        if not user:
             raise credentials_exception
        return user
        
    # Neither provided
    raise credentials_exception

def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    # Add active check if needed
    return current_user
