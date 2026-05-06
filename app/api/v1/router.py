from fastapi import APIRouter
from backend.app.modules.mobile.api.router import router as mobile_router
from backend.app.api.v1.agent import router as agent_router

api_router = APIRouter()
api_router.include_router(mobile_router, prefix="/mobile", tags=["Mobile"])
api_router.include_router(agent_router, prefix="/agent", tags=["AI Agent"])
