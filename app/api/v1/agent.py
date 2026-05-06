from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import httpx
import logging
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def proxy_agent_chat(
    payload: Dict[str, Any],
    request: Request,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proxies chat requests to the AI Agent microservice.
    Injects tenant_id and passes through Authorization header.
    """
    if settings.DISABLE_AI_AGENT:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Strategic AI Advisor is currently disabled for this environment."
        )
    message = payload.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    # Inject multi-tenant context into the payload
    payload["tenant_id"] = str(current_user.tenant_id)
    payload["user_id"] = str(current_user.id)

    # Extract original Authorization header to pass through
    auth_header = request.headers.get("Authorization")
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.AGENT_SERVICE_URL}/chat",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"Agent service error: {response.status_code} - {response.text}")
                # Try to return the agent's error detail if available
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", "AI Agent service error.")
                except:
                    detail = "AI Agent service error."
                raise HTTPException(status_code=response.status_code, detail=detail)
            
            return response.json()

    except httpx.ConnectError:
        logger.error(f"Could not connect to AI Agent service at {settings.AGENT_SERVICE_URL}")
        raise HTTPException(
            status_code=503, 
            detail="AI Agent service is currently unreachable."
        )
    except Exception as e:
        logger.error(f"Unexpected error in agent proxy: {e}")
        raise HTTPException(status_code=500, detail="Internal server error in AI proxy.")
