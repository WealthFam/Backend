from fastapi import APIRouter
from backend.app.modules.mobile.api.router import router as mobile_router

api_router = APIRouter()
api_router.include_router(mobile_router, prefix="/mobile", tags=["Mobile"])
