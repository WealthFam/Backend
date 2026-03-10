import logging
import os
import asyncio

logger = logging.getLogger(__name__)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.router import api_router as api_v1_router
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.core.exceptions import generic_exception_handler, http_exception_handler
from backend.app.core.migration import run_auto_migrations
from backend.app.core.scheduler import start_scheduler, stop_scheduler
from backend.app.core.websockets import manager
from backend.app.modules.auth.dependencies import get_current_user_from_token
from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.finance.routers import router as finance_router
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.ai_router import router as ai_router
from backend.app.modules.ingestion.email_sync import EmailSyncService
from backend.app.modules.ingestion.router import router as ingestion_router
from backend.app.modules.vault.router import router as vault_router

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    # Routers
    application.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
    application.include_router(finance_router, prefix=f"{settings.API_V1_STR}/finance", tags=["finance"])
    application.include_router(ingestion_router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["ingestion"])
    application.include_router(ai_router, prefix=f"{settings.API_V1_STR}/ingestion", tags=["ai"])
    application.include_router(vault_router, prefix=f"{settings.API_V1_STR}/finance/vault", tags=["Vault"])
    
    # Standardized API V1 Router (currently includes mobile)
    application.include_router(api_v1_router, prefix=settings.API_V1_STR)

    @application.on_event("startup")
    async def startup_event():
        
        # 1. Ensure all ORM-defined tables exist (CREATE TABLE IF NOT EXISTS)
        logger.info("Running Base.metadata.create_all...")
        Base.metadata.create_all(bind=engine)
        
        # 2. Run ALTER TABLE migrations for columns added after initial table creation
        logger.info("Running auto-migrations...")
        try:
            run_auto_migrations(engine)
        except Exception as e:
            logger.error(f"Auto-migration failed: {e}")
            logger.exception(e)
        
        # 3. Start Scheduler (Handles both recurring checks and email auto-sync)
        start_scheduler()
        
        # Seed Demo Data (Only if DEMO_MODE is true)
        demo_mode = str(os.getenv("DEMO_MODE", "false")).lower()
        logger.info(f"Startup Config: DEMO_MODE={demo_mode}")
        
        if demo_mode == "true":
            try:
                logger.info("Starting demo data seeding...")
                from backend.app.core.seeder import seed_data
                seed_data()
                logger.info("Demo data seeding completed.")
            except Exception as e:
                logger.error(f"Startup seeding failed: {e}")
                logger.exception(e)

        # Trigger single-tenant migration on the parser service
        # This aligns any old 'system_tenant' data in the parser DB with the active tenant.
        db = SessionLocal()
        try:
            from backend.app.modules.auth.models import Tenant
            # Find the most recent active tenant
            tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).limit(2).all()
            
            # If we have exactly one tenant (ideal for self-hosted/single-user Docker), 
            # we trigger the migration automatically.
            if len(tenants) == 1:
                from backend.app.modules.ingestion.parser_service import ExternalParserService
                single_tenant_id = tenants[0].id
                logger.info(f"Found active tenant {single_tenant_id}. Waiting for Parser service to trigger data migration...")
                
                async def wait_and_trigger():
                    import requests
                    # 5 minute window: 60 retries * 5 seconds = 300 seconds
                    max_retries = 60 
                    url = f"{settings.PARSER_SERVICE_URL}/health"
                    logger.info(f"Starting 5-minute wait window for Parser health check...")
                    
                    for i in range(max_retries):
                        try:
                            # Use internal health check to wait for service
                            if requests.get(url, timeout=3).status_code == 200:
                                logger.info(f"Parser is healthy. Firing migration for tenant {single_tenant_id}...")
                                success = ExternalParserService.trigger_migration(single_tenant_id)
                                if success:
                                    logger.info("Parser migration trigger SUCCESS.")
                                else:
                                    logger.warning("Parser migration trigger returned non-200 status.")
                                return
                        except Exception:
                            pass
                        
                        if (i + 1) % 12 == 0: # Log every 1 minute
                            logger.info(f"Still waiting for Parser service... (Minute {(i+1)//12}/5)")
                        
                        await asyncio.sleep(5)
                    logger.warning("Parser service did not become healthy within 5 minutes. Migration trigger skipped.")

                asyncio.create_task(wait_and_trigger())
            else:
                log_msg = f"Active tenants found: {len(tenants)}. "
                if len(tenants) == 0:
                    log_msg += "No tenant data found to migrate."
                else:
                    log_msg += "Automatic migration trigger skipped (multiple tenants require manual action)."
                logger.info(log_msg)
        except Exception as e:
            logger.error(f"Failed to check/trigger parser migration: {e}")
        finally:
            db.close()

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
    logger.info(f"Incoming WS connection attempt: tenant_id={tenant_id}, token_length={len(token) if token else 0}")
    try:
        # Authenticate user from token
        with SessionLocal() as db:
            user = get_current_user_from_token(db, token)
        
        if not user:
            logger.warning(f"WebSocket auth failed: Invalid or expired token for tenant {tenant_id}.")
            await websocket.close(code=4008) # Policy Violation / Auth Failed
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