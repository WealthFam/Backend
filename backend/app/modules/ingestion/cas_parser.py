from typing import List, Dict, Any, Optional
import os
import tempfile
import imaplib
import email
import logging

logger = logging.getLogger(__name__)

class CASParser:
    """
    Parses Consolidated Account Statements (CAS) using the External Parser Service.
    """

    @staticmethod
    def parse_pdf(tenant_id: str, file_path: str, password: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parses a CAS PDF using the External Parser Microservice.
        """
        try:
             # Read file content
            with open(file_path, "rb") as f:
                content = f.read()

            from backend.app.modules.ingestion.parser_service import ExternalParserService
            
            # Call Microservice
            response = ExternalParserService.parse_cas(tenant_id, content, password or "")
            
            if not response or response.get("status") != "success":
                raise ValueError(f"CAS Parsing failed via microservice: {response.get('logs') if response else 'Unknown Error'}")

            # Microservice returns List[ParsedItem] in 'results'
            results = response.get("results", [])
            transactions = []
            for item in results:
                if item.get("transaction"):
                    # The backend expects raw dicts that it mapping logic can handle
                    # but since these are already standardized, we need to ensure they have 
                    # the keys expected by MutualFundService.map_transactions_to_schemes
                    t = item["transaction"]
                    meta = item.get("metadata", {})
                    transactions.append({
                        "date": t.get("date"),
                        "amount": t.get("amount"),
                        "type": t.get("type"),
                        "scheme_name": t.get("description") or t.get("merchant", {}).get("cleaned"),
                        "folio_number": t.get("ref_id") or t.get("account", {}).get("mask"),
                        "units": meta.get("units", 0),
                        "nav": meta.get("nav", 0),
                        "amfi": meta.get("amfi"),
                        "isin": meta.get("isin"),
                        "is_synthesized": meta.get("is_synthesized", False)
                    })

            return transactions

        except Exception as e:
            logger.error(f"Error parsing CAS via microservice: {e}")
            raise e

    @staticmethod
    def scan_cas_emails(
        email_config: object, 
        password: str
    ) -> List[Dict[str, Any]]:
        """
        Scan emails for CAS, parse PDFs, and return a flattened list of all raw transactions.
        Does NOT ingest into DB. Mapping and ingestion happen in MutualFundService.
        """
        all_found_transactions = []
        
        try:
            mail = imaplib.IMAP4_SSL(email_config.imap_server)
            mail.login(email_config.email, email_config.password)
            mail.select(email_config.folder)
            
            search_query = '(OR (SUBJECT "Consolidated Account Statement") (FROM "camsonline"))'
            if email_config.cas_last_sync_at:
                imap_date = email_config.cas_last_sync_at.strftime("%d-%b-%Y")
                search_query = f'({search_query} SINCE {imap_date})'
                
            status, messages = mail.search(None, search_query)
            if status != "OK":
                return []
                
            email_ids = messages[0].split()

            for e_id in email_ids:
                _, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
                        continue
                     
                    filename = part.get_filename()
                    if filename and filename.lower().endswith('.pdf'):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
                            f.write(part.get_payload(decode=True))
                            temp_path = f.name
                            
                        try:
                            transactions = CASParser.parse_pdf(str(email_config.tenant_id), temp_path, password)
                            all_found_transactions.extend(transactions)
                        except Exception:
                            pass
                        finally:
                            if os.path.exists(temp_path):
                                try:
                                    os.remove(temp_path)
                                except: pass

            mail.close()
            mail.logout()
            
        except Exception as e:
            raise e
            
        return all_found_transactions
