import json
from google import genai
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.modules.ingestion import models as ingestion_models
from google.api_core.exceptions import ResourceExhausted, InvalidArgument, Unauthenticated
from google.genai.errors import ClientError
import traceback

class AIProvider(ABC):
    @abstractmethod
    def list_models(self, api_key: str) -> List[Dict[str, str]]:
        pass

class GeminiProvider:
    def list_models(self, api_key: str) -> List[Dict[str, str]]:
        try:
            client = genai.Client(api_key=api_key)
            models = []
            for m in client.models.list():
                # Only include models that support content generation
                if 'generateContent' in m.supported_actions:
                    # m.name usually looks like 'models/gemini-1.5-flash'
                    # We strip 'models/' for internal consistency if needed, 
                    # but the error message showed it expecting it.
                    # Let's keep the full name as returned by the API list.
                    models.append({
                        "label": m.display_name or m.name,
                        "value": m.name
                    })
            return models
        except Exception as e:
            pass
            return []

    def generate_analysis(self, config: ingestion_models.AIConfiguration, summary_data: str) -> Optional[str]:
        if not config.api_key:
            return None
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        
        prompt = (
            "You are a professional financial advisor. Analyze the following financial summary data for a household. "
            "Provide 3-4 concise, actionable insights or observations. Focus on spending patterns, budget health, and savings opportunities. "
            "Keep it friendly and professional. Use bullet points. "
            f"\n\nFINANCIAL SUMMARY:\n{summary_data}"
        )
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text if response else None
        except Exception as e:
            pass
            return None

    def generate_structured_insights(self, config: ingestion_models.AIConfiguration, summary_data: str) -> Optional[List[Dict[str, Any]]]:
        if not config.api_key:
            return None
            
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        
        prompt = (
            "You are a sophisticated personal finance analyst. Analyze the provided budget and spending data, which includes:"
             "- Current Month Breakdown (Categories & Overview)"
             "- Last Month Overview (Use for trend comparison)"
             "- Year-to-Date (YTD) Totals (Use for long-term health check)"
            
            "Identify the 5 most critical financial observations/patterns. Look for:"
            "1. Month-over-Month Trends (e.g., 'Spending is down 15% vs last month')."
            "2. Category Anomalies (e.g., 'Dining Out is 2x higher than usual')."
            "3. Progress vs YTD (e.g., 'You have saved 20% of your income this year')."
            "4. Budget Adherence (e.g., 'Excellent discipline in Groceries')."
            "5. Forward-looking risks based on current pace."
            
            "Return a JSON list of exactly 5 insights. Each insight must be a JSON object with: "
            "'id' (unique string), 'type' (one of: danger, warning, success, info), 'title' (short, punchy headline), "
            "'content' (1 concise sentence explaining the observation and specific actionable advice), 'icon' (a relevant emoji). "
            f"\n\nFINANCIAL DATA:\n{summary_data}"
        )
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=f"{prompt}\n\nRESPONSE FORMAT: JSON Array of objects."
            )
            if not response or not response.text:
                return None
                
            text = response.text
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except ClientError as e:
            if e.code == 429 or "RESOURCE_EXHAUSTED" in str(e):
                return [{
                    "id": "ai_quota",
                    "type": "warning",
                    "title": "AI Quota Exceeded",
                    "content": "You've hit the usage limit for the free Gemini API. Insights will refresh later.",
                    "icon": "hourglass_empty"
                }]
            elif e.code in [400, 401, 403]:
                return [{
                    "id": "ai_auth_error",
                    "type": "danger",
                    "title": "AI Configuration Error",
                    "content": "Your API Key appears to be invalid or expired. Please check your settings.",
                    "icon": "key_off",
                    "action": "settings"
                }]
            logger.error(f"AI ClientError: {e}")
            pass
        except ResourceExhausted:
            return [{
                "id": "ai_quota",
                "type": "warning",
                "title": "AI Quota Exceeded",
                "content": "You've hit the usage limit for the free Gemini API. Insights will refresh later.",
                "icon": "hourglass_empty"
            }]
        except (InvalidArgument, Unauthenticated):
            return [{
                "id": "ai_auth_error",
                "type": "danger",
                "title": "AI Configuration Error",
                "content": "Your API Key appears to be invalid or expired. Please check your settings.",
                "icon": "key_off",
                "action": "settings"
            }]
        except Exception as e:
            logger.error(f"AI Generation Error: {e}")
            traceback.print_exc()
            pass
        return None

    def generate_loan_advice(self, config: ingestion_models.AIConfiguration, loan_details: str) -> Optional[str]:
        if not config.api_key:
            return None
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        
        prompt = (
            "You are a sophisticated financial planner. Analyze the following loan details provided by the user. "
            "Provide a comprehensive assessment including:\n"
            "1. Interest Rate Analysis: Is it high/low compared to current market standards (assume India region)?\n"
            "2. Prepayment Strategy: Suggest if/how they should prepay to save interest.\n"
            "3. Repayment Burden: Comment on the EMI burden if any salary info is implied (or give generic advice).\n"
            "4. Actionable Tips: Specific steps to close this loan faster.\n"
            "Format the output as clean Markdown with headers."
            f"\n\nLOAN DETAILS:\n{loan_details}"
        )
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text if response else None
        except Exception:
            return None

    def generate_loans_overview_advice(self, config: ingestion_models.AIConfiguration, loans_data: str) -> Optional[str]:
        if not config.api_key:
            return None
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        
        prompt = (
            "You are a sophisticated financial planner. Analyze the following list of active loans for a household. "
            "Provide a high-level summary and strategic advice including:\n"
            "1. Portfolio Risk: Identify if they are over-leveraged or have high-interest debt mix.\n"
            "2. Consolidation Opportunities: Should they consider consolidating multiple loans?\n"
            "3. Debt Snowball/Avalanche: Which loan should they prioritize paying off first and why?\n"
            "4. Monthly Cashflow Impact: Overall impact of EMIs on their financial flexibility.\n"
            "Format the output as clean Markdown with bullet points and headers."
            f"\n\nLOANS DATA:\n{loans_data}"
        )
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text if response else None
        except Exception:
            return None

    def batch_clean_merchant_names(self, config: ingestion_models.AIConfiguration, descriptions: List[str]) -> Optional[Dict[str, str]]:
        if not config.api_key or not descriptions:
            return None
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        
        prompt = (
            "You are a transaction mapping expert. Given a list of noisy bank transaction descriptions, "
            "extract the clean, canonical merchant name for each. Remove transaction IDs, dates, UPI handles, and location codes. "
            "Examples:\n"
            "- 'UPI/ZOMATO/TXN123/BANGALORE' -> 'Zomato'\n"
            "- 'SWIGGY*ORDER_99' -> 'Swiggy'\n"
            "- 'AMAZON PAY INDIA PAYMT' -> 'Amazon'\n\n"
            "Return a JSON object where the key is the original description and the value is the clean merchant name."
            f"\n\nDESCRIPTIONS:\n{json.dumps(descriptions)}"
        )
        
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=f"{prompt}\n\nRESPONSE FORMAT: JSON Object."
            )
            if not response or not response.text:
                return None
            
            text = response.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except Exception:
            return None

