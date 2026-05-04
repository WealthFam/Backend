import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from backend.app.core import timezone
from backend.app.core.database import SessionLocal, db_write_lock, force_checkpoint
from backend.app.modules.finance import models
from backend.app.modules.finance.services.mutual_funds import MutualFundService
from backend.app.modules.finance.services.recurring_service import RecurringService
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.email_sync import EmailSyncService

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def daily_recurrence_check():
    """
    Job to check and process recurring transactions for all tenants.
    """
    logger.info("Starting daily recurrence check...")
    db: Session = SessionLocal()
    try:
        # Find tenants who have active recurring transactions due
        # We use a raw distinct query or ORM distinct
        
        # optimized: Get distinct tenant_ids that have due items
        due_tenants = db.query(models.RecurringTransaction.tenant_id).filter(
            models.RecurringTransaction.is_active == True,
            models.RecurringTransaction.next_run_date <= timezone.utcnow()
        ).distinct().all()
        
        tenant_ids = [t[0] for t in due_tenants]
        
        total_processed = 0
        for tid in tenant_ids:
            try:
                count = RecurringService.process_recurring_transactions(db, tid)
                total_processed += count
                logger.info(f"Processed {count} recurring transactions for tenant {tid}")
            except Exception as e:
                logger.error(f"Error processing recurrence for tenant {tid}: {e}")
                
        logger.info(f"Daily recurrence check completed. Total generated: {total_processed}")
        
    except Exception as e:
        logger.error(f"Critical error in daily_recurrence_check: {e}")
    finally:
        db.close()

def auto_sync_job():
    """
    Job to check and run auto-sync for all active email configurations.
    """
    logger.info("[AutoSync] Checking for scheduled syncs...")
    db: Session = SessionLocal()
    try:
        configs = db.query(ingestion_models.EmailConfiguration).filter(
            ingestion_models.EmailConfiguration.is_active == True,
            ingestion_models.EmailConfiguration.auto_sync_enabled == True
        ).all()
        
        logger.info(f"[AutoSync] Found {len(configs)} active configs.")
        for config in configs:
            logger.info(f"[AutoSync] Syncing {config.email}...")
            try:
                # A. Sync General Transaction Emails
                result = EmailSyncService.sync_emails(
                    db=db,
                    tenant_id=config.tenant_id,
                    config_id=config.id,
                    imap_server=config.imap_server,
                    email_user=config.email,
                    email_pass=config.password,
                    folder=config.folder,
                    search_criterion='ALL',
                    since_date=config.last_sync_at
                )
                
                if result.get("status") == "completed":
                    config.last_sync_at = timezone.utcnow()
                    db.commit()
                
                # B. Sync Bank Statements (New)
                # This uses the dedicated statement_last_sync_at timestamp
                from backend.app.modules.ingestion.statement_processor import StatementProcessor
                asyncio.run(StatementProcessor.sync_statements(
                    db=db, 
                    tenant_id=config.tenant_id
                ))
                    
            except Exception as e:
                logger.error(f"[AutoSync] Error syncing {config.email}: {e}")
    except Exception as e:
        logger.error(f"[AutoSync] General Loop Error: {e}")
    finally:
        db.close()

def mutual_fund_sync_job():
    """
    Job to refresh mutual fund NAVs for all tenants.
    Runs every 12 hours.
    """
    logger.info("[MFSync] Starting scheduled NAV refresh...")
    db: Session = SessionLocal()
    try:
        # Get all distinct tenant_ids that have mutual fund holdings
        from backend.app.modules.finance.models import MutualFundHolding
        tenants = db.query(MutualFundHolding.tenant_id).distinct().all()
        tenant_ids = [t[0] for t in tenants]
        
        logger.info(f"[MFSync] Found {len(tenant_ids)} tenants with holdings.")
        for tid in tenant_ids:
            try:
                logger.info(f"[MFSync] Syncing for tenant {tid}...")
                asyncio.run(MutualFundService.refresh_tenant_navs(db, tid))
            except Exception as e:
                logger.error(f"[MFSync] Error syncing for tenant {tid}: {e}")
                
    except Exception as e:
        logger.error(f"[MFSync] General MFSync Error: {e}")
    finally:
        db.close()

