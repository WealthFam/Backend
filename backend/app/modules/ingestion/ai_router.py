from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.ingestion import models as ingestion_models
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Settings"])

class AISettingsUpdate(BaseModel):
    provider: str
    model_name: str
    api_key: Optional[str] = None
    is_enabled: bool
    prompts: Dict[str, str]

class AISettingsRead(BaseModel):
    provider: str
    model_name: str
    is_enabled: bool
    prompts: Dict[str, str]
    has_api_key: bool

@router.get("/settings", response_model=AISettingsRead)
def get_ai_settings(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(ingestion_models.AIConfiguration).filter(
        ingestion_models.AIConfiguration.tenant_id == str(current_user.tenant_id)
    ).first()

    if not config:
        # Return defaults
        return {
            "provider": "gemini",
            "model_name": "gemini-pro",
            "is_enabled": False,
            "prompts": {
                "parsing": "Extract transaction details from the following message. Return JSON with: amount (number), date (DD/MM/YYYY), recipient (string), account_mask (4 digits), ref_id (string or null), type (DEBIT/CREDIT)."
            },
            "has_api_key": False
        }

    return {
        "provider": config.provider,
        "model_name": config.model_name,
        "is_enabled": config.is_enabled,
        "prompts": json.loads(config.prompts_json or "{}"),
        "has_api_key": bool(config.api_key)
    }

@router.post("/settings")
def update_ai_settings(
    payload: AISettingsUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(ingestion_models.AIConfiguration).filter(
        ingestion_models.AIConfiguration.tenant_id == str(current_user.tenant_id)
    ).first()

    if not config:
        config = ingestion_models.AIConfiguration(
            tenant_id=str(current_user.tenant_id)
        )
        db.add(config)

    config.provider = payload.provider
    config.model_name = payload.model_name
    config.is_enabled = payload.is_enabled
    config.prompts_json = json.dumps(payload.prompts)
    
    if payload.api_key:
        config.api_key = payload.api_key

    db.commit()
    
    # Sync with External Parser
    try:
        from backend.app.modules.ingestion.parser_service import ExternalParserService
        ExternalParserService.sync_ai_config(
            tenant_id=str(current_user.tenant_id),
            api_key=config.api_key or "",
            model_name=config.model_name,
            is_enabled=config.is_enabled
        )
    except Exception as e:
        logger.error(f"Failed to sync AI config: {e}")

    return {"status": "updated"}

@router.post("/test")
def test_ai_connection(
    payload: Dict[str, str],
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    content = payload.get("content", "Test transaction: Spent Rs 500 at Amazon using card XX1234 on 01/01/2024")
    
    # Use generic 'SMS' source for testing as it fits the snippet format best
    try:
         # We use parse_sms as a proxy for generic parsing since content is short text
        res = ExternalParserService.parse_sms(str(current_user.tenant_id), "TEST_SENDER", content)
        
        if res and res.get("status") in ["success", "processed"]:
            results = res.get("results", [])
            if results:
                return {"status": "success", "data": results[0].get("transaction")}
        
        return {"status": "failed", "message": f"Parser returned: {res.get('status') if res else 'None'} - {res}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/models")
def list_ai_models(
    provider: str = "gemini",
    api_key: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.ingestion.ai_service import AIService
    return AIService.list_available_models(db, str(current_user.tenant_id), provider, api_key)

@router.post("/generate-insights")
def generate_insights(
    payload: Dict[str, Any],
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.ingestion.ai_service import AIService
    summary_data = payload.get("summary_data")
    if not summary_data:
        raise HTTPException(status_code=400, detail="Missing summary_data")
    
    insights = AIService.generate_summary_insights(db, str(current_user.tenant_id), summary_data)
    return {"insights": insights}

@router.get("/aliases")
def get_merchant_aliases(
    current_user: auth_models.User = Depends(get_current_user)
):
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    return ExternalParserService.get_aliases(str(current_user.tenant_id))

@router.post("/aliases")
def create_merchant_alias(
    payload: Dict[str, str],
    current_user: auth_models.User = Depends(get_current_user)
):
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    pattern = payload.get("pattern")
    alias = payload.get("alias")
    if not pattern or not alias:
        raise HTTPException(status_code=400, detail="Pattern and alias are required")
    success = ExternalParserService.create_alias(str(current_user.tenant_id), pattern, alias)
    return {"status": "success" if success else "failed"}

@router.delete("/aliases/{alias_id}")
def delete_merchant_alias(
    alias_id: str,
    current_user: auth_models.User = Depends(get_current_user)
):
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    success = ExternalParserService.delete_alias(str(current_user.tenant_id), alias_id)
    return {"status": "success" if success else "failed"}
