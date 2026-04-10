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
from google.genai.errors import ClientError

logger = logging.getLogger(__name__)

def handle_ai_error(e: Exception):
    if isinstance(e, ClientError):
        logger.error(f"Gemini API Error: {e}")
        status = e.code if hasattr(e, 'code') else 500
        
        detail = "AI intelligence is currently unavailable. Please check your settings."
        code = "AI_GENERAL_ERROR"
        err_str = str(e).upper()
        
        if status == 429 or "RESOURCE_EXHAUSTED" in err_str:
            detail = "Quota limit reached for your Gemini API key. Please try again in a few minutes or switch models."
            code = "AI_QUOTA_EXHAUSTED"
        elif status == 401 or "UNAUTHENTICATED" in err_str or "API_KEY_INVALID" in err_str:
            detail = "Authentication failed. Your API key might be invalid or expired."
            code = "AI_AUTH_FAILED"
        elif status == 404 or "NOT_FOUND" in err_str:
            detail = "The requested model was not found in your Google project."
            code = "AI_MODEL_NOT_FOUND"
        elif status == 400 or "INVALID_ARGUMENT" in err_str:
            detail = "The request or data is invalid for the current AI model."
            code = "AI_INVALID_REQUEST"
            
        return HTTPException(status_code=status, detail={"detail": detail, "code": code})
    
    if isinstance(e, HTTPException):
        return e
        
    logger.error(f"Unexpected AI error: {e}")
    return HTTPException(
        status_code=500, 
        detail={"detail": "Intelligence service encountered an unexpected error.", "code": "AI_UNEXPECTED_ERROR"}
    )

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
    api_key: Optional[str] = None
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
        "api_key": config.api_key,
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
    
    try:
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
    
    try:
        insights = AIService.generate_summary_insights(db, str(current_user.tenant_id), summary_data)
        return {"insights": insights}
    except Exception as e:
        raise handle_ai_error(e)

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

@router.post("/training/{message_id}/auto-parse")
def auto_parse_training_message(
    message_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.ingestion.ai_service import AIService
    
    msg = db.query(ingestion_models.UnparsedMessage).filter(
        ingestion_models.UnparsedMessage.id == message_id,
        ingestion_models.UnparsedMessage.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    try:
        content = msg.raw_content or ""
        result = AIService.auto_parse_transaction(db, str(current_user.tenant_id), content)
        
        if not result:
            raise HTTPException(status_code=400, detail="AI parsing failed or AI is disabled.")
            
        return result
    except Exception as e:
        raise handle_ai_error(e)
