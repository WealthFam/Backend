from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.modules.finance import models
from backend.app.modules.finance.services.recurring_service import RecurringService
from backend.app.core import timezone
from backend.app.modules.finance.services.mutual_funds import MutualFundService
from backend.app.modules.ingestion.email_sync import EmailSyncService
from backend.app.modules.ingestion import models as ingestion_models
import logging
import asyncio

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

def start_scheduler():
    # Run daily at 00:01 UTC (or server time)
    trigger = CronTrigger(hour=0, minute=1)
    
    # Also support a faster interval for debug/demo?
    # For now, stick to daily.
    
    scheduler.add_job(daily_recurrence_check, trigger, id="daily_recurrence_check", replace_existing=True)
    
    # Run email sync every 3 hours
    scheduler.add_job(auto_sync_job, 'interval', hours=3, id="auto_sync_job", replace_existing=True)
    
    # Run mutual fund sync every 12 hours
    scheduler.add_job(mutual_fund_sync_job, 'interval', hours=12, id="mutual_fund_sync_job", replace_existing=True)
    
    scheduler.start()
    logger.info("APScheduler started.")

def stop_scheduler():
    scheduler.shutdown()
    logger.info("APScheduler shut down.")
