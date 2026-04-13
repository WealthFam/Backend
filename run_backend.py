import logging
import multiprocessing
import os
import subprocess
import sys
import traceback

# Standard Compliance (Section 11.243): Sys.path must be set before any internal module imports
sys.path.append(os.getcwd())

import uvicorn

# Standard Compliance (Section 11.278): Structured logging replaces raw print statements
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("orchestrator")

# Internal Application Imports (Section 11.247)
from backend.app.core.database import Base as BackendBase, engine as backend_engine
from backend.app.core.migrations.manager import run_schema_sync
from parser.db.database import Base as ParserBase, engine as parser_engine

# Import models to register them with SQLAlchemy Base (Section 3.91)
import backend.app.modules.auth.models
import backend.app.modules.finance.models
import backend.app.modules.ingestion.models
import backend.app.modules.vault.models
import backend.app.modules.notifications.models
import parser.db.models

# Configuration Constants (Section 11.277)
BACKEND_PORT = 8000
PARSER_PORT = 8001
HOST = "0.0.0.0"

def run_main_app():
    """Starts the main FastAPI backend service."""
    logger.info(f"Starting Main Backend on port {BACKEND_PORT}...")
    use_reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    uvicorn.run("backend.app.main:app", host=HOST, port=BACKEND_PORT, reload=use_reload)

def run_parser_service():
    """Starts the parser microservice."""
    logger.info(f"Starting Parser Service on port {PARSER_PORT}...")
    use_reload = os.getenv("APP_RELOAD", "false").lower() == "true"
    uvicorn.run("parser.main:app", host=HOST, port=PARSER_PORT, reload=use_reload)

def run_initialization():
    """
    Performs system-wide initialization sequentially to prevent DuckDB lock contention.
    """
    logger.info("Initializing system services...")
    
    try:
        # Step 1: Baseline DDL (PRACTICES.md Section 3.93)
        logger.info("Synchronizing core database schemas...")
        BackendBase.metadata.create_all(bind=backend_engine)
        ParserBase.metadata.create_all(bind=parser_engine)
        
        # Step 2: Modular Scheme Evolution
        logger.info("Applying pending schema migrations...")
        run_schema_sync(backend_engine)
        
        # Step 3: Resource Cleanup
        # Dispose engines to release DuckDB file locks before spawning parallel microservices
        backend_engine.dispose()
        parser_engine.dispose()
        logger.info("Database synchronization finalized; file locks released.")
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    logger.info("Core initialization complete. Transitioning to service launch.")

if __name__ == "__main__":
    # Ensure data volumes exist in non-Windows environments
    if not os.path.exists("/data") and os.name != 'nt':
        try:
            os.makedirs("/data", exist_ok=True)
        except Exception:
            pass

    # Step 1: Execute sequential setup
    run_initialization()

    # Step 2: Spawn service processes
    backend_proc = multiprocessing.Process(target=run_main_app)
    parser_proc = multiprocessing.Process(target=run_parser_service)

    backend_proc.start()
    parser_proc.start()

    try:
        backend_proc.join()
        parser_proc.join()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received. Terminating services...")
        backend_proc.terminate()
        parser_proc.terminate()
