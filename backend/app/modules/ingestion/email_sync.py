import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Any, Optional
from backend.app.core import timezone
from sqlalchemy.orm import Session
from backend.app.modules.ingestion import models as ingestion_models
# from backend.app.modules.ingestion.registry import EmailParserRegistry
from backend.app.modules.ingestion.services import IngestionService

class EmailSyncService:
    @staticmethod
    def sync_emails(
        db: Session, 
        tenant_id: str, 
        config_id: str, # Accept ID directly
        imap_server: str, 
        email_user: str, 
        email_pass: str,
        folder: str = "INBOX",
        search_criterion: str = 'UNSEEN',
        since_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Connect to IMAP, fetch unread emails, parse them, and ingest transactions.
        """
        
        # Create Log Entry
        log_entry = ingestion_models.EmailSyncLog(
            config_id=config_id,
            tenant_id=tenant_id,
            status="running",
            message="Starting sync..."
        )
        db.add(log_entry)
        db.commit() # Commit to get ID
        db.refresh(log_entry)

        stats = {"total_fetched": 0, "processed": 0, "failed": 0, "errors": []}
        
        try:
            # Connect to the server
            mail = imaplib.IMAP4_SSL(imap_server)
            mail.login(email_user, email_pass)
            mail.select(folder)

            # Search for emails
            final_criterion = search_criterion
            if since_date:
                # IMAP SINCE format: DD-Mon-YYYY
                date_str = since_date.strftime("%d-%b-%Y")
                if search_criterion == 'ALL':
                    final_criterion = f'SINCE "{date_str}"'
                else:
                    final_criterion = f'({search_criterion} SINCE "{date_str}")'
            
            status, messages = mail.search(None, final_criterion)
            if status != "OK":
                return {"status": "error", "message": f"Search failed: {status}"}

            email_ids = messages[0].split()
            stats["total_fetched"] = len(email_ids)

            for e_id in email_ids:
                try:
                    # Fetch the email message by ID (PEEK to avoid marking as read)
                    # Use RFC822 for full message, but wrapped in BODY.PEEK[] if supported, 
                    # but standard python imaplib with RFC822 usually marks as seen. 
                    # To peek, we technically need BODY.PEEK[] which returns the body structure.
                    # However, for full raw email with headers, standard is RFC822.
                    # To avoid marking as read, many servers support BODY.PEEK[] effectively returning content.
                    # But simpler is to fetching BODY.PEEK[] 
                    
                    status, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
                    if status != "OK":
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            # Decode subject
                            subject_header = msg["Subject"]
                            subject, encoding = decode_header(subject_header)[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8")
                            
                            
                            # Extract body
                            body = ""
                            html_body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition"))
                                    if "attachment" in content_disposition:
                                        continue
                                    if content_type == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if payload: body = payload.decode(errors='ignore')
                                    elif content_type == "text/html":
                                        payload = part.get_payload(decode=True)
                                        if payload: html_body = payload.decode(errors='ignore')
                            else:
                                content_type = msg.get_content_type()
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    content = payload.decode(errors='ignore')
                                    if content_type == "text/html":
                                        html_body = content
                                    else:
                                        body = content

                            # Fallback to HTML if plain text is empty
                            if not body.strip() and html_body.strip():
                                body = html_body

                            # Clean HTML if necessary
                            if "<html" in body.lower() or "<div" in body.lower() or "<p" in body.lower():
                                body = re.sub('<script.*?>.*?</script>', ' ', body, flags=re.DOTALL | re.IGNORECASE)
                                body = re.sub('<style.*?>.*?</style>', ' ', body, flags=re.DOTALL | re.IGNORECASE)
                                body = re.sub('<[^<]+?>', ' ', body)
                                body = " ".join(body.split())

                            # Extract Email Header Date as Fallback
                            email_date = None
                            try:
                                email_date = parsedate_to_datetime(msg.get("Date"))
                            except: pass

                            # --- QUICK FILTER: Ignore obvious non-transactional noise ---
                            noise_keywords = [
                                "otp", "login alert", "successful login", "welcome", "your statement is ready", 
                                "appointment", "newsletter", "verify your email", "marketing", "offer", 
                                "cashback on your next", "security alert", "password reset", "kyc", 
                                "application update", "scheduled maintenance", "privacy policy",
                                # Social
                                "linkedin", "facebook", "instagram", "twitter", "youtube", "reddit", "pinterest", 
                                "follower", "connection request", "mentioned in", "tagged in", "commented on",
                                # Career
                                "job alert", "recruitment", "interview", "career", "naukri", "indeed", "glassdoor", 
                                "application status", "resume", "hiring", "talent acquisition",
                                # Marketing/News
                                "promotional", "subscription", "digest", "discount", "coupon", "clearance", 
                                "deals of the day", "cashback rewards", "gift card", "points statement",
                                # Administrative/General
                                "invitation", "webinar", "workshop", "survey", "feedback", "joined", 
                                "weekly roundup", "daily briefing", "activity update", "unsubscribed"
                            ]
                            subject_lower = subject.lower()
                            if any(nk in subject_lower for nk in noise_keywords):
                                stats["failed"] += 1
                                stats["errors"].append(f"Skipped noise: {subject[:30]}...")
                                continue

                            # Parse via External Microservice
                            from backend.app.modules.ingestion.parser_service import ExternalParserService
                            from backend.app.modules.ingestion.base import ParsedTransaction

                            sender_id = msg.get("From")
                            parser_response = ExternalParserService.parse_email(tenant_id, subject, body, sender_id)
                            
                            status = parser_response.get("status") if parser_response else "offline"
                            
                            if parser_response and status in ["processed", "success", "duplicate_submission"]:
                                if status == "duplicate_submission":
                                    continue

                                results = parser_response.get("results", [])
                                if not results:
                                    stats["failed"] += 1
                                    stats["errors"].append(f"No transactions found in email: {subject[:30]}")
                                    continue
                                    
                                for item in results:
                                    t = item.get("transaction")
                                    if not t: continue
                                    
                                    # Map to ParsedTransaction
                                    parsed = ParsedTransaction(
                                        amount=t.get("amount"),
                                        date=datetime.fromisoformat(t.get("date").replace("Z", "+00:00")),
                                        description=t.get("description") or subject,
                                        type=t.get("type"),
                                        account_mask=t.get("account", {}).get("mask"),
                                        recipient=t.get("recipient") or t.get("merchant", {}).get("cleaned"),
                                        category=t.get("category"),
                                        ref_id=t.get("ref_id"),
                                        balance=t.get("balance"),
                                        credit_limit=t.get("credit_limit"),
                                        raw_message=t.get("raw_message") or body,
                                        source="EMAIL",
                                        is_ai_parsed=item.get("metadata", {}).get("parser_used") == "AI"
                                    )
                                    
                                    result = IngestionService.process_transaction(db, tenant_id, parsed)
                                    status = result.get("status")
                                    
                                    if status in ["success", "triaged"]:
                                        stats["processed"] += 1
                                    elif result.get("deduplicated"):
                                        pass
                                    else:
                                        stats["failed"] += 1
                                        reason = result.get('message') or result.get('reason') or "Unknown Error"
                                        err_msg = f"Ingestion failed for '{subject[:30]}...': {reason}"
                                        stats["errors"].append(err_msg)
                            else:
                                stats["failed"] += 1
                                err_msg = f"External parser failed for: {subject[:30]}..."
                                stats["errors"].append(err_msg)
                                
                                # --- INTERACTIVE TRAINING CAPTURE ---
                                # Check for transaction-related keywords with more precision
                                # We skip emails that matched the QUICK FILTER above (noise_keywords)
                                keywords = ["bill", "mutual fund", "paid", "upi", "spent", "debited", "vpa", "txn", "transaction", "amount"]
                                combined_text = (subject + " " + body).lower()
                                
                                # Use a regex to check for currency-like patterns
                                has_money = bool(re.search(r'(?i)(?:Rs\.?|INR|₹)\s*[\d,]+', combined_text))
                                
                                # Re-run noise check here just in case (though it should have been caught in QUICK FILTER)
                                is_noise = any(nk in combined_text for nk in noise_keywords)
                                
                                if not is_noise and (any(k in combined_text for k in keywords) or has_money):
                                    IngestionService.capture_unparsed(
                                        db=db,
                                        tenant_id=tenant_id,
                                        source="EMAIL",
                                        raw_content=f"Subject: {subject}\nBody: {body}",
                                        subject=subject,
                                        sender=msg.get("From")
                                    )
                                
                                # Print body snippet for debugging
                                if any(k in combined_text for k in ["txn", "upi", "hdfc", "spent", "debited", "transaction"]):
                                    clean_body = body.replace("\n", " ").strip()

                except Exception as e:
                    stats["errors"].append(f"Error processing message {e_id}: {str(e)}")
                    stats["failed"] += 1

            mail.close()
            mail.logout()

            # Update Log Success
            if log_entry:
                log_entry.status = "completed"
                log_entry.completed_at = timezone.utcnow()
                log_entry.items_processed = stats["processed"]
                log_entry.message = f"Found {stats['total_fetched']}, Processed {stats['processed']}"
                if stats["errors"]:
                    # Join first 3 errors for the summary message
                    error_summary = "; ".join(stats["errors"][:3])
                    log_entry.message += f" (Errors: {error_summary})"
                db.commit()

            return {
                "status": "completed",
                "stats": stats
            }

        except Exception as e:
            # Update Log Error
            if log_entry:
                log_entry.status = "error"
                log_entry.completed_at = timezone.utcnow()
                log_entry.message = str(e)
                db.commit()

            return {"status": "error", "message": f"Connection failed: {str(e)}", "stats": stats}
