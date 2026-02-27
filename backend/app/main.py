from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

from backend.app.core.config import settings
from backend.app.core.exceptions import http_exception_handler, generic_exception_handler
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.core.migration import run_auto_migrations

# Routers
from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.finance.routers import router as finance_router
from backend.app.modules.ingestion.router import router as ingestion_router
from backend.app.modules.ingestion.ai_router import router as ai_router
from backend.app.modules.mobile.router import router as mobile_router
from backend.app.modules.vault.router import router as vault_router

# Background Tasks
from backend.app.modules.ingestion.email_sync import EmailSyncService
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.core.scheduler import start_scheduler, stop_scheduler

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restrict in production
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
    application.include_router(mobile_router, prefix=f"{settings.API_V1_STR}/mobile", tags=["mobile"])
    application.include_router(vault_router, prefix=f"{settings.API_V1_STR}/finance/vault", tags=["Vault"])
    
    
    # Run Auto-Migrations (DuckDB Schema Evolution)
    # run_auto_migrations(engine)  <-- REFACTORED TO STARTUP EVENT


    # --- Background Tasks ---
    
    @application.on_event("startup")
    async def startup_event():
        # --- Database Setup ---
        try:
            logger.info("Initializing database and running migrations...")
            # Create tables first
            Base.metadata.create_all(bind=engine)
            # Run Auto-Migrations (DuckDB Schema Evolution)
            run_auto_migrations(engine)
            logger.info("Database initialization complete.")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            # Non-fatal during startup might be better, but DuckDB usually needs this
        
        # Start Scheduler (Handles both recurring checks and email auto-sync)
        start_scheduler()
        
        # Trigger single-tenant migration on the parser service if we have exactly one tenant
        try:
            logger.info("Checking if Parser needs single-tenant data migration...")
            db = SessionLocal()
            from backend.app.modules.auth.models import Tenant
            tenants = db.query(Tenant).limit(2).all()
            if len(tenants) == 1:
                from backend.app.modules.ingestion.parser_service import ExternalParserService
                single_tenant_id = tenants[0].id
                logger.info(f"Found single active backend tenant {single_tenant_id}. Triggering parser data migration.")
                
                async def wait_and_trigger():
                    import requests
                    import time
                    max_retries = 10
                    url = f"{settings.PARSER_SERVICE_URL}/health"
                    for i in range(max_retries):
                        try:
                            # Use internal health check to wait for service
                            if requests.get(url, timeout=2).status_code == 200:
                                logger.info(f"Parser is healthy. Firing migration for tenant {single_tenant_id}...")
                                ExternalParserService.trigger_migration(single_tenant_id)
                                return
                        except:
                            pass
                        logger.info(f"Waiting for Parser service... (Attempt {i+1}/{max_retries})")
                        await asyncio.sleep(2)
                    logger.warning("Parser service did not become healthy in time. Migration trigger skipped.")

                asyncio.create_task(wait_and_trigger())
            db.close()
        except Exception as e:
            logger.error(f"Failed to check/trigger parser migration: {e}")
        
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

    @application.on_event("shutdown")
    async def stop_scheduler_event():
        stop_scheduler()

    return application

app = create_application()

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
