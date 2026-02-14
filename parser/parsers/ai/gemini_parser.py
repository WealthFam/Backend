from google import genai
from google.genai import types, errors
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json
from parser.db.models import AIConfig
from parser.schemas.transaction import Transaction, TransactionType, AccountInfo, MerchantInfo
from datetime import datetime
from decimal import Decimal

class GeminiParser:
    def __init__(self, db: Session):
        self.db = db
        self.config = self._get_config()

    def _get_config(self) -> Optional[AIConfig]:
        return self.db.query(AIConfig).first()

    def parse(self, content: str, source: str, date_hint: Optional[Any] = None) -> Optional[Transaction]:
        if not self.config:
            return None
            
        if not self.config.is_enabled:
            return None
            
        if not self.config.api_key_enc:
            return None

        # New google-genai client
        client = genai.Client(api_key=self.config.api_key_enc)
        
        config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=1,
            top_k=32,
            max_output_tokens=1024,
            response_mime_type="application/json",
        )

        model_id = self.config.model_name or "gemini-1.5-flash"

        # Determine reference date
        ref_date = datetime.now()
        if date_hint and isinstance(date_hint, datetime):
            ref_date = date_hint
        elif date_hint and isinstance(date_hint, str):
             try:
                 ref_date = datetime.fromisoformat(date_hint)
             except: pass
             
        ref_date_str = ref_date.strftime('%Y-%m-%d')

        # Standard Prompt
        prompt = rf"""
        You are a precise financial parser. Extract transaction details from this {source} message.
        Return ONLY valid JSON.
        
        Input: "{content}"
        
        Required JSON Structure:
        {{
            "amount": float,
            "type": "DEBIT" or "CREDIT",
            "date": "YYYY-MM-DD",
            "currency": "INR" (default),
            "account_mask": "1234" (last 4 digits or null),
            "bank_name": "HDFC" (or null),
            "merchant": "Amazon" (clean name),
            "description": "raw description",
            "ref_id": "transaction reference/UTR number or null",
            "confidence": float (0.0 to 1.0, based on how certain you are of the extraction),
            "suggested_regex": "a Python regex to match this EXACT message format",
            "field_mapping": {{
                "amount": index of group,
                "date": index of group,
                "merchant": index of group,
                "account": index of group,
                "type": "DEBIT" or "CREDIT"
            }}
        }}
        
        Rules:
        1. If date is missing/relative (e.g. 'today', 'yesterday'), calculate it based on reference date: {ref_date_str}.
        2. ALWAYS return date in ISO format (YYYY-MM-DD). Convert '28-03-24' to '2024-03-28'.
        3. For 'merchant', extract the actual entity name (e.g. 'Uber', 'Zomato').
        4. If amount, type or date is missing, set confidence to 0.5 or lower.
        5. The `suggested_regex` should be generic enough to match similar messages (e.g. replace 123.45 with [\d,\.]+) but specific to this bank/type.
        6. In `field_mapping`, use 1-based indexing for the capture groups in your `suggested_regex`.
        7. If unable to extract strictly, return null.
        """

        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=config
            )
            text = response.text.strip()
            # Clean potential markdown code blocks
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            
            data = json.loads(text)
            if not data: return None
            
            # Robust Date Parsing
            extracted_date = data.get("date")
            final_date = datetime.now()
            if extracted_date:
                try:
                    if "-" in extracted_date and len(extracted_date) == 10:
                        final_date = datetime.strptime(extracted_date, "%Y-%m-%d")
                    else:
                        from dateutil import parser as date_parser
                        final_date = date_parser.parse(extracted_date)
                except:
                    final_date = datetime.now()

            # Map to Schema
            return Transaction(
                amount=Decimal(str(data.get("amount", 0))),
                type=TransactionType(data.get("type", "DEBIT").upper()),
                date=final_date,
                currency=data.get("currency", "INR"),
                ref_id=data.get("ref_id"),
                account=AccountInfo(
                    mask=get_digits(data.get("account_mask")), 
                    provider=data.get("bank_name")
                ),
                merchant=MerchantInfo(
                    raw=data.get("description") or data.get("merchant") or "Unknown", 
                    cleaned=data.get("merchant") or "Unknown"
                ),
                description=data.get("description") or content,
                recipient=data.get("merchant") or "Unknown",
                raw_message=content,
                confidence=float(data.get("confidence", 0.9))
            )

        except errors.ClientError as e:
            # The SDK might use 'code' or 'status_code' depending on version
            status_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            if status_code == 429:
                print(f"AI Quota Exhausted (429): {e}")
            else:
                print(f"AI Client Error ({status_code}): {e}")
            return None
        except Exception as e:
            print(f"AI Parse Error: {e}")
            return None

    def parse_with_pattern(self, content: str, source: str, date_hint: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        """Extended parse that returns both transaction and suggested pattern."""
        if not self.config:
            return {"error": "AI Config not found"}
            
        if not self.config.is_enabled:
            return {"error": "AI is disabled in settings"}
            
        if not self.config.api_key_enc:
             return {"error": "API Key missing"}

        client = genai.Client(api_key=self.config.api_key_enc)
        config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        )
        model_id = self.config.model_name or "gemini-1.5-flash"

        ref_date = datetime.now()
        if date_hint and isinstance(date_hint, datetime):
            ref_date = date_hint
        elif date_hint and isinstance(date_hint, str):
             try: ref_date = datetime.fromisoformat(date_hint)
             except: pass
        ref_date_str = ref_date.strftime('%Y-%m-%d')

        prompt = rf"""
        You are a precise financial parser. Extract transaction details AND generate a reusable regex for this {source} message.
        Return ONLY valid JSON.
        
        Input: "{content}"
        
        Required JSON Structure:
        {{
            "transaction": {{
                "amount": float,
                "type": "DEBIT" or "CREDIT",
                "date": "YYYY-MM-DD",
                "account_mask": "1234" (last 4 digits or null),
                "bank_name": "HDFC" (or null),
                "merchant": "Amazon",
                "description": "raw",
                "ref_id": "utr",
                "confidence": float
            }},
            "suggested_regex": "Python regex with capture groups",
            "field_mapping": {{
                "amount": group_idx,
                "date": group_idx,
                "merchant": group_idx,
                "account": group_idx,
                "type": "DEBIT" or "CREDIT"
            }}
        }}

        Rules for Regex:
        1. Use [\d,\.]+ for amounts.
        2. Use (.*?) for merchants.
        3. Use [\d\-\/]+ for dates.
        4. Ensure it's robust enough for similar messages from this bank.
        """

        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=config
            )
            data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
            return data
        except errors.ClientError as e:
            status_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
            if status_code == 429:
                msg = "Gemini API quota exceeded. Please check your plan or retry later."
                print(f"AI Pattern Gen Quota Error: {msg}")
                return {"error": "quota_exhausted", "message": msg}
            return {"error": str(e)}
        except Exception as e:
            print(f"AI Pattern Gen Error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

def get_digits(s):
    if not s: return None
    return "".join(filter(str.isdigit, str(s)))[-4:]
