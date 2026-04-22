import logging
import httpx
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from sqlalchemy import func

from backend.app.core.market_database import MarketSessionLocal, market_db_write_lock
from backend.app.modules.finance.market_models import MutualFundNAVHistory
from backend.app.core import timezone

logger = logging.getLogger(__name__)

MFAPI_BASE_URL = "https://api.mfapi.in/mf"

class NAVService:
    @staticmethod
    def get_nav_history(scheme_code: str, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """
        Fetches NAV history from the market database.
        """
        db = MarketSessionLocal()
        try:
            scheme_code_str = str(scheme_code)
            # Normalize dates to datetime for query
            s_dt = datetime.combine(start_date, datetime.min.time())
            e_dt = datetime.combine(end_date, datetime.max.time())

            results = db.query(MutualFundNAVHistory).filter(
                MutualFundNAVHistory.scheme_code == scheme_code_str,
                MutualFundNAVHistory.nav_date >= s_dt,
                MutualFundNAVHistory.nav_date <= e_dt
            ).order_by(MutualFundNAVHistory.nav_date.asc()).all()

            return [
                {"date": r.nav_date.strftime("%Y-%m-%d"), "value": Decimal(str(r.nav))}
                for r in results
            ]
        finally:
            db.close()

    @staticmethod
    def sync_nav_history(scheme_code: str, force: bool = False):
        """
        Syncs NAV history from MFAPI to the market database.
        Runs in a background thread.
        """
        db = MarketSessionLocal()
        try:
            scheme_code_str = str(scheme_code)
            
            # Optimization: If we have data from "yesterday" or today, skip unless forced.
            latest = db.query(MutualFundNAVHistory).filter(
                MutualFundNAVHistory.scheme_code == scheme_code_str
            ).order_by(MutualFundNAVHistory.nav_date.desc()).first()
            
            today = timezone.utcnow().date()
            if not force and latest and latest.nav_date.date() >= (today - timedelta(days=1)):
                logger.info(f"NAV History for {scheme_code} is up to date (Latest: {latest.nav_date.date()}).")
                return

            logger.info(f"Syncing NAV History for {scheme_code} from API...")
            try:
                response = httpx.get(f"{MFAPI_BASE_URL}/{scheme_code}", timeout=20.0)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch NAV for {scheme_code}: {response.status_code}")
                    return

                data = response.json()
                raw_entries = data.get("data", [])
                if not raw_entries:
                    return

                # Acquire lock before modifying the DB
                with market_db_write_lock:
                    # 1. Re-query existing dates INSIDE the lock to handle race conditions 
                    # from concurrent sync tasks for the same scheme.
                    existing_dates = {
                        r[0].date() for r in db.query(MutualFundNAVHistory.nav_date).filter(
                            MutualFundNAVHistory.scheme_code == scheme_code_str
                        ).all()
                    }

                    added_dates = set()
                    new_count = 0
                    
                    for entry in raw_entries:
                        try:
                            d_obj = datetime.strptime(entry['date'], "%d-%m-%Y").date()
                            # Double check against DB and locally added dates
                            if d_obj not in existing_dates and d_obj not in added_dates:
                                nav_val = Decimal(str(entry['nav']))
                                record = MutualFundNAVHistory(
                                    scheme_code=scheme_code_str,
                                    nav_date=datetime.combine(d_obj, datetime.min.time()),
                                    nav=nav_val
                                )
                                db.add(record)
                                added_dates.add(d_obj)
                                new_count += 1
                                
                                if new_count % 500 == 0:
                                    db.flush()
                        except:
                            continue
                    
                    if new_count > 0:
                        db.commit()
                        logger.info(f"Cached {new_count} new NAV records for {scheme_code}.")
                    else:
                        logger.info(f"No new records found for {scheme_code} after API fetch.")
            except Exception as e:
                logger.error(f"Error during NAV sync for {scheme_code}: {e}")
                db.rollback()
        finally:
            db.close()

    @staticmethod
    def get_latest_nav(scheme_code: str) -> Optional[Dict[str, Any]]:
        """
        Returns the latest NAV from cache.
        """
        db = MarketSessionLocal()
        try:
            latest = db.query(MutualFundNAVHistory).filter(
                MutualFundNAVHistory.scheme_code == str(scheme_code)
            ).order_by(MutualFundNAVHistory.nav_date.desc()).first()
            
            if latest:
                return {
                    "nav": Decimal(str(latest.nav)),
                    "date": latest.nav_date.strftime("%d-%m-%Y"),
                    "nav_date_obj": latest.nav_date
                }
            return None
        finally:
            db.close()
            
    @staticmethod
    def get_latest_nav_delta(scheme_code: str) -> Dict[str, Any]:
        """
        Returns the delta between the latest and previous NAV from cache.
        """
        db = MarketSessionLocal()
        try:
            results = db.query(MutualFundNAVHistory).filter(
                MutualFundNAVHistory.scheme_code == str(scheme_code)
            ).order_by(MutualFundNAVHistory.nav_date.desc()).limit(2).all()
            
            if len(results) < 2:
                # Fallback: if only one record exists, delta is zero
                latest_nav = Decimal(str(results[0].nav)) if results else Decimal("0.0")
                return {
                    "delta": Decimal("0.0"), 
                    "percent": Decimal("0.0"), 
                    "latest": latest_nav,
                    "previous": latest_nav
                }
            
            latest = results[0]
            previous = results[1]
            
            n1 = Decimal(str(latest.nav))
            n0 = Decimal(str(previous.nav))
            
            delta = n1 - n0
            percent = (delta / n0 * 100) if n0 > 0 else Decimal("0.0")
            
            return {
                "delta": delta,
                "percent": percent,
                "latest": n1,
                "previous": n0
            }
        finally:
            db.close()

    @staticmethod
    def get_sparkline(scheme_code: str, days: int = 30) -> List[float]:
        """
        Returns the last N days of NAVs for a sparkline.
        """
        db = MarketSessionLocal()
        try:
            results = db.query(MutualFundNAVHistory).filter(
                MutualFundNAVHistory.scheme_code == str(scheme_code)
            ).order_by(MutualFundNAVHistory.nav_date.desc()).limit(days).all()
            
            # Reverse to chronological order
            results.reverse()
            return [float(r.nav) for r in results]
        finally:
            db.close()
    @staticmethod
    def fetch_live_nav_history(scheme_code: str, days: int = 365) -> Dict[str, Any]:
        """
        Fetches NAV history directly from API without touching the market database.
        Used for Explore mode where we don't want to cache data for funds the user doesn't own.
        """
        try:
            response = httpx.get(f"{MFAPI_BASE_URL}/{scheme_code}", timeout=15.0)
            if response.status_code != 200:
                return {"meta": {}, "history": []}
            
            data = response.json()
            raw_history = data.get("data", [])
            meta = data.get("meta", {})
            
            start_date = (timezone.utcnow() - timedelta(days=days)).date()
            valid_history = []
            
            for entry in raw_history:
                try:
                    # MFAPI format is DD-MM-YYYY
                    d_obj = datetime.strptime(entry['date'], "%d-%m-%Y").date()
                    if d_obj >= start_date:
                        valid_history.append({
                            "date": d_obj.strftime("%Y-%m-%d"),
                            "value": Decimal(str(entry['nav']))
                        })
                except:
                    continue
            
            # Sort ascending for chart (MFAPI is descending)
            return {
                "meta": meta,
                "history": sorted(valid_history, key=lambda x: x['date'])
            }
        except Exception as e:
            logger.error(f"Live NAV fetch failed for {scheme_code}: {e}")
            return {"meta": {}, "history": []}
