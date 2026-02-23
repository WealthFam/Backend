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
    
    
    # DB Creation (Dev only - migrations removed, use fresh schema.sql for setup)
    # Checks for existing tables.
    
    # Create tables first
    Base.metadata.create_all(bind=engine)

    # Run Auto-Migrations (DuckDB Schema Evolution)
    run_auto_migrations(engine)

    # --- Background Tasks ---
    
    @application.on_event("startup")
    async def startup_event():
        # Start Scheduler (Handles both recurring checks and email auto-sync)
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
