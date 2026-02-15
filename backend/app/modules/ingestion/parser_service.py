import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class ExternalParserService:
    @staticmethod
    def parse_sms(sender: str, body: str, received_at: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Call the external parser microservice for SMS ingestion.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/ingest/sms"
            # Parser expects 'sender' and 'body'
            payload = {"sender": sender, "body": body}
            if received_at:
                payload["received_at"] = received_at.isoformat()
                
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error calling external parser: {e}")
            return None

    @staticmethod
    def parse_email(subject: str, body_text: str, sender: str = "Unknown", received_at: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """
        Call the external parser microservice for Email ingestion.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/ingest/email"
            # Parser expects 'subject', 'body_text', 'sender'
            payload = {
                "subject": subject, 
                "body_text": body_text,
                "sender": sender
            }
            if received_at:
                payload["received_at"] = received_at.isoformat()
                
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error calling external parser: {e}")
            return None

    @staticmethod
    def sync_ai_config(api_key: str, model_name: str, is_enabled: bool):
        """
        Push AI configuration to the microservice.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/config/ai"
            payload = {
                "api_key": api_key,
                "model_name": model_name,
                "is_enabled": is_enabled
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error syncing AI config: {e}")
            return False

    @staticmethod
    def parse_file(file_content: bytes, filename: str, mapping: Optional[Dict] = None, header_row_index: Optional[int] = None, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Call the external parser microservice for File ingestion.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/ingest/file"
            
            files = {'file': (filename, file_content)}
            data = {}
            if mapping:
                import json
                data['mapping_override'] = json.dumps(mapping)
            if header_row_index is not None:
                data['header_row_index'] = header_row_index
            if password:
                data['password'] = password
                
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": f"Parser returned {response.status_code}", "logs": [response.text]}
        except Exception as e:
            logger.error(f"Error calling external parser: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def parse_cas(file_content: bytes, password: str) -> Optional[Dict[str, Any]]:
        """
        Call the external parser microservice for CAS parsing.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/ingest/cas"
            
            files = {'file': ('cas.pdf', file_content, 'application/pdf')}
            data = {'password': password}
            
            response = requests.post(url, files=files, data=data, timeout=60)
            
            if response.status_code == 200:
                return response.json() 
            return None
        except Exception as e:
            logger.error(f"Error calling external parser: {e}")
            return None

    @staticmethod
    def create_pattern(source: str, regex_pattern: str, mapping: Dict[str, Any]) -> bool:
        """
        Push a new regex pattern to the microservice.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/config/patterns"
            payload = {
                "source": source,
                "regex_pattern": regex_pattern,
                "mapping": mapping
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error creating pattern in external parser: {e}")
            return False

    @staticmethod
    def create_alias(pattern: str, alias: str) -> bool:
        """
        Push a new merchant alias to the microservice.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/config/aliases"
            payload = {"pattern": pattern, "alias": alias}
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error creating alias in external parser: {e}")
            return False

    @staticmethod
    def update_alias(alias_id: str, pattern: str, alias: str) -> bool:
        """
        Update an existing merchant alias.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/config/aliases/{alias_id}"
            payload = {"pattern": pattern, "alias": alias}
            response = requests.put(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error updating alias in external parser: {e}")
            return False

    @staticmethod
    def get_aliases() -> List[Dict[str, Any]]:
        """
        Get all merchant aliases from the microservice.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/config/aliases"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error fetching aliases: {e}")
            return []

    @staticmethod
    def delete_alias(alias_id: str) -> bool:
        """
        Delete a merchant alias.
        """
        try:
            url = f"{settings.PARSER_SERVICE_URL}/config/aliases/{alias_id}"
            response = requests.delete(url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting alias: {e}")
            return False

