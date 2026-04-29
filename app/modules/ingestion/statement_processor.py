import os
import logging
import tempfile
import uuid
import shutil
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import fitz # PyMuPDF for unlocking trials
import pdfplumber
import io
import asyncio

from backend.app.core import timezone
from backend.app.core.database import db_write_lock
from backend.app.modules.finance import models as finance_models
from backend.app.modules.auth.models import User
from backend.app.modules.ingestion.parser_service import ExternalParserService
from backend.app.modules.vault.service import VaultService
from backend.app.modules.vault.models import DocumentType
from backend.app.modules.ingestion.utils.crypto import CryptoUtils

logger = logging.getLogger(__name__)

class StatementProcessor:
    
    @staticmethod
    async def sync_statements(db: Session, tenant_id: str, since_date: Optional[datetime] = None):
        """
        Background task to scan emails for statements and process them.
        """
        # 1. Get all active IMAP configs for the tenant
        from backend.app.modules.ingestion.models import EmailConfiguration
        configs = db.query(EmailConfiguration).filter(
            EmailConfiguration.tenant_id == tenant_id,
            EmailConfiguration.is_active == True
        ).all()
        
        if not configs:
            logger.warning(f"No active EmailConfiguration found for tenant {tenant_id}")
            return
            
        for config in configs:
            logger.info(f"Scanning email inbox: {config.email} for tenant {tenant_id}")
            
            # Determine scan start date
            scan_since = since_date
            is_manual = since_date is not None
            
            if not is_manual and config.statement_last_sync_at:
                scan_since = config.statement_last_sync_at
                
            # 2. Fetch Emails with Attachments
            try:
                mail = imaplib.IMAP4_SSL(config.imap_server)
                mail.login(config.email, config.password)
                mail.select("INBOX")
                
                # Search for potential statements
                search_criterion = '(OR SUBJECT "statement" SUBJECT "e-statement")'
                if scan_since:
                    date_str = scan_since.strftime("%d-%b-%Y")
                    search_criterion = f'({search_criterion} SINCE "{date_str}")'
                    
                status, messages = mail.search(None, search_criterion)
                if status != "OK":
                    continue
                    
                email_ids = messages[0].split()
                for e_id in email_ids:
                    status, msg_data = mail.fetch(e_id, "(BODY.PEEK[])")
                    if status != "OK": continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            await StatementProcessor._process_email_message(db, tenant_id, msg)
                            
                mail.close()
                mail.logout()
                
                # Only update statement_last_sync_at if this was an automated scan
                if not is_manual:
                    config.statement_last_sync_at = timezone.utcnow()
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Error syncing statements for {config.email}: {e}")

    @staticmethod
    async def _process_email_message(db: Session, tenant_id: str, msg: email.message.Message):
        """
        Extract attachments from an email and process if they look like statements.
        """
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
                
            filename = part.get_filename()
            if not filename or not filename.lower().endswith('.pdf'):
                continue
                
            # Decode filename
            decoded_filename, encoding = decode_header(filename)[0]
            if isinstance(decoded_filename, bytes):
                filename = decoded_filename.decode(encoding or 'utf-8')
                
            # Process attachment
            file_bytes = part.get_payload(decode=True)
            sender = msg.get("From", "Unknown")
            await StatementProcessor.process_statement_file(db, tenant_id, filename, file_bytes, source="EMAIL", email_sender=sender)

    @staticmethod
    async def process_statement_file(db: Session, tenant_id: str, filename: str, file_bytes: bytes, source: str = "MANUAL", account_id: Optional[str] = None, email_sender: Optional[str] = None, manual_password: Optional[str] = None):
        """
        Main entry point for processing a statement file (PDF).
        Handles unlocking, parsing, and saving.
        """
        # 0. Idempotency Check: Don't process if already exists and not deleted
        existing = db.query(finance_models.Statement).filter(
            finance_models.Statement.tenant_id == tenant_id,
            finance_models.Statement.filename == filename,
            finance_models.Statement.is_deleted == False
        ).first()
        if existing:
            logger.info(f"Statement already exists: {filename}. Skipping.")
            return existing

        # 1. Try to unlock the PDF
        unlocked_bytes, password_used = StatementProcessor._try_unlock_pdf(db, tenant_id, file_bytes, email_sender=email_sender, manual_password=manual_password)
        
        if not unlocked_bytes:
            logger.warning(f"Failed to unlock statement: {filename}")
            # Create a PENDING statement record that requires manual password
            return await StatementProcessor._create_pending_statement(db, tenant_id, filename, file_bytes, source, email_sender=email_sender)

        # 2. Heuristic Check: Is this actually a financial statement?
        # We only check if we successfully unlocked it.
        if unlocked_bytes:
            if not StatementProcessor._is_likely_statement(unlocked_bytes):
                logger.info(f"PDF {filename} failed heuristic check. Discarding as non-statement.")
                return None

        # 3. Cache Successful Password
        if password_used:
            StatementProcessor._cache_working_password(db, tenant_id, email_sender, password_used)

        # 4. Call Parser Service
        try:
            parser_result = ExternalParserService.parse_statement(tenant_id, unlocked_bytes, password=password_used)
            if not parser_result or parser_result.get("status") != "success":
                raise Exception(f"Parser failed: {parser_result.get('logs')}")
                
            transactions = parser_result.get("results", [])
            if not transactions:
                raise Exception("No transactions extracted from statement.")

            # 3. Save to Vault
            # We save the ORIGINAL (encrypted) file to the vault for security
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
                
            class MockFile:
                def __init__(self, path, name):
                    self.file = open(path, "rb")
                    self.filename = name
                    self.content_type = "application/pdf"
            
            mock_file = MockFile(tmp_path, filename)
            
            # Get an owner for the vault (default to first tenant user)
            owner = db.query(User).filter(User.tenant_id == tenant_id).first()
            owner_id = str(owner.id) if owner else None
            
            # Now we can just await it since we are in an async method
            vault_doc = await VaultService.upload_document(
                db, tenant_id, owner_id, mock_file, 
                file_type=DocumentType.STATEMENT,
                description=f"Automated statement ingestion from {source}"
            )
            
            mock_file.file.close()
            if os.path.exists(tmp_path): os.remove(tmp_path)

            # 4. Create Statement and StatementTransactions
            with db_write_lock:
                # Deduce Account (Use mask from first transaction)
                account = None
                if account_id:
                    account = db.query(finance_models.Account).filter(
                        finance_models.Account.id == account_id,
                        finance_models.Account.tenant_id == tenant_id
                    ).first()
                
                if not account:
                    account_mask = transactions[0]["transaction"]["account"]["mask"]
                    account = db.query(finance_models.Account).filter(
                        finance_models.Account.tenant_id == tenant_id,
                        finance_models.Account.account_mask.endswith(account_mask[-4:])
                    ).first()
                
                if not account:
                    # Create placeholder account if missing
                    account_mask = transactions[0]["transaction"]["account"]["mask"]
                    account = finance_models.Account(
                        tenant_id=tenant_id,
                        name=f"Statement Account (XX{account_mask[-4:]})",
                        type=finance_models.AccountType.BANK,
                        account_mask=account_mask[-4:],
                        is_verified=False
                    )
                    db.add(account)
                    db.commit()
                    db.refresh(account)

                statement = finance_models.Statement(
                    tenant_id=tenant_id,
                    account_id=str(account.id),
                    vault_id=vault_doc.id,
                    filename=filename,
                    status=finance_models.StatementStatus.PARSED,
                    source=finance_models.StatementSource(source)
                )
                db.add(statement)
                db.commit()
                db.refresh(statement)
                
                from backend.app.modules.finance.services.transaction_service import TransactionService
                for item in transactions:
                    t = item["transaction"]
                    
                    # 1. Start with the parser's category
                    cat_sug = t.get("category")
                    
                    # 2. Check rules engine to override if we have a better match
                    rule_cat = TransactionService.get_suggested_category(db, tenant_id, t["description"], t.get("recipient", ""))
                    if rule_cat and rule_cat != "Uncategorized":
                        cat_sug = rule_cat
                        
                    st = finance_models.StatementTransaction(
                        statement_id=statement.id,
                        tenant_id=tenant_id,
                        date=datetime.fromisoformat(t["date"]),
                        amount=t["amount"],
                        type=finance_models.TransactionType.CREDIT if t["type"] == "CREDIT" else finance_models.TransactionType.DEBIT,
                        description=t["description"],
                        ref_id=t.get("ref_id"),
                        category_suggestion=cat_sug
                    )
                    db.add(st)
                
                db.commit()
                
            # 5. Run Reconciliation (Future)
            StatementProcessor.reconcile_statement(db, statement.id)
            return statement
            
        except Exception as e:
            logger.error(f"Error processing statement {filename}: {e}")
            db.rollback()

    @staticmethod
    def _try_unlock_pdf(db: Session, tenant_id: str, file_bytes: bytes, email_sender: Optional[str] = None, manual_password: Optional[str] = None) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Attempts to decrypt a PDF using various password patterns.
        """
        import fitz
        from io import BytesIO
        
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        if not pdf.is_encrypted:
            return file_bytes, None

        trials = set()
        
        # 0. Manual password provided by user (HIGHEST PRIORITY)
        if manual_password:
            trials.add(manual_password)

        # 1. Try Cached Password for this sender
        if email_sender:
            cached_pwd = StatementProcessor._get_cached_password(db, tenant_id, email_sender)
            if cached_pwd:
                try:
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    if doc.authenticate(cached_pwd):
                        unlocked_stream = doc.tobytes()
                        doc.close()
                        return unlocked_stream, cached_pwd
                    doc.close()
                except: pass

        # 2. Generate Trial Passwords from User Profiles
        users = db.query(User).filter(User.tenant_id == tenant_id).all()
        
        for user in users:
            # Pattern: PAN (UPPER and lower)
            if user.pan_number:
                trials.add(user.pan_number.upper())
                trials.add(user.pan_number.lower())
            
            # Pattern: Name4 + DDMM (e.g. SUJI0105)
            if user.full_name and user.dob:
                name_part = "".join(filter(str.isalpha, user.full_name))[:4]
                dob_part = user.dob.strftime("%d%m")
                trials.add(f"{name_part.upper()}{dob_part}")
                trials.add(f"{name_part.lower()}{dob_part}")
            
            # Pattern: Last 5 Mobile + DDMMYY (e.g. 12345160982)
            if user.phone_number and user.dob:
                mobile_part = user.phone_number[-5:]
                dob_part = user.dob.strftime("%d%m%y")
                trials.add(f"{mobile_part}{dob_part}")

            # Pattern: First 4 Name + DDMMYYYY
            if user.full_name and user.dob:
                name_part = "".join(filter(str.isalpha, user.full_name))[:4]
                dob_part = user.dob.strftime("%d%m%Y")
                trials.add(f"{name_part.upper()}{dob_part}")
                trials.add(f"{name_part.lower()}{dob_part}")

        # 3. Execution
        for pwd in trials:
            try:
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if doc.authenticate(pwd):
                    unlocked_stream = doc.tobytes()
                    doc.close()
                    return unlocked_stream, pwd
                doc.close()
            except: continue
                
        return None, None

    @staticmethod
    def _get_cached_password(db: Session, tenant_id: str, sender: str) -> Optional[str]:
        from backend.app.modules.finance.models import StatementPasswordCache
        setting = db.query(StatementPasswordCache).filter(
            StatementPasswordCache.tenant_id == tenant_id,
            StatementPasswordCache.sender_email == sender.lower().strip()
        ).first()
        if not setting: return None
        return CryptoUtils.decrypt(setting.password)

    @staticmethod
    def _is_likely_statement(pdf_bytes: bytes) -> bool:
        """
        Check if the PDF is likely a financial statement based on keywords.
        Uses pdfplumber to extract text from the first 2 pages.
        """
        keywords = ["statement", "transaction", "balance", "account", "credit", "debit", "summary", "invoice"]
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                # Check first 2 pages for performance
                text = ""
                for page in pdf.pages[:min(len(pdf.pages), 2)]:
                    text += (page.extract_text() or "").lower()
                
                # Check for at least 2 distinct keywords
                match_count = sum(1 for k in keywords if k in text)
                return match_count >= 2
        except Exception as e:
            logger.warning(f"Heuristic check failed: {e}. Defaulting to True.")
            return True # Fallback to true if parsing fails

    @staticmethod
    def _cache_working_password(db: Session, tenant_id: str, sender: Optional[str], password: str):
        """
        Save the working password for future statements from the same source.
        """
        if not sender: return
        
        from backend.app.modules.finance.models import StatementPasswordCache
        # Normalize sender (email)
        sender = sender.lower().strip()
        
        existing = db.query(StatementPasswordCache).filter(
            StatementPasswordCache.tenant_id == tenant_id,
            StatementPasswordCache.sender_email == sender
        ).first()
        
        if existing:
            existing.password = CryptoUtils.encrypt(password)
        else:
            cache = StatementPasswordCache(
                tenant_id=tenant_id,
                sender_email=sender,
                password=CryptoUtils.encrypt(password)
            )
            db.add(cache)
        
        db.commit()

    @staticmethod
    async def _create_pending_statement(db: Session, tenant_id: str, filename: str, file_bytes: bytes, source: str, email_sender: Optional[str] = None) -> finance_models.Statement:
        """
        Save the statement even if it fails decryption, so the user can provide the password manually later.
        """
        try:
            # 1. Save to Vault
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
                
            class MockFile:
                def __init__(self, path, name):
                    self.file = open(path, "rb")
                    self.filename = name
                    self.content_type = "application/pdf"
            
            mock_file = MockFile(tmp_path, filename)
            owner = db.query(User).filter(User.tenant_id == tenant_id).first()
            owner_id = str(owner.id) if owner else None
            
            vault_doc = await VaultService.upload_document(
                db, tenant_id, owner_id, mock_file, 
                file_type=DocumentType.STATEMENT,
                description=f"Pending statement (decryption failed) from {source}"
            )
            
            mock_file.file.close()
            if os.path.exists(tmp_path): os.remove(tmp_path)

            # 2. Create PENDING Statement record
            # We don't have an account_id yet since we couldn't parse it.
            # We'll need a way to link it later. For now, we can leave account_id as None if allowed,
            # but our model says NOT NULL. 
            # Actually, let's try to find a default account or just use a dummy one?
            # Or maybe we change the model to allow NULL account_id for PENDING statements.
            
            statement = finance_models.Statement(
                tenant_id=tenant_id,
                account_id=None, # We'll need to update the model to allow NULL
                vault_id=vault_doc.id,
                filename=filename,
                status=finance_models.StatementStatus.PENDING,
                source=finance_models.StatementSource(source),
                email_sender=email_sender
            )
            db.add(statement)
            db.commit()
            return statement
            
        except Exception as e:
            logger.error(f"Failed to create pending statement for {filename}: {e}")
            db.rollback()

    @staticmethod
    async def retry_statement(db: Session, tenant_id: str, statement_id: str, password: str) -> Dict[str, Any]:
        """
        Retry parsing a pending statement with a new password.
        Follows Ironclad Service Pattern.
        """
        from backend.app.modules.finance import models as finance_models
        from backend.app.modules.vault.service import VaultService
        
        statement = db.query(finance_models.Statement).filter(
            finance_models.Statement.id == statement_id,
            finance_models.Statement.tenant_id == tenant_id
        ).first()
        
        if not statement:
            raise ValueError("Statement not found")

        # Get file content from vault
        doc_meta = await VaultService.get_document_by_id(db, tenant_id, statement.vault_id)
        if not doc_meta or not doc_meta.file_path:
            raise ValueError("Statement file not found in vault")

        with open(doc_meta.file_path, "rb") as f:
            doc_bytes = f.read()

        with db_write_lock:
            try:
                new_statement = await StatementProcessor.process_statement_file(
                    db, tenant_id, 
                    statement.filename, doc_bytes, 
                    source=statement.source.value,
                    email_sender=statement.email_sender,
                    manual_password=password
                )
                
                if new_statement and new_statement.status == finance_models.StatementStatus.PARSED:
                    # Soft-delete the old pending/failed one
                    statement.is_deleted = True
                    statement.deleted_at = timezone.utcnow()
                    db.commit()
                    return {"status": "success", "message": "Statement parsed successfully.", "statement_id": new_statement.id}
                else:
                    raise ValueError("Failed to decrypt with provided password.")
            except Exception as e:
                db.rollback()
                raise e

    @staticmethod
    def delete_statement(db: Session, tenant_id: str, statement_id: str):
        """
        Soft-delete a statement and its transactions.
        Follows Ironclad Service Pattern.
        """
        from backend.app.modules.finance import models as finance_models
        
        with db_write_lock:
            try:
                statement = db.query(finance_models.Statement).filter(
                    finance_models.Statement.id == statement_id,
                    finance_models.Statement.tenant_id == tenant_id
                ).first()
                
                if statement:
                    statement.is_deleted = True
                    statement.deleted_at = timezone.utcnow()
                    
                    # Also soft-delete transactions
                    db.query(finance_models.StatementTransaction).filter(
                        finance_models.StatementTransaction.statement_id == statement_id
                    ).update({
                        "is_deleted": True,
                        "deleted_at": timezone.utcnow()
                    })
                    
                    db.commit()
            except Exception as e:
                db.rollback()
                raise e

    @staticmethod
    def reconcile_statement(db: Session, statement_id: str):
        """
        Compare StatementTransactions with Ledger Transactions.
        Marks matches.
        Follows Ironclad Service Pattern.
        """
        from backend.app.modules.finance import models as finance_models
        
        with db_write_lock:
            try:
                statement = db.query(finance_models.Statement).filter(
                    finance_models.Statement.id == statement_id,
                    finance_models.Statement.is_deleted == False
                ).first()
                if not statement: return
                
                # 1. Self-healing: Check previously reconciled transactions for orphans
                all_st_txns = db.query(finance_models.StatementTransaction).filter(
                    finance_models.StatementTransaction.statement_id == statement_id
                ).all()
                
                for st in all_st_txns:
                    if st.is_reconciled and st.matched_transaction_id:
                        # Check if matched ledger txn still exists and is not deleted
                        exists = db.query(finance_models.Transaction).filter(
                            finance_models.Transaction.id == st.matched_transaction_id,
                            finance_models.Transaction.is_deleted == False
                        ).first()
                        
                        if not exists:
                            # Orphaned! Reset it.
                            st.is_reconciled = False
                            st.matched_transaction_id = None

                # 2. Reconcile non-matched transactions
                from datetime import timedelta
                from backend.app.modules.finance.services.transaction_service import TransactionService
                
                for st in all_st_txns:
                    if st.is_reconciled:
                        continue
                        
                    # A. Update Category Suggestion based on latest rules
                    rule_cat = TransactionService.get_suggested_category(db, st.tenant_id, st.description, st.ref_id or "")
                    if rule_cat and rule_cat != "Uncategorized":
                        st.category_suggestion = rule_cat

                    # B. Fuzzy match: Date (within 1 day), Amount (exact), Type (exact)
                    date_min = st.date - timedelta(days=1)
                    date_max = st.date + timedelta(days=1)
                    
                    ledger_amount = -st.amount if st.type == finance_models.TransactionType.DEBIT else st.amount
                    
                    match = db.query(finance_models.Transaction).filter(
                        finance_models.Transaction.tenant_id == st.tenant_id,
                        finance_models.Transaction.account_id == statement.account_id,
                        finance_models.Transaction.amount == ledger_amount,
                        finance_models.Transaction.date >= date_min,
                        finance_models.Transaction.date <= date_max,
                        finance_models.Transaction.is_deleted == False # Crucial check
                    ).first()
                    
                    if match:
                        st.is_reconciled = True
                        st.matched_transaction_id = match.id
                        
                db.commit()
            except Exception as e:
                db.rollback()
                raise e