class AIService:
    _providers = {
        "gemini": GeminiProvider()
    }

    @classmethod
    def get_settings(cls, db: Session, tenant_id: str) -> Optional[Dict[str, Any]]:
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id
        ).first()
        if not config: return None
        return {
            "provider": config.provider,
            "model_name": config.model_name,
            "is_enabled": config.is_enabled,
            "prompts": json.loads(config.prompts_json or "{}"),
            "has_api_key": bool(config.api_key)
        }

    @classmethod
    def get_raw_api_key(cls, db: Session, tenant_id: str) -> Optional[str]:
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id
        ).first()
        return config.api_key if config else None


    @classmethod
    def list_available_models(cls, db: Session, tenant_id: str, provider_name: str, api_key_override: Optional[str] = None) -> List[Dict[str, str]]:
        # 1. Get API Key (either from override or DB)
        api_key = api_key_override
        if not api_key:
            config = db.query(ingestion_models.AIConfiguration).filter(
                ingestion_models.AIConfiguration.tenant_id == tenant_id
            ).first()
            if config:
                api_key = config.api_key
        
        if not api_key:
            return []

        # 2. Call Provider
        provider = cls._providers.get(provider_name.lower())
        if not provider:
            return []
            
        return provider.list_models(api_key)

    @classmethod
    def generate_summary_insights(cls, db: Session, tenant_id: str, summary_data: Dict[str, Any]) -> Optional[str]:
        # 1. Get Config
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if not config:
            return "AI Insights are currently disabled in settings."

        # 2. Call Provider
        provider = cls._providers.get(config.provider.lower())
        if not provider or not hasattr(provider, 'generate_analysis'):
            return "AI Provider not configured correctly."

        # Convert summary to string for the prompt
        summary_str = json.dumps(summary_data, indent=2, default=str)
        
        return provider.generate_analysis(config, summary_str)

    @classmethod
    def generate_structured_insights(cls, db: Session, tenant_id: str, summary_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        # 1. Get Config
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if not config:
            return None

        # 2. Call Provider
        provider = cls._providers.get(config.provider.lower())
        if not provider or not hasattr(provider, 'generate_structured_insights'):
            return None

        # Convert summary to string for the prompt
        summary_str = json.dumps(summary_data, indent=2, default=str)
        
        return provider.generate_structured_insights(config, summary_str)

    @classmethod
    def generate_loan_insights(cls, db: Session, tenant_id: str, loan_data: Dict[str, Any]) -> Optional[str]:
        # 1. Get Config
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if not config:
            return "AI Insights are currently disabled in settings."

        # 2. Call Provider
        provider = cls._providers.get(config.provider.lower())
        if not provider or not hasattr(provider, 'generate_loan_advice'):
            return "AI Provider not configured correctly."

        # Convert summary to string for the prompt
        details_str = json.dumps(loan_data, indent=2, default=str)
        
        return provider.generate_loan_advice(config, details_str)

    @classmethod
    def generate_loans_overview_insights(cls, db: Session, tenant_id: str, loans_data: List[Dict[str, Any]]) -> Optional[str]:
        # 1. Get Config
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if not config:
            return "AI Insights are currently disabled in settings."

        # 2. Call Provider
        provider = cls._providers.get(config.provider.lower())
        if not provider or not hasattr(provider, 'generate_loans_overview_advice'):
            return "AI Provider not configured correctly."

        # Convert summary to string for the prompt
        data_str = json.dumps(loans_data, indent=2, default=str)
        
        return provider.generate_loans_overview_advice(config, data_str)

    @classmethod
    def clean_merchant_names(cls, db: Session, tenant_id: str, descriptions: List[str]) -> Dict[str, str]:
        """
        Extract clean merchant names from noisy descriptions. 
        Uses AI if available, else falls back to heuristics.
        """
        if not descriptions: return {}

        # 1. Try AI
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if config:
            provider = cls._providers.get(config.provider.lower())
            if provider and hasattr(provider, 'batch_clean_merchant_names'):
                cleaned = provider.batch_clean_merchant_names(config, descriptions)
                if cleaned: return cleaned

        # 2. Fallback to Heuristics
        results = {}
        for d in descriptions:
            results[d] = cls.heuristic_clean_merchant(d)
        return results

    @staticmethod
    def heuristic_clean_merchant(description: str) -> str:
        import re
        if not description: return "Unknown"
        # Remove UPI/ prefixes
        clean = re.sub(r'^UPI/', '', description, flags=re.I)
        # Remove everything after the second / if it exists
        parts = clean.split('/')
        if len(parts) > 1:
            clean = parts[0]
        # Remove common Junk
        clean = re.sub(r'[0-9]{5,}', '', clean) # long numbers
        clean = re.sub(r'\*.*', '', clean) # remove content after *
        # Clean special chars but keep space
        clean = re.sub(r'[^a-zA-Z\s]', ' ', clean)
        # Trim and Title
        clean = ' '.join(clean.split()).title()
        return clean or "Unknown"
