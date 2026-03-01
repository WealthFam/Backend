from fastapi import APIRouter
from backend.app.api.v1 import mobile

api_router = APIRouter()
api_router.include_router(mobile.router, prefix="/mobile", tags=["Mobile"])
