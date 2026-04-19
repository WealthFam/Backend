import json
import logging
import re
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from google import genai
from google.api_core.exceptions import InvalidArgument, ResourceExhausted, Unauthenticated
from google.genai.errors import ClientError
from sqlalchemy.orm import Session

from backend.app.modules.ingestion import models as ingestion_models
from backend.app.core import timezone
from backend.app.core.database import db_write_lock

logger = logging.getLogger(__name__)


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
                if 'generateContent' in m.supported_actions:
                    models.append({
                        "label": m.display_name or m.name,
                        "value": m.name
                    })
            return models
        except Exception as e:
            logger.error(f"Gemini list_models error: {e}")
            return []

    def generate_analysis(self, config: ingestion_models.AIConfiguration, summary_data: str) -> Optional[str]:
        if not config.api_key:
            logger.error("Gemini generate_analysis: API Key is MISSING in config")
            return None
        
        logger.info(f"Gemini generate_analysis: API Key is present. Model name: {config.model_name}")
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"
        
        prompt = (
            "You are a top-tier personal finance analyst. Analyze the following household financial data. "
            "Provide exactly 3 highly compact, actionable insights without any fluff. "
            "CRITICAL FORMAT RULES:\n"
            "- Output ONLY 3 bullet points. Do not include any introductory text or concluding remarks.\n"
            "- Each bullet point MUST be a maximum of 2 sentences.\n"
            "- Start each bullet with a bolded 2-4 word micro-headline (e.g., **Category Spike:**).\n"
            "CRITICAL CONTENT RULES:\n"
            "- Focus on identifying anomalies, budget adherence trends, and specific savings strategies.\n"
            "- The user is on a fixed salary. DO NOT mention low income, zero income, budget deficits, or spending exceeding income.\n"
            "- Base all analysis STRICTLY on the numbers provided for the specific 'timeframe_filter'.\n"
            "- When formatting currency, ALWAYS use the Indian Rupee symbol (₹) and INR formatting (e.g., ₹10,000).\n"
            f"\n\nFINANCIAL SUMMARY:\n{summary_data}"
        )
        
        try:
            logger.info(f"Generating Gemini analysis with model: {model_id}")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text if response else None
        except Exception as e:
            logger.error(f"Gemini generate_analysis error: {e}")
            return None

    def generate_structured_insights(self, config: ingestion_models.AIConfiguration, summary_data: str, db: Session, tenant_id: str, force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        if not config.api_key:
            logger.error("Gemini generate_structured_insights: API Key is MISSING in config")
            return None
            
        # Check Cache First (if not forced to refresh)
        if not force_refresh:
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == "dashboard_summary"
            ).first()
            if cached and cached.content:
                # Check if it's less than 24 hours old
                if cached.updated_at:
                    age = (timezone.utcnow() - cached.updated_at).total_seconds()
                    if age < 86400: # 24 hours
                        try:
                            insights = json.loads(cached.content)
                            if isinstance(insights, list):
                                for insight in insights:
                                    insight['is_cached'] = True
                            return insights
                        except Exception as cache_err:
                            logger.error(f"Error parsing recent cached insights: {cache_err}")
            
        logger.info(f"Gemini generate_structured_insights: API Key is present. Model name: {config.model_name}")
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"
        
        prompt = (
            "You are a sophisticated personal finance analyst. Analyze the provided budget and spending data, which includes:"
             "- Date Range & Filtering Context (timeframe_filter, account_filtered)"
             "- Category Breakdown & Trends"
            
            "Identify the 5 most critical financial observations/patterns. Look for:"
             "1. Pattern Anomalies (e.g., 'Dining Out is 2x higher than usual')."
             "2. Budget Adherence (e.g., 'Excellent discipline in Groceries')."
             "3. Spending velocity & pacing based on the timeframe."
             "4. Forward-looking risks based entirely on the spending rate."
             "5. Actionable savings opportunities."
             
             "CRITICAL RULES:"
             "- The user is on a fixed salary. ABSOLUTELY DO NOT mention low income, zero income, budget deficits, or spending exceeding income."
             "- Base all analysis STRICTLY on the numbers provided and respect the 'timeframe_filter' indicated. Do not assume the data is for a full month if the timeframe indicates otherwise."
             "- ALWAYS format any currency values with the Indian Rupee symbol (₹) and standard INR numbering format (e.g., ₹10,000)."
            
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
                logger.warning("Gemini structured insights: Quota exceeded, attempting to use cache")
                cached = db.query(ingestion_models.AIInsightCache).filter(
                    ingestion_models.AIInsightCache.tenant_id == tenant_id,
                    ingestion_models.AIInsightCache.insight_type == "dashboard_summary"
                ).first()
                if cached and cached.content:
                    try:
                        insights = json.loads(cached.content)
                        # Add a flag that this is cached data
                        if isinstance(insights, list) and len(insights) > 0:
                            for insight in insights:
                                insight['is_cached'] = True
                            insights = [i for i in insights if i.get('id') != 'ai_quota']
                        return insights
                    except Exception as cache_err:
                        logger.error(f"Error parsing cached insights: {cache_err}")

                return None
            elif e.code in [400, 401, 403]:
                logger.error(f"Gemini structured insights: Auth error {e.code}, checking cache fallback")
                cached = db.query(ingestion_models.AIInsightCache).filter(
                    ingestion_models.AIInsightCache.tenant_id == tenant_id,
                    ingestion_models.AIInsightCache.insight_type == "dashboard_summary"
                ).first()
                if cached and cached.content:
                    try:
                        insights = json.loads(cached.content)
                        if isinstance(insights, list) and len(insights) > 0:
                            for insight in insights:
                                insight['is_cached'] = True
                            return insights
                    except: pass

                return [{
                    "id": "ai_auth_error",
                    "type": "danger",
                    "title": "AI Configuration Error",
                    "content": "Your API Key appears to be invalid or expired. Please check your settings.",
                    "icon": "key_off",
                    "action": "settings"
                }]
            logger.error(f"AI ClientError in structured insights: {e}")
            logger.error(traceback.format_exc())
        except ResourceExhausted:
            logger.warning("Gemini structured insights: ResourceExhausted, attempting to use cache")
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == "dashboard_summary"
            ).first()
            if cached and cached.content:
                try:
                    insights = json.loads(cached.content)
                    if isinstance(insights, list) and len(insights) > 0:
                        for insight in insights:
                            insight['is_cached'] = True
                        insights = [i for i in insights if i.get('id') != 'ai_quota']
                    return insights
                except Exception as cache_err:
                    logger.error(f"Error parsing cached insights: {cache_err}")
            
            return None
        except (InvalidArgument, Unauthenticated):
            logger.error("Gemini structured insights: Auth exception, checking cache fallback")
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == "dashboard_summary"
            ).first()
            if cached and cached.content:
                try:
                    insights = json.loads(cached.content)
                    if isinstance(insights, list) and len(insights) > 0:
                        for insight in insights:
                            insight['is_cached'] = True
                        return insights
                except: pass

            return [{
                "id": "ai_auth_error",
                "type": "danger",
                "title": "AI Configuration Error",
                "content": "Your API Key appears to be invalid or expired. Please check your settings.",
                "icon": "key_off",
                "action": "settings"
            }]
        except Exception as e:
            logger.error(f"AI Generation Error in structured insights: {e}")
            logger.error(traceback.format_exc())
        return None

    def generate_loan_advice(
        self, config: ingestion_models.AIConfiguration, loan_details: str
    ) -> Optional[str]:
        if not config.api_key:
            return None

        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        prompt = (
            "You are a top-tier financial strategist and 'Wealth Shredder'. "
            "Your goal is to help the user eliminate their debt as aggressively "
            "and efficiently as possible. "
            "Analyze the provided loan details and, CRITICALLY, the strategic "
            "prepayment simulations.\n\n"
            "Provide a high-impact, mathematically-driven assessment including:\n"
            "1. THE SHREDDER STRATEGY: Compare the 'Standard' path with the provided "
            "'Scenarios'. Identify which scenario offers the best "
            "'Interest Savings per Rupee Invested'.\n"
            "2. THE COST OF DELAY: Calculate how much interest is literally being "
            "thrown away every day/month if they do NOT take action.\n"
            "3. STRATEGIC TIP: One non-obvious, mathematically sound tip to close "
            "this specific loan faster.\n"
            "4. CALL TO ACTION: A punchy, definitive closing statement on how many "
            "months and how much money they will reclaim.\n\n"
            "Format the output as clean Markdown. Use bolding for numbers. "
            "Be direct, aggressive towards debt, and highly precise."
            f"\n\nLOAN & SIMULATION DATA:\n{loan_details}"
        )

        try:
            logger.info(f"Generating Gemini loan advice with model: {model_id}")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text if response else "No response from AI."
        except Exception as e:
            logger.error(f"Gemini loan advice error: {e}")
            raise e

    def generate_loans_overview_advice(
        self, config: ingestion_models.AIConfiguration, loans_data: str
    ) -> Optional[str]:
        if not config.api_key:
            return None
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"
            
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
            logger.info(f"Generating Gemini loans overview with model: {model_id}")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            return response.text if response else "No response from AI."
        except Exception as e:
            logger.error(f"Gemini loans overview advice error: {e}")
            raise e

    def generate_mutual_fund_advice(
        self, config: ingestion_models.AIConfiguration, portfolio_data: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generates a hybrid strategic brief for mutual fund portfolios.
        Returns a dict: { 'summary': 'Markdown text', 'highlights': [ {id, type, title, content, icon} ] }
        """
        if not config.api_key:
            return None

        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"

        prompt = (
            "You are an elite 'AI Advisor' specializing in HNI mutual fund management. "
            "Analyze the portfolio and benchmarks, then return a HYBRID advisor brief in JSON format.\n\n"
            "1. MANDATORY SYMBOL MAPPING: Use these symbols for Markdown headers in the summary:\n"
            "   - 🎯 EXECUTIVE SUMMARY\n"
            "   - 📈 ALPHA & BENCHMARKING\n"
            "   - ⚖️ RECOMMENDED ACTIONS\n"
            "   - 🛡️ RISK GUARDRAILS\n"
            "2. MATH PRECISION: Bold all financial amounts, percentages, and performance deltas (e.g., **+15.2%**, **₹1.2Cr**) to ensure high-contrast rendering.\n"
            "3. ADVISE & SUGGEST: Provide 3-4 specific, actionable suggestions. These must be explicit, e.g., 'Consolidate redundant Large Cap funds'.\n\n"
            "JSON STRUCTURE:\n"
            "1. 'summary': A high-fidelity Markdown narrative (approx. 200 words). Include a '📈 ALPHA & BENCHMARKING' section comparing portfolio vs Nifty/Sensex.\n"
            "2. 'highlights': 4-5 high-impact cards for current status. Each card needs: 'id' (unique), 'type' (success, warning, danger, info), 'title' (punchy), 'content' (1 direct sentence), 'icon' (relevant emoji).\n"
            "3. 'suggestions': 3-4 action cards. Each needs: 'id' (unique), 'title' (action-oriented), 'content' (1 direct sentence rationale), 'priority' (high, medium, low).\n\n"
            "Tone: Authoritative, Mathematically-Aggressive, and Precise."
            f"\n\nPORTFOLIO & MARKET DATA:\n{portfolio_data}"
        )

        try:
            logger.info(f"Generating Gemini hybrid brief with model: {model_id}")
            response = client.models.generate_content(
                model=model_id,
                contents=f"{prompt}\n\nRESPONSE FORMAT: Valid JSON Object with 'summary' and 'highlights' keys."
            )
            if not response or not response.text:
                return {"summary": "Strategist is synthesizing offline.", "highlights": []}
            
            text = response.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
            
            return {"summary": text, "highlights": []} # Fallback if JSON fails
        except Exception as e:
            logger.error(f"Gemini mutual fund brief error: {e}")
            raise e

    def batch_clean_merchant_names(self, config: ingestion_models.AIConfiguration, descriptions: List[str]) -> Optional[Dict[str, str]]:
        if not config.api_key or not descriptions:
            return None
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"
        
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
            logger.info(f"Gemini batch cleaning {len(descriptions)} merchants with model: {model_id}")
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
        except Exception as e:
            logger.error(f"Gemini batch_clean_merchant_names error: {e}")
            return None

    def auto_parse_transaction(self, config: ingestion_models.AIConfiguration, content: str) -> Optional[Dict[str, Any]]:
        if not config.api_key or not content:
            return None
        
        # Test Environment Mocking
        if config.api_key == "MOCK_KEY_FOR_TESTING" or "MOCK" in config.api_key.upper():
            logger.info("AI: Using simulated extraction for Mock Key")
            return {
                "amount": 1250.50,
                "date": timezone.utcnow().isoformat(),
                "recipient": "Blue Tokai (Simulated)",
                "category": "Dining Out",
                "account_mask": "9988",
                "ref_id": "TXN_SIM_123",
                "type": "DEBIT"
            }
        
        client = genai.Client(api_key=config.api_key)
        model_id = config.model_name or "gemini-1.5-flash"
        if not model_id.startswith("models/"):
            model_id = f"models/{model_id}"
        
        # Get custom prompt if available, else use default
        prompts = json.loads(config.prompts_json or "{}")
        base_prompt = prompts.get("parsing", (
            "Extract transaction details from the following message. "
            "Return exactly one JSON object with: "
            "amount (number), date (ISO 8601 string), recipient (string), category (string), account_mask (last 4 digits), ref_id (string or null), type (DEBIT/CREDIT)."
        ))
        
        try:
            logger.info(f"Gemini auto-parsing transaction with model: {model_id}")
            response = client.models.generate_content(
                model=model_id,
                contents=f"{base_prompt}\n\nRAW MESSAGE:\n{content}\n\nRESPONSE FORMAT: Single JSON Object."
            )
            if not response or not response.text:
                return None
            
            text = response.text
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except ClientError:
            raise
        except Exception as e:
            logger.error(f"Gemini auto_parse_transaction error: {e}")
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
        api_key = api_key_override
        if not api_key:
            config = db.query(ingestion_models.AIConfiguration).filter(
                ingestion_models.AIConfiguration.tenant_id == tenant_id
            ).first()
            if config:
                api_key = config.api_key
        
        if not api_key:
            return []

        provider = cls._providers.get(provider_name.lower())
        if not provider:
            return []
            
        return provider.list_models(api_key)

    @classmethod
    def generate_summary_insights(cls, db: Session, tenant_id: str, summary_data: Dict[str, Any], force_refresh: bool = False) -> Optional[str]:
        cache_type = "dashboard_summary_text"
        
        # 1. Cache Check
        if not force_refresh:
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content

        # 2. Provider Fetch
        try:
            config = db.query(ingestion_models.AIConfiguration).filter(
                ingestion_models.AIConfiguration.tenant_id == tenant_id,
                ingestion_models.AIConfiguration.is_enabled == True
            ).first()

            if not config:
                return "Dashboard intelligence is currently disabled."

            provider = cls._providers.get(config.provider.lower())
            if not provider or not hasattr(provider, 'generate_analysis'):
                return "AI Consultant not configured."

            summary_str = json.dumps(summary_data, indent=2, default=str)
            logger.info(f"AIService: Generating AI analysis for tenant {tenant_id}")
            result = provider.generate_analysis(config, summary_str)

            if result:
                with db_write_lock:
                    try:
                        # Update Cache
                        cached = db.query(ingestion_models.AIInsightCache).filter(
                            ingestion_models.AIInsightCache.tenant_id == tenant_id,
                            ingestion_models.AIInsightCache.insight_type == cache_type
                        ).first()
                        if cached:
                            cached.content = result
                            cached.updated_at = timezone.utcnow()
                        else:
                            new_cache = ingestion_models.AIInsightCache(
                                tenant_id=tenant_id,
                                insight_type=cache_type,
                                content=result
                            )
                            db.add(new_cache)
                        db.commit()
                        return result
                    except Exception as catch_err:
                        db.rollback()
                        logger.error(f"Error caching summary insights: {catch_err}")
                        return result
        except Exception as e:
            db.rollback()
            logger.warning(f"AI Refresh failed for dashboard summary: {e}")
            # Fallback to cache
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content
            
            return "Strategy Advisor: System is currently analyzing offline. Check your AI key or quota for fresh insights."

        return None

    @classmethod
    def generate_structured_insights(cls, db: Session, tenant_id: str, summary_data: Dict[str, Any], force_refresh: bool = False) -> Optional[List[Dict[str, Any]]]:
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if not config:
            return None

        provider = cls._providers.get(config.provider.lower())
        if not provider or not hasattr(provider, 'generate_structured_insights'):
            return None

        summary_str = json.dumps(summary_data, indent=2, default=str)
        
        result = provider.generate_structured_insights(config, summary_str, db, tenant_id, force_refresh)
        
        # Cache successful results
        if result and len(result) > 0 and result[0].get('id') != 'ai_quota' and result[0].get('id') != 'ai_auth_error':
            with db_write_lock:
                try:
                    cached = db.query(ingestion_models.AIInsightCache).filter(
                        ingestion_models.AIInsightCache.tenant_id == tenant_id,
                        ingestion_models.AIInsightCache.insight_type == "dashboard_summary"
                    ).first()
                    
                    content_str = json.dumps(result)
                    if cached:
                        cached.content = content_str
                        cached.updated_at = timezone.utcnow()
                    else:
                        new_cache = ingestion_models.AIInsightCache(
                            tenant_id=tenant_id,
                            insight_type=dashboard_cache_type if 'dashboard_cache_type' in locals() else "dashboard_summary",
                            content=content_str
                        )
                        db.add(new_cache)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Error caching structured insights: {e}")
                
        return result

    @classmethod
    def generate_loan_insights(cls, db: Session, tenant_id: str, loan_data: Dict[str, Any], force_refresh: bool = False) -> Optional[str]:
        cache_type = f"loan_details_{loan_data.get('id')}"
        
        # 1. Cache Check
        if not force_refresh:
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content

        # 2. Provider Fetch
        try:
            config = db.query(ingestion_models.AIConfiguration).filter(
                ingestion_models.AIConfiguration.tenant_id == tenant_id,
                ingestion_models.AIConfiguration.is_enabled == True
            ).first()

            if not config:
                return "Strategic insights are disabled."

            provider = cls._providers.get(config.provider.lower())
            if not provider or not hasattr(provider, 'generate_loan_advice'):
                return "AI Strategic Planner not configured."

            details_str = json.dumps(loan_data, indent=2, default=str)
            result = provider.generate_loan_advice(config, details_str)

            if result:
                with db_write_lock:
                    try:
                        # Update Cache
                        cached = db.query(ingestion_models.AIInsightCache).filter(
                            ingestion_models.AIInsightCache.tenant_id == tenant_id,
                            ingestion_models.AIInsightCache.insight_type == cache_type
                        ).first()
                        if cached:
                            cached.content = result
                            cached.updated_at = timezone.utcnow()
                        else:
                            new_cache = ingestion_models.AIInsightCache(
                                tenant_id=tenant_id,
                                insight_type=cache_type,
                                content=result
                            )
                            db.add(new_cache)
                        db.commit()
                        return result
                    except Exception as catch_err:
                        db.rollback()
                        logger.error(f"Error caching loan insights: {catch_err}")
                        return result # Still return the result even if cache fails
        except Exception as e:
            db.rollback()
            logger.warning(f"AI Refresh failed for loan {loan_data.get('id')}: {e}")
            # Fallback to cache even if it's stale
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content
            
            return "Precision Plan: AI Strategist is currently offline. Your mathematical simulations are valid below."

        return None

    @classmethod
    def generate_loans_overview_insights(cls, db: Session, tenant_id: str, loans_data: List[Dict[str, Any]], force_refresh: bool = False) -> Optional[str]:
        cache_type = "loans_overview"
        
        # 1. Cache Check
        if not force_refresh:
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content

        # 2. Provider Fetch
        try:
            config = db.query(ingestion_models.AIConfiguration).filter(
                ingestion_models.AIConfiguration.tenant_id == tenant_id,
                ingestion_models.AIConfiguration.is_enabled == True
            ).first()

            if not config:
                return "Wealth Shredder analysis is currently disabled."

            provider = cls._providers.get(config.provider.lower())
            if not provider or not hasattr(provider, 'generate_loans_overview_advice'):
                return "AI Wealth Strategist not configured."

            data_str = json.dumps(loans_data, indent=2, default=str)
            result = provider.generate_loans_overview_advice(config, data_str)

            if result:
                with db_write_lock:
                    try:
                        # Update Cache
                        cached = db.query(ingestion_models.AIInsightCache).filter(
                            ingestion_models.AIInsightCache.tenant_id == tenant_id,
                            ingestion_models.AIInsightCache.insight_type == cache_type
                        ).first()
                        if cached:
                            cached.content = result
                            cached.updated_at = timezone.utcnow()
                        else:
                            new_cache = ingestion_models.AIInsightCache(
                                tenant_id=tenant_id,
                                insight_type=cache_type,
                                content=result
                            )
                            db.add(new_cache)
                        db.commit()
                        return result
                    except Exception as catch_err:
                        db.rollback()
                        logger.error(f"Error caching loans overview: {catch_err}")
                        return result
        except Exception as e:
            db.rollback()
            logger.warning(f"AI Refresh failed for loans overview: {e}")
            # Fallback to cache
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content
            
            return "Strategic Portfolio Analysis: Your Portfolio Strategist is currently analyzing offline. Please verify your credentials or quota."

    @classmethod
    def check_cache(cls, db: Session, tenant_id: str, cache_type: str) -> Optional[Dict[str, Any]]:
        """Helper to quickly check for existing cached insights."""
        cached = db.query(ingestion_models.AIInsightCache).filter(
            ingestion_models.AIInsightCache.tenant_id == tenant_id,
            ingestion_models.AIInsightCache.insight_type == cache_type
        ).first()
        if cached and cached.content:
            try:
                import json
                return json.loads(cached.content)
            except:
                pass
        return None

    @classmethod
    def generate_portfolio_insights(cls, db: Session, tenant_id: str, portfolio_data: List[Dict[str, Any]], force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        cache_type = "mutual_fund_portfolio_v5"
        
        # 1. Cache Check
        cached = cls.check_cache(db, tenant_id, cache_type)
        if not force_refresh and cached:
            return cached

        # 2. Provider Fetch
        try:
            config = db.query(ingestion_models.AIConfiguration).filter(
                ingestion_models.AIConfiguration.tenant_id == tenant_id,
                ingestion_models.AIConfiguration.is_enabled == True
            ).first()

            if not config:
                return "Advisor Insights are currently disabled."

            provider = cls._providers.get(config.provider.lower())
            if not provider or not hasattr(provider, 'generate_mutual_fund_advice'):
                return "AI Advisor not configured."

            data_str = json.dumps(portfolio_data, indent=2, default=str)
            result = provider.generate_mutual_fund_advice(config, data_str)

            if result:
                with db_write_lock:
                    try:
                        content_str = json.dumps(result)
                        # Update Cache
                        cached = db.query(ingestion_models.AIInsightCache).filter(
                            ingestion_models.AIInsightCache.tenant_id == tenant_id,
                            ingestion_models.AIInsightCache.insight_type == cache_type
                        ).first()
                        if cached:
                            cached.content = content_str
                            cached.updated_at = timezone.utcnow()
                        else:
                            new_cache = ingestion_models.AIInsightCache(
                                tenant_id=tenant_id,
                                insight_type=cache_type,
                                content=content_str
                            )
                            db.add(new_cache)
                        db.commit()
                        return result
                    except Exception as catch_err:
                        db.rollback()
                        logger.error(f"Error caching portfolio insights: {catch_err}")
                        return result
                    except Exception as catch_err:
                        db.rollback()
                        logger.error(f"Error caching portfolio insights: {catch_err}")
                        return result
        except Exception as e:
            db.rollback()
            logger.warning(f"AI Refresh failed for mutual fund portfolio: {e}")
            # Fallback to cache
            cached = db.query(ingestion_models.AIInsightCache).filter(
                ingestion_models.AIInsightCache.tenant_id == tenant_id,
                ingestion_models.AIInsightCache.insight_type == cache_type
            ).first()
            if cached:
                return cached.content
            
            return "Portfolio Intelligence: Your Strategic Architect is currently offline. Please verify your credentials or quota."

        return None

    @classmethod
    def auto_parse_transaction(cls, db: Session, tenant_id: str, content: str) -> Optional[Dict[str, Any]]:
        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if not config:
            return None

        provider = cls._providers.get(config.provider.lower())
        if not provider or not hasattr(provider, 'auto_parse_transaction'):
            return None

        return provider.auto_parse_transaction(config, content)

    @classmethod
    def clean_merchant_names(cls, db: Session, tenant_id: str, descriptions: List[str]) -> Dict[str, str]:
        """
        Extract clean merchant names from noisy descriptions. 
        Uses AI if available, else falls back to heuristics.
        """
        if not descriptions: return {}

        config = db.query(ingestion_models.AIConfiguration).filter(
            ingestion_models.AIConfiguration.tenant_id == tenant_id,
            ingestion_models.AIConfiguration.is_enabled == True
        ).first()

        if config:
            provider = cls._providers.get(config.provider.lower())
            if provider and hasattr(provider, 'batch_clean_merchant_names'):
                cleaned = provider.batch_clean_merchant_names(config, descriptions)
                if cleaned: return cleaned

        results = {}
        for d in descriptions:
            results[d] = cls.heuristic_clean_merchant(d)
        return results

    @staticmethod
    def heuristic_clean_merchant(description: str) -> str:
        if not description: return "Unknown"
        
        # 1. Remove common noise patterns
        # Handle "Vpa Q12345..." and similar UPI prefixes
        clean = re.sub(r'^(UPI/|VPA\s*Q[0-9]{3,}\s*|IMPS/|NEFT/|RTGS/|TRANSFER\s+TO\s+|TRANSFER\s+FROM\s+)', '', description, flags=re.I)
        
        # 2. Handle common bank formats like "NAME/TXN123/BANK"
        if '/' in clean:
            parts = clean.split('/')
            # Use the longest alphabetical part or first part if alphabetical
            valid_parts = [p.strip() for p in parts if len(p.strip()) >= 3 and not p.strip().isdigit()]
            if valid_parts:
                clean = valid_parts[0]
            else:
                clean = parts[0]

        # 3. Remove common Junk (trailing IDs, stars, long numbers)
        clean = re.sub(r'[0-9]{8,}', '', clean) # long numbers
        clean = re.sub(r'\s+[0-9]{4,}\s+', ' ', clean) # mid-string numbers
        clean = re.sub(r'\*.*', '', clean) # remove content after *
        
        # 4. Final string cleanup
        clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', clean)
        clean = ' '.join(clean.split()).title()
        
        # Minimum characters check
        if len(clean) < 3:
            # Fallback to original description but stripped of special chars if it's too aggressive
            alt = re.sub(r'[^a-zA-Z0-9\s]', ' ', description)
            alt = ' '.join(alt.split()).title()
            # If fallback is still purely numeric or too short, return Unknown
            if len(alt) < 3 or alt.replace(' ', '').isdigit():
                return "Unknown"
            return alt
            
        return clean
