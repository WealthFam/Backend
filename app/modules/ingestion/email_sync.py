import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, Any, Optional
from backend.app.core import timezone
from sqlalchemy.orm import Session
from backend.app.core.database import db_write_lock
from backend.app.modules.ingestion import models as ingestion_models
# from backend.app.modules.ingestion.registry import EmailParserRegistry
from backend.app.modules.ingestion.services import IngestionService

class EmailSyncService:
    @staticmethod
    def run_sync_task_in_background(
        tenant_id: str, 
        config_id: str, 
        imap_server: str, 
        email_user: str, 
        email_pass: str,
        folder: str = "INBOX",
        search_criterion: str = 'UNSEEN',
        since_date: Optional[datetime] = None,
        log_id: Optional[str] = None
    ):
        from backend.app.core.database import SessionLocal
        import logging
        db = SessionLocal()
        try:
            log_entry = None
            if log_id:
                log_entry = db.query(ingestion_models.EmailSyncLog).get(log_id)

            EmailSyncService.sync_emails(
                db=db,
                tenant_id=tenant_id,
                config_id=config_id,
                imap_server=imap_server,
                email_user=email_user,
                email_pass=email_pass,
                folder=folder,
                search_criterion=search_criterion,
                since_date=since_date,
                log_entry=log_entry
            )
        except Exception as e:
            logging.error(f"Background Sync Error: {e}")
        finally:
            db.close()

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
        since_date: Optional[datetime] = None,
        log_entry: Optional[ingestion_models.EmailSyncLog] = None
    ) -> Dict[str, Any]:
        """
        Connect to IMAP, fetch unread emails, parse them, and ingest transactions.
        """
        
        # Create Log Entry if not provided
        if not log_entry:
            log_entry = ingestion_models.EmailSyncLog(
                config_id=config_id,
                tenant_id=tenant_id,
                status="running",
                message="Starting sync..."
            )
            db.add(log_entry)
            db.commit() # Commit to get ID
            db.refresh(log_entry)

        stats = {"total": 0, "processed": 0, "failed": 0, "duplicates": 0, "errors": []}
        
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

            batch_queue = []

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
                                
                                # Record skipped noise
                                item_log = ingestion_models.EmailSyncItemLog(
                                    tenant_id=tenant_id,
                                    sync_log_id=log_entry.id,
                                    subject=subject,
                                    sender=msg.get("From"),
                                    received_at=email_date,
                                    status="skipped",
                                    reason="Noise filter"
                                )
                                db.add(item_log)
                                continue

                            # Enqueue for batch analysis
                            sender_id = msg.get("From")
                            
                            # Create individual item log
                            item_log = ingestion_models.EmailSyncItemLog(
                                tenant_id=tenant_id,
                                sync_log_id=log_entry.id,
                                subject=subject,
                                sender=sender_id,
                                received_at=email_date,
                                status="pending"
                            )
                            db.add(item_log)
                            db.flush() # Get ID

                            batch_queue.append({
                                "id": e_id.decode() if isinstance(e_id, bytes) else str(e_id),
                                "subject": subject,
                                "body_text": body,
                                "sender": sender_id,
                                "received_at": email_date,
                                "item_log_id": item_log.id
                            })
                            
                except Exception as e:
                    stats["errors"].append(f"Error extracting message {e_id}: {str(e)}")
                    stats["failed"] += 1

            mail.close()
            mail.logout()

            # --- PROCESS ACCUMULATED BATCH ---
            if batch_queue:
                # Deferred internal imports to prevent circular dependency at module initialisation
                from backend.app.modules.ingestion.parser_service import ExternalParserService
                from backend.app.modules.ingestion.base import ParsedTransaction
                
                chunk_size = 50
                for i in range(0, len(batch_queue), chunk_size):
                    chunk = batch_queue[i:i+chunk_size]
                    
                    parser_response = ExternalParserService.parse_email_batch(tenant_id, chunk)
                    if not parser_response:
                        stats["failed"] += len(chunk)
                        stats["errors"].append(f"External Batch parser completely failed for {len(chunk)} emails.")
                        continue
                        
                    results_map = parser_response.get("results", {})
                    
                    for item in chunk:
                        e_id = item["id"]
                        subject = item["subject"]
                        body = item["body_text"]
                        email_date = item["received_at"]
                        sender_id = item["sender"]
                        
                        res = results_map.get(e_id)
                        status = res.get("status") if res else "offline"
                        
                        if res and status in ["processed", "success", "duplicate_submission"]:
                            if status == "duplicate_submission":
                                continue
                            
                            logs = res.get("logs", [])
                            if any("quota_exhausted" in log for log in logs) or any("API Key missing" in log for log in logs):
                                stats["errors"].append("Rate Limit or API Key error detected inside batch.")
                                # We continue since the batch is already resolved, no need to break

                            results = res.get("results", [])
                            if not results:
                                stats["failed"] += 1
                                stats["errors"].append(f"No transactions found in email: {subject[:30]}")
                                continue
                                
                            for parsed_item in results:
                                t = parsed_item.get("transaction")
                                if not t: continue
                                
                                # Date Parsing
                                raw_date = t.get("date") or ""
                                try:
                                    parsed_date = timezone.ensure_utc(datetime.fromisoformat(raw_date.replace("Z", "+00:00")))
                                except:
                                    parsed_date = timezone.ensure_utc(email_date) if email_date else timezone.utcnow()

                                parsed = ParsedTransaction(
                                    amount=t.get("amount"),
                                    date=parsed_date,
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
                                    is_ai_parsed="AI" in str(parsed_item.get("metadata", {}).get("parser_used", "")).upper()
                                )
                                
                                proc_result = IngestionService.process_transaction(db, tenant_id, parsed)
                                p_status = proc_result.get("status")
                                
                                if p_status in ["success", "triaged"]:
                                    stats["processed"] += 1
                                    
                                    # Update item log
                                    item_log = db.query(ingestion_models.EmailSyncItemLog).get(item["item_log_id"])
                                    if item_log:
                                        with db_write_lock:
                                            item_log.status = "processed"
                                            item_log.parser_used = parsed_item.get("metadata", {}).get("parser_used")
                                            item_log.transaction_id = proc_result.get("transaction_id")
                                            db.commit()
                                elif proc_result.get("deduplicated"):
                                    stats["processed"] += 1
                                    stats["duplicates"] = stats.get("duplicates", 0) + 1
                                    
                                    # Update item log as duplicate
                                    item_log = db.query(ingestion_models.EmailSyncItemLog).get(item["item_log_id"])
                                    if item_log:
                                        with db_write_lock:
                                            item_log.status = "duplicate"
                                            item_log.reason = proc_result.get("reason")
                                            db.commit()
                                else:
                                    stats["failed"] += 1
                                    reason = proc_result.get('message') or proc_result.get('reason') or "Unknown Error"
                                    stats["errors"].append(f"Ingestion failed for '{subject[:30]}...': {reason}")
                                    
                                    # Update item log
                                    item_log = db.query(ingestion_models.EmailSyncItemLog).get(item["item_log_id"])
                                    if item_log:
                                        with db_write_lock:
                                            item_log.status = "failed"
                                            item_log.reason = reason
                                            db.commit()
                        else:
                            stats["failed"] += 1
                            stats["errors"].append(f"Parser failed to extract: {subject[:30]}...")
                            
                            keywords = ["bill", "mutual fund", "paid", "upi", "spent", "debited", "vpa", "txn", "transaction", "amount"]
                            combined_text = (subject + " " + body).lower()
                            has_money = bool(re.search(r'(?i)(?:Rs\.?|INR|₹)\s*[\d,]+', combined_text))
                            
                            # The Quick Filter handled explicit noise checking earlier
                            if (any(k in combined_text for k in keywords) or has_money):
                                IngestionService.capture_unparsed(
                                    db=db,
                                    tenant_id=tenant_id,
                                    source="EMAIL",
                                    raw_content=f"Subject: {subject}\nBody: {body}",
                                    subject=subject,
                                    sender=sender_id
                                )

                            # Update item log
                            item_log = db.query(ingestion_models.EmailSyncItemLog).get(item["item_log_id"])
                            if item_log:
                                item_log.status = "failed"
                                item_log.reason = f"Parser failed to extract: {subject[:30]}..."
                                db.commit()

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