def pulse_check_job():
    """
    Periodic job to check for goal milestones and budget alerts for all tenants.
    Runs every 6 hours.
    """
    with db_write_lock:
        logger.info("[Pulse] Starting scheduled milestone/budget check...")
        db: Session = SessionLocal()
        try:
            from backend.app.modules.auth.models import Tenant
            from backend.app.modules.notifications import NotificationService
            tenants = db.query(Tenant).all()
            for t in tenants:
                try:
                    NotificationService.check_all_alerts(db, t.id)
                except Exception as e:
                    logger.error(f"[Pulse] Error for tenant {t.id}: {e}")
        finally:
            db.close()

def daily_summary_job():
    """
    Sends a summary of today's activities at 11:00 PM IST (17:30 UTC).
    """
    with db_write_lock:
        logger.info("[Summary] Starting daily summary broadcast...")
        db: Session = SessionLocal()
        try:
            from backend.app.modules.auth.models import Tenant
            from backend.app.modules.notifications import NotificationService
            tenants = db.query(Tenant).all()
            for t in tenants:
                try:
                    NotificationService.send_daily_summary(db, t.id)
                except Exception as e:
                    logger.error(f"[Summary] Error for tenant {t.id}: {e}")
        finally:
            db.close()

def prune_expired_tokens():
    """
    Job to delete expired or revoked tokens from user_tokens table.
    Runs daily.
    """
    logger.info("[Maintenance] Starting session token pruning...")
    db: Session = SessionLocal()
    try:
        from backend.app.modules.auth.models import UserToken
        from backend.app.core import timezone
        
        # Delete tokens that expired more than 24 hours ago OR are revoked
        # (Keeping revoked for a bit is fine, but eventually they should go)
        now = timezone.utcnow()
        count = db.query(UserToken).filter(
            (UserToken.expires_at < now) | (UserToken.is_revoked == True)
        ).delete(synchronize_session=False)
        
        db.commit()
        logger.info(f"[Maintenance] Pruned {count} session tokens.")
    except Exception as e:
        db.rollback()
        logger.error(f"[Maintenance] Error pruning tokens: {e}")
    finally:
        db.close()

def periodic_checkpoint_job():
    """
    Periodic job to force a DuckDB checkpoint.
    Ensures that even if the 2MB threshold is not met, 
    data is persisted to the main file every 30 minutes.
    """
    with db_write_lock:
        logger.info("[Maintenance] Starting periodic database checkpoint...")
        if force_checkpoint():
            logger.info("[Maintenance] Periodic database checkpoint complete.")
        else:
            logger.error("[Maintenance] Periodic database checkpoint failed.")

def start_scheduler():
    # Run daily at 00:01 UTC (or server time)
    trigger = CronTrigger(hour=0, minute=1)
    
    # Also support a faster interval for debug/demo?
    # For now, stick to daily.
    
    scheduler.add_job(daily_recurrence_check, trigger, id="daily_recurrence_check", replace_existing=True)
    
    # Run email sync every 3 hours
    scheduler.add_job(auto_sync_job, 'interval', hours=3, id="auto_sync_job", replace_existing=True)
    
    # Run mutual fund sync daily at 03:00 AM
    scheduler.add_job(mutual_fund_sync_job, CronTrigger(hour=3, minute=0), id="mutual_fund_sync_job", replace_existing=True)
    
    # NEW: Run pulse check every 6 hours
    scheduler.add_job(pulse_check_job, 'interval', hours=1, id="pulse_check_job", replace_existing=True)
    
    # NEW: Run daily summary at 11:00 PM IST (17:30 UTC)
    scheduler.add_job(daily_summary_job, CronTrigger(hour=17, minute=30), id="daily_summary_job", replace_existing=True)
    
    # NEW: Run token pruning daily at 03:00 UTC
    scheduler.add_job(prune_expired_tokens, CronTrigger(hour=3, minute=0), id="prune_expired_tokens", replace_existing=True)
    
    # NEW: Frequent DuckDB Checkpoints (every 30 minutes)
    scheduler.add_job(periodic_checkpoint_job, 'interval', minutes=30, id="periodic_checkpoint_job", replace_existing=True)
    
    scheduler.start()
    logger.info("APScheduler started.")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("APScheduler shut down.")
