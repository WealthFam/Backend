import logging
import os
import asyncio

logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.v1.router import api_router as api_v1_router
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.exceptions import generic_exception_handler, http_exception_handler
from backend.app.core.migrations.manager import run_schema_sync
from backend.app.core.scheduler import start_scheduler, stop_scheduler
from backend.app.core.websockets import manager
from backend.app.modules.auth.dependencies import get_current_user_from_token
from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.finance.routers import router as finance_router
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.ai_router import router as ai_router
from backend.app.modules.ingestion.email_sync import EmailSyncService
from backend.app.modules.ingestion.router import router as ingestion_router
from backend.app.modules.notifications.routers.alerts import router as notifications_router
from backend.app.modules.vault.router import router as vault_router

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Middleware
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")] if settings.ALLOWED_ORIGINS else []
    
    # Starlette/FastAPI CORS does not allow allow_origins=["*"] when allow_credentials=True.
    # If the user put "*", we'll use allow_origin_regex=".*" which effectively does the same
    # while satisfying the library requirements, though it's less secure.
    # BEST PRACTICE: Define explicit origins in .env
    
    cors_params = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
    
    if "*" in origins:
        cors_params["allow_origin_regex"] = ".*"
    else:
        cors_params["allow_origins"] = origins

    application.add_middleware(CORSMiddleware, **cors_params)


    # Exception Handlers
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        logger.error(f"422 Validation Error at {request.url.path}: {exc.errors()}")
        logger.error(f"Request body: {exc.body}")
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": str(exc.body)},
        )

    # Routers
    application.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    application.include_router(finance_router, prefix=f"{settings.API_V1_STR}/finance", tags=["finance"])
    application.include_router(notifications_router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
    application.include_router(ingestion_router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["ingestion"])
    application.include_router(ai_router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["ai"])
    application.include_router(vault_router, prefix=f"{settings.API_V1_STR}/finance/vault", tags=["Vault"])
    
    # Standardized API V1 Router (currently includes mobile)
    application.include_router(api_v1_router, prefix=settings.API_V1_STR)

    @application.on_event("startup")
    async def startup_event():
        # Set the event loop for the connection manager to enable thread-safe broadcasts
        manager.set_loop(asyncio.get_event_loop())
        
        # 1. Ensure all ORM-defined tables exist (CREATE TABLE IF NOT EXISTS)
        logger.info("Running Base.metadata.create_all...")
        Base.metadata.create_all(bind=engine)
        
        # 2. Run modular migrations for schema evolution (DuckDB safe)
        logger.info("Running auto-migrations...")
        try:
            run_schema_sync(engine)
        except Exception as e:
            logger.error(f"Auto-migration failed: {e}")
            logger.exception(e)
            # Fail early if migrations are broken to prevent inconsistent data states
            raise e
        
        # 3. Start Scheduler (Handles both recurring checks and email auto-sync)
        start_scheduler()
    @application.on_event("shutdown")
    async def stop_scheduler_event():
        stop_scheduler()

    return application


app = create_application()

from fastapi import Query

@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str, token: str = Query(...)):
    """
    WebSocket endpoint for real-time notifications.
    Token is passed as a query param for authentication.
    """
    logger.info(f"--- WebSocket Connection Attempt ---")
    logger.info(f"Tenant: {tenant_id}")
    logger.info(f"Token length: {len(token) if token else 0}")
    
    try:
        # Authenticate user from token
        with SessionLocal() as db:
            user = get_current_user_from_token(db, token)
        
        if not user:
            logger.warning(f"WebSocket auth failed: Invalid or expired token.")
            await websocket.close(code=4008)
            return
            
        if str(user.tenant_id) != tenant_id:
            logger.warning(f"WebSocket auth failed: User {user.email} (tenant {user.tenant_id}) attempted to connect to tenant {tenant_id}.")
            await websocket.close(code=4003) # Forbidden
            return

        logger.info(f"WebSocket authenticated: User {user.email} for tenant {tenant_id}")
        await manager.connect(websocket, tenant_id)
        
        while True:
            # Keep connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
    except Exception as e:
        logger.error(f"WebSocket fatal error for tenant {tenant_id}: {str(e)}")
        # Only try to disconnect if it was already connected
        try:
            manager.disconnect(websocket, tenant_id)
        except:
            pass

@app.get("/")
def root():
    return {"message": "Welcome to WealthFam API"}

@app.get("/ping")
def ping_test():
    return {"ping": "pong"}

@app.get("/health")
def health():
    """Health check endpoint for cloud platforms"""
    try:
        # Check database connectivity
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "status": "healthy",
            "service": "WealthFam",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "WealthFam",
            "database": "disconnected",
            "error": str(e)
        }
