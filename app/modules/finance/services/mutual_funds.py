import asyncio
import hashlib
import json
import logging
import re
import threading
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

import httpx
from dateutil import parser as date_parser
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import ObjectDeletedError

logger = logging.getLogger(__name__)

from backend.app.core import timezone
from backend.app.core.database import SessionLocal, db_write_lock
from backend.app.modules.finance.models import (
    MutualFundHolding,
    MutualFundOrder,
    MutualFundSyncLog,
    MutualFundsMeta,
    MutualFundBenchmark,
)
from backend.app.modules.auth.models import User
from ..models import PortfolioTimelineCache, InvestmentGoal
from ..utils.financial_math import xirr, calculate_start_date, add_months, categorize_fund
from backend.app.modules.ingestion.ai_service import AIService

from .benchmarks import BenchmarkService
from .external.market_data import MarketDataService
from .external.nav_service import NAVService

MFAPI_BASE_URL = "https://api.mfapi.in/mf"

class MutualFundService:
    # Standardized transaction keywords for categorization
    MF_WITHDRAWAL_KEYWORDS = ["SELL", "CREDIT", "REDEMP", "PAYOUT", "OUT", "SWITCH-OUT", "STP-OUT", "STP - OUT", "SWITCH - OUT"]
    MF_INVESTMENT_KEYWORDS = ["BUY", "DEBIT", "SIP", "TOPUP", "PURCHASE", "INVEST", "REINV", "SWITCH-IN", "STP-IN", "STP - IN", "SWITCH - IN", "ADDITIONAL", "SUMMARY BALANCE"]
    
    # Internal keywords that don't represent external capital flows (for portfolio-wide XIRR)
    MF_INTERNAL_KEYWORDS = ["SWITCH", "STP", "SWP", "MERGER", "CONSOLIDATION"]
    
    # Reinvestment keywords (to be excluded from cash flow calculations)
    MF_REINVESTMENT_KEYWORDS = ["REINV", "DIVIDEND REINVESTMENT", "DIV REINV"]

    @staticmethod
    def _parse_date_safely(date_input: Any) -> Optional[date]:
        """
        Standardizes date parsing for Indian formats (DD-MM-YYYY) vs ISO formats (YYYY-MM-DD).
        Ensures ISO strings are NOT parsed with dayfirst=True to prevent flip errors.
        """
        if not date_input:
            return None
        
        if isinstance(date_input, (date, datetime)):
            # If it's already a date/datetime object, just return the date part
            return date_input.date() if hasattr(date_input, 'date') else date_input
            
        date_str = str(date_input).strip()
        
        try:
            # 1. Check if it's already an ISO string (YYYY-MM-DD)
            # YYYY-MM-DD always has '-' at index 4
            if len(date_str) >= 10 and date_str[4] == '-' and date_str[:4].isdigit():
                return date_parser.parse(date_str).date()
            
            # 2. Check for ISO T format (2026-04-12T00:00:00Z)
            if 'T' in date_str:
                return date_parser.parse(date_str).date()
                
            # 3. Fallback to ambiguous format with dayfirst=True for Indian context
            # dateutil is smart enough to handle DD-MMM-YYYY (12-Apr-2026) with dayfirst=True too
            return date_parser.parse(date_str, dayfirst=True).date()
        except Exception:
            # Final fallback: generic parse
            try:
                return date_parser.parse(date_str).date()
            except:
                return None


    @staticmethod
    def _normalize_txn_type(raw_type: Any) -> str:
        """
        Unified normalization for transaction types.
        Maps Bank-Centric labels (DEBIT/CREDIT) to Investment-Centric ones (BUY/SELL).
        """
        if not raw_type:
            return "BUY"
            
        t = str(raw_type).upper().strip()
        
        # 1. Bank-Centric Normalization
        if "DEBIT" in t:
            return "BUY"
        if "CREDIT" in t:
            return "SELL"
            
        # 2. Investment-Centric Normalization (Withdrawals)
        is_withdrawal = any(kw in t for kw in MutualFundService.MF_WITHDRAWAL_KEYWORDS)
        if is_withdrawal:
            return "SELL"
            
        # 3. Default to current value if not explicitly a withdrawal
        return t


    @staticmethod
    def get_latest_sync_status(db: Session, tenant_id: str):
        """Get the latest sync log for a tenant"""
        return db.query(MutualFundSyncLog).filter(
            MutualFundSyncLog.tenant_id == tenant_id
        ).order_by(MutualFundSyncLog.started_at.desc()).first()

    @staticmethod
    async def refresh_tenant_navs(tenant_id: str, db: Optional[Session] = None):
        """
        Background task to refresh all NAVs for a tenant and update timeline cache.
        """
        # Close-at-end flag if we create our own session
        created_local_db = False
        if db is None:
            db = SessionLocal()
            created_local_db = True

        try:
            # 1. Create Sync Log
            sync_log = MutualFundSyncLog(
                tenant_id=tenant_id,
                status="running"
            )
            with db_write_lock:
                db.add(sync_log)
                db.commit()

            # 2. Get all holdings for the tenant
            holdings = db.query(MutualFundHolding).filter(
                MutualFundHolding.tenant_id == tenant_id,
                MutualFundHolding.is_deleted == False
            ).all()
            
            if not holdings:
                with db_write_lock:
                    sync_log.status = "completed"
                    sync_log.completed_at = timezone.utcnow()
                    db.commit()
                return {"status": "completed", "updated": 0}

            # 3. Synchronize all NAVs for this tenant using the Market Cache
            updated_count = 0
            for h in holdings:
                try:
                    # Offload to thread to keep the event loop responsive
                    # NAVService handles its own market_db_write_lock internally
                    await asyncio.to_thread(NAVService.sync_nav_history, h.scheme_code)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync NAV for {h.scheme_code}: {e}")

            # 4. Trigger holding updates from the fresh cache
            # This updates last_nav and current_value in the primary DB.
            # get_portfolio handles its own db_write_lock internally.
            MutualFundService.get_portfolio(db, tenant_id)
            
            # 5. Finalize Sync Log
            with db_write_lock:
                sync_log.status = "completed"
                sync_log.num_funds_updated = updated_count
                sync_log.completed_at = timezone.utcnow()
                db.commit()

            # 6. Recalculate Timeline for Today (pre-cache)
            try:
                MutualFundService.get_performance_timeline(db, tenant_id, period="1m", granularity="1d")
            except Exception:
                # Silent fallback for non-critical failures (consistent with repo pattern)
                pass

            return {"status": "completed", "updated": updated_count}

        except Exception as e:
            with db_write_lock:
                db.rollback()
                sync_log.status = "error"
                sync_log.completed_at = timezone.utcnow()
                sync_log.error_message = str(e)
                db.commit()
            raise e
        finally:
            if created_local_db:
                db.close()

    
    @staticmethod
    def _safe_commit(db: Session, max_retries: int = 5):
        """Helper to commit with retries. With global lock, this is mostly a fallback."""
        for i in range(max_retries):
            try:
                db.commit()
                return
            except Exception as e:
                if "Conflict" in str(e) and i < max_retries - 1:
                    time.sleep(0.1 * (2 ** i))
                    db.rollback()
                    # CRITICAL: We don't continue because rollback cleared the session.
                    # This should now be prevented by the global lock.
                raise e
    
    @staticmethod
    def get_mock_returns(scheme_code: str) -> Decimal:
        try:
            code_str = str(scheme_code or '0')
            hash_val = sum(ord(c) for c in code_str)
            base = 12 + (hash_val % 25)
            # Add some decimal variation based on hash to make it look real
            decimal = (hash_val % 10) / 10.0
            return float(f"{base + decimal:.1f}")
        except Exception:
            # Fallback mock return if calculation fails
            return 12.0

    @staticmethod
    def search_funds(query: Optional[str] = None, category: Optional[str] = None, amc: Optional[str] = None, limit: int = 20, offset: int = 0, sort_by: str = 'relevance', all_funds_cache: Optional[List[dict]] = None):
        """
        Search for mutual funds with server-side pagination.
        Returns Tuple[List[dict], int] containing the results and total count.
        """
        try:
            # Fetch the main list from MFAPI if not provided
            if all_funds_cache:
                all_funds = all_funds_cache
            else:
                response = httpx.get(f"{MFAPI_BASE_URL}")
                if response.status_code == 200:
                    all_funds = response.json()
                else:
                    return [], 0
            
            # Default recommendations if no query/filter
            if not any([query, category, amc]) and not all_funds_cache:
                # Popular Fund Scheme Codes (Examples of large well-known funds)
                featured_codes = [
                    '120716', # ICICI Prudential Bluechip Fund
                    '120503', # ICICI Prudential Value Discovery Fund
                    '101140', # HDFC Top 100 Fund
                    '100033', # Aditya Birla Sun Life Frontline Equity Fund
                    '118989', # Nippon India Large Cap Fund
                    '103133', # SBI Bluechip Fund
                    '120828', # ICICI Prudential Nifty 50 Index Fund
                    '103175', # HDFC Index Fund-NIFTY 50 Plan
                ]
                featured = [f for f in all_funds if str(f.get('schemeCode')) in featured_codes]
                if featured: 
                    # If we only show featured, the total is the featured count
                    # though usually we want to allow scrolling through all if query is empty
                    pass 

            query_low = query.lower() if query else None
            cat_low = category.lower() if category else None
            amc_low = amc.lower() if amc else None

            # Common inactive keywords to filter out (PRACTICES.md Section 10)
            inactive_keywords = ["(matured)", "(redeemed)", "liquidated", "terminated", "suspended"]

            # Filter and Paginate
            filtered_funds = []
            for f in all_funds:
                scheme_name = f.get('schemeName', '')
                scheme_name_low = scheme_name.lower()
                
                # Rule: Proactively filter out inactive/matured funds to reduce search noise
                if any(kw in scheme_name_low for kw in inactive_keywords):
                    continue

                # Standard filtering logic
                match = True
                if query_low and query_low not in scheme_name_low:
                    match = False
                
                if cat_low:
                    if cat_low == "index funds": cat_low = "index"
                    if cat_low not in scheme_name_low:
                        match = False
                        
                if amc_low and amc_low not in scheme_name_low: 
                    match = False
                    
                if match:
                    filtered_funds.append(f)

            total_count = len(filtered_funds)

            # Sorting
            if sort_by == 'returns_desc':
                filtered_funds.sort(key=lambda x: MutualFundService.get_mock_returns(str(x.get('schemeCode'))), reverse=True)
            elif sort_by == 'returns_asc':
                filtered_funds.sort(key=lambda x: MutualFundService.get_mock_returns(str(x.get('schemeCode'))))
            # Default 'relevance' keeps original order

            # Pagination
            start = offset
            end = offset + limit
            results = filtered_funds[start:end]
            
            # Enrich with mock data for UI completeness
            for r in results:
                scheme_code = str(r.get('schemeCode', '0'))
                # Mock metadata based on scheme code hash for consistency
                code_hash = sum(ord(c) for c in scheme_code)
                
                r['nav'] = Decimal(str(100.0 + (int(r.get('schemeCode', 0)) % 500) / 10.0))
                r['returns_3y'] = Decimal(str(MutualFundService.get_mock_returns(scheme_code)))
                r['category'] = "Mutual Fund" 
                
                # New Metadata for Overhaul
                r['risk_level'] = ['Low', 'Moderate', 'High', 'Very High'][code_hash % 4]
                r['aum'] = f"{(1000 + (code_hash % 9000)):,} Cr"
                r['trending'] = (code_hash % 7 == 0) # ~14% funds are trending
                r['rating'] = 3 + (code_hash % 3) # 3, 4, or 5 stars
                
                # Normalize keys for Pydantic (schemeCode -> scheme_code)
                r['scheme_code'] = r.pop('schemeCode', None)
                r['scheme_name'] = r.pop('schemeName', None)
                            
            return results, total_count
        except Exception as e:
            logger.error(f"Search error: {e}")
            return [], 0

    @staticmethod
    def get_portfolio_insights(db: Session, tenant_id: str, user_id: Optional[str] = None, force_refresh: bool = False):
        """
        Adheres to Section 16 of PRACTICES.md:
        1. Checks cache for instant return.
        2. Aggregates portfolio data & benchmarks logic lazily.
        """
        # OPTIMIZATION: Check cache BEFORE fetching slow market benchmarks
        if not force_refresh:
            cached = AIService.check_cache(db, tenant_id, "mutual_fund_portfolio_v5")
            if cached:
                return cached

        portfolio = MutualFundService.get_portfolio(db, tenant_id, user_id)
        
        if not portfolio:
            return {
                "summary": "No mutual fund holdings found to analyze.",
                "highlights": [],
                "suggestions": []
            }
            
        # Get market indices for benchmarking
        market_data = []
        try:
            market_data = MutualFundService.get_market_indices()
        except Exception: 
            # Silent fallback for AI mapping enrichment
            pass

        # Standardized AI Data Mapping
        ai_data = {
            "holdings": [],
            "benchmarks": market_data
        }
        
        for item in portfolio:
            ai_data["holdings"].append({
                "fund": item.get("scheme_name"),
                "category": item.get("category"),
                "invested": float(item.get("invested_value", 0)),
                "current": float(item.get("current_value", 0)),
                "returns_pct": float(item.get("profit_loss_pct", 0))
            })
            
        return AIService.generate_portfolio_insights(db, tenant_id, ai_data, force_refresh)

    @staticmethod
    def get_holding_insights(db: Session, tenant_id: str, holding_id: str, force_refresh: bool = False):
        """
        Generates fund-specific AI insights.
        Checks cache first unless force_refresh is true.
        """
        # Fetch holding details
        details = MutualFundService.get_holding_details(db, tenant_id, holding_id)
        
        # Fallback: if holding_id is numeric, it's an aggregated scheme view
        if not details and str(holding_id).isdigit():
            details = MutualFundService.get_scheme_details(db, tenant_id, holding_id)
            
        if not details:
            return None
            
        # Standardized Data for AI Deep-Dive
        ai_data = {
            "fund_name": details.get("scheme_name"),
            "category": details.get("category"),
            "invested": float(details.get("invested_value", 0)),
            "current": float(details.get("current_value", 0)),
            "profit_loss": float(details.get("profit_loss", 0)),
            "profit_loss_pct": float(details.get("profit_loss_pct", 0)),
            "units": float(details.get("units", 0)),
            "avg_price": float(details.get("average_price", 0)),
            "xirr": float(details.get("xirr", 0)) if details.get("xirr") else None,
            "last_nav": float(details.get("last_nav", 0)) if details.get("last_nav") else None
        }
        
        return AIService.generate_holding_insights(db, tenant_id, holding_id, ai_data, force_refresh)

    @staticmethod
    def get_fund_nav(scheme_code: str):
        try:
            response = httpx.get(f"{MFAPI_BASE_URL}/{scheme_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "SUCCESS":
                    # Meta: fund_house, scheme_type, scheme_category, scheme_code, scheme_name
                    # Data: date, nav
                    return data
            return None
        except Exception as e:
            return None

    @staticmethod
    def map_transactions_to_schemes(transactions: List[dict]):
        """Map raw transaction names/AMFI codes to MFAPI scheme codes."""
        if not transactions:
            return []
            
        all_funds = []
        amfi_map = {}
        try:
            import httpx
            resp = httpx.get("https://api.mfapi.in/mf", timeout=10.0)
            if resp.status_code == 200:
                all_funds = resp.json()
                amfi_map = {str(f['schemeCode']): f for f in all_funds}
        except Exception:
            pass
        mapped_results = []
        for txn in transactions:
            matched_scheme = None
            amfi_code = txn.get('amfi')
            
            # Normalize confusing bank terminology for Preview UI
            original_type = txn.get('type')
            if txn.get('is_synthesized'):
                txn['type'] = 'SUMMARY BALANCE'
            else:
                txn['type'] = MutualFundService._normalize_txn_type(original_type)
            
            if original_type != txn['type']:
                logger.info(f"[MAPPER] Normalized Type: {original_type} -> {txn['type']}")
            
            # 1. Try AMFI lookup
            if amfi_code and str(amfi_code) in amfi_map:
                matched_scheme = amfi_map[str(amfi_code)]
            
            # 2. Fallback to Name Search - Pass cache to avoid redundant fetches
            if not matched_scheme:
                results, _ = MutualFundService.search_funds(txn['scheme_name'], all_funds_cache=all_funds)
                if results:
                    matched_scheme = results[0]
            
            if matched_scheme:
                txn['scheme_code'] = matched_scheme['schemeCode']
                txn['mapped_name'] = matched_scheme['schemeName']
                txn['mapping_status'] = 'MAPPED'
            else:
                txn['mapping_status'] = 'UNMAPPED'
                txn['error'] = "Could not map scheme to master list"
            
            # Mark as duplicate (will be checked by endpoints that have db access)
            txn['is_duplicate'] = False  # Default, will be updated by endpoint
            
            # Standardize date format using safe parsing for Indian context
            if 'date' in txn:
                parsed_date = MutualFundService._parse_date_safely(txn['date'])
                if parsed_date:
                    txn['date'] = parsed_date.strftime("%Y-%m-%d")
            
            mapped_results.append(txn)
            
        return mapped_results
    
    @staticmethod
    def check_duplicates(db: Session, tenant_id: str, transactions: List[dict]) -> List[dict]:
        """
        Check which transactions are duplicates of existing orders.
        Returns the same list with 'is_duplicate' flag set.
        """
        try:
            from datetime import datetime, date
        
            for txn in transactions:
                is_duplicate = False
                scheme_code = txn.get('scheme_code')
            
                # Only check if successfully mapped
                if scheme_code:
                    user_id = txn.get('user_id')
                    external_id = txn.get('external_id')
                    
                    if external_id:
                        existing = db.query(MutualFundOrder.id).filter(
                            MutualFundOrder.tenant_id == tenant_id,
                            MutualFundOrder.user_id == user_id,
                            MutualFundOrder.external_id == external_id,
                            MutualFundOrder.is_deleted == False
                        ).first()
                        if existing:
                            is_duplicate = True

                    
                    if not is_duplicate and txn.get('is_synthesized'):
                        scheme_code_str = str(scheme_code).strip()
                        try:
                            rounded_units = abs(round(float(txn.get('units', 0)), 4))
                        except (ValueError, TypeError):
                            rounded_units = 0.0
                            
                        # Check for existing holding balance regardless of user_id (if it belongs to tenant)
                        existing_holding = db.query(MutualFundHolding).filter(
                            MutualFundHolding.tenant_id == tenant_id,
                            MutualFundHolding.scheme_code == scheme_code_str,
                            MutualFundHolding.is_deleted == False
                        ).first()
                        
                        if existing_holding:
                            db_units = abs(float(existing_holding.units))
                            diff = abs(db_units - rounded_units)

                            
                            # For synthesized balance entries: If we already have >= units, it's likely already imported.
                            # This handles cases where a previous import doubled the units.
                            if db_units >= rounded_units - 0.001:
                                is_duplicate = True
                
                # Priority 3: Check by field match (For historical transactions)
                if not is_duplicate:
                    txn_date = MutualFundService._parse_date_safely(txn.get('date'))
                    
                    if txn_date:
                        # Fix: Normalize type and sign for comparison
                        txn_type = txn.get('type', 'BUY')
                        if txn_type == "DEBIT": txn_type = "BUY"
                        elif txn_type == "CREDIT": txn_type = "SELL"
                        
                        rounded_units = abs(round(float(txn.get('units', 0)), 4))
                        rounded_amount = abs(round(float(txn.get('amount', 0)), 2))

                        # Ensure scheme_code is string for DB query
                        scheme_code_str = str(scheme_code).strip()
                        
                        # Candidate search: Fetch ALL orders for this scheme (safer to filter in Python)
                        # Relax user_id check to include legacy (NULL) records
                        candidates = db.query(MutualFundOrder).filter(
                            MutualFundOrder.tenant_id == tenant_id,
                            (MutualFundOrder.user_id == user_id) | (MutualFundOrder.user_id.is_(None)),
                            MutualFundOrder.scheme_code == scheme_code_str,
                            MutualFundOrder.is_deleted == False
                        ).all()
                        
                        def normalize_type(t_str):
                            t = str(t_str).upper().strip()
                            
                            withdrawal_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_WITHDRAWAL_KEYWORDS) + r')\b'
                            investment_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_INVESTMENT_KEYWORDS) + r')\b'
                            
                            if re.search(withdrawal_pattern, t): return "SELL"
                            if re.search(investment_pattern, t): return "BUY"
                            return t

                        # Python-side robust matching
                        for result in candidates:
                            # 1. Date Check
                            db_date = result.order_date.date() if hasattr(result.order_date, 'date') else result.order_date
                            if db_date != txn_date:
                                continue

                            # 2. Units/Amount Check (Epsilon)
                            db_units = abs(float(result.units))
                            db_amount = abs(float(result.amount))
                            
                            if not (abs(db_units - rounded_units) < 0.001 and abs(db_amount - rounded_amount) < 0.01):
                                continue

                            # 3. Type Check (Robust Normalization)
                            db_type_norm = normalize_type(result.type)
                            input_type_norm = normalize_type(txn_type)
                            
                            if db_type_norm == input_type_norm:
                                is_duplicate = True
                                break
            
                txn['is_duplicate'] = is_duplicate
        
            return transactions
        except Exception as e:
            raise e

    @staticmethod
    def import_mapped_transactions(db: Session, tenant_id: str, transactions: List[dict]):
        """Bulk ingest transactions under a global lock."""
        stats = {"processed": 0, "failed": 0, "details": {"imported": [], "failed": []}}
        
        
        affected_schemes = set()
        
        with db_write_lock:
            for idx, txn in enumerate(transactions):
                try:
                    result = MutualFundService._add_transaction_logic(db, tenant_id, txn)
                    
                    if result and hasattr(result, 'id'):
                        stats["processed"] += 1
                        stats["details"]["imported"].append(txn)
                        if hasattr(result, 'scheme_code'):
                            affected_schemes.add(result.scheme_code)
                    else:
                        stats["failed"] += 1
                        txn['error'] = "No order returned"
                        stats["details"]["failed"].append(txn)
                except Exception as e:
                    txn['error'] = str(e)
                    stats["failed"] += 1
                    stats["details"]["failed"].append(txn)
            
            # Recalculate affected holdings for data integrity
            for scheme_code in affected_schemes:
                try:
                    MutualFundService._recalculate_holdings_logic(db, tenant_id, scheme_code=scheme_code)
                except Exception as e:
                    logger.error(f"Failed to recalculate holding for {scheme_code} after import: {e}")

            MutualFundService._safe_commit(db)
            
            # Force DuckDB checkpoint to ensure visibility for other sessions (readers)
            try:
                db.execute(text("PRAGMA force_checkpoint;"))
            except Exception as e:
                logger.warning(f"Failed to force DuckDB checkpoint: {e}")
            
        return stats

    @staticmethod
    def add_transaction(db: Session, tenant_id: str, data: dict):
        """Public method that wraps logic in a global lock for DuckDB safety."""
        with db_write_lock:
            result = MutualFundService._add_transaction_logic(db, tenant_id, data)
            MutualFundService._safe_commit(db)
            return result

    @staticmethod
    def _add_transaction_logic(db: Session, tenant_id: str, data: dict):
        # 1. Ensure Meta exists
        scheme_code = str(data['scheme_code'])
        meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == scheme_code).first()
        
        if not meta:
            # Fetch from API and save
            fund_data = MutualFundService.get_fund_nav(scheme_code)
            if fund_data:
                meta_info = fund_data.get("meta", {})
                meta = MutualFundsMeta(
                    scheme_code=str(meta_info.get("scheme_code")),
                    scheme_name=meta_info.get("scheme_name"),
                    fund_house=meta_info.get("fund_house"),
                    category=meta_info.get("scheme_category")
                )
                db.add(meta)
                db.flush() # Use flush instead of commit to allow external batching
            else:
                raise ValueError("Invalid Scheme Code or API Error")

        # 2. Check for duplicate order (Idempotency)
        user_id = data.get('user_id')
        external_id = data.get('external_id')
        
        # Priority 1: Check by External ID
        if external_id:
            existing_order = db.query(MutualFundOrder).filter(
                MutualFundOrder.tenant_id == tenant_id,
                MutualFundOrder.user_id == user_id,
                MutualFundOrder.external_id == external_id,
                MutualFundOrder.is_deleted == False
            ).first()
            if existing_order:
                return existing_order

        # Priority 2: Check by exact match with precision handling
        # Use rounding to avoid float representation issues in DuckDB/Python
        from sqlalchemy import func
        
        txn_date = MutualFundService._parse_date_safely(data['date'])
        if not txn_date:
            raise ValueError(f"Could not parse transaction date: {data['date']}")

        # Fix confusing bank type labels before saving
        original_type = data.get('type', 'BUY')
        raw_type = MutualFundService._normalize_txn_type(original_type) if not data.get('is_synthesized') else 'SUMMARY BALANCE'
        
        if str(original_type).upper().strip() != raw_type:
            logger.info(f"[INGESTION] Normalized Type for {scheme_code}: {original_type} -> {raw_type}")
            
        is_withdrawal = (raw_type == "SELL")
        normalized_type = "SELL" if is_withdrawal else "BUY"
        
        rounded_units = abs(round(float(data['units']), 4))
        rounded_amount = abs(round(float(data['amount']), 2))
        
        # Check for duplicates by looking for ANY order on same date/units/amount for this fund
        # RECENT HARDENING: We search for ALL orders (including deleted ones) to support revival
        existing_order = db.query(MutualFundOrder).filter(
            MutualFundOrder.tenant_id == tenant_id,
            MutualFundOrder.user_id == user_id,
            MutualFundOrder.scheme_code == scheme_code,
            func.date(MutualFundOrder.order_date) == txn_date,
            func.round(func.abs(MutualFundOrder.units), 4) == rounded_units,
            func.round(func.abs(MutualFundOrder.amount), 2) == rounded_amount
        ).first()

        if existing_order:
            # Check if existing order type is logically the same
            existing_type = str(existing_order.type).upper().strip()
            # Robust Type Check: Compare normalized withdrawal status to prevent cross-type revival
            existing_is_withdrawal = (MutualFundService._normalize_txn_type(existing_type) == "SELL")
            
            if existing_is_withdrawal == is_withdrawal:
                # REVIVAL LOGIC: If the existing order was deleted, restore it instead of creating a duplicate
                if existing_order.is_deleted:
                    existing_order.is_deleted = False
                    existing_order.deleted_at = None
                    db.flush()

                # SELF-HEALING: Ensure the holding for this existing order is revived if it was accidentally deleted
                if existing_order.holding_id:
                    h = db.query(MutualFundHolding).filter(MutualFundHolding.id == existing_order.holding_id).first()
                    if h and h.is_deleted:
                        h.is_deleted = False
                        h.deleted_at = None
                        db.flush()
                
                # NOTE: We return the revived order. import_mapped_transactions will handle 
                # bulk recalculation of the holding balance at the end.
                return existing_order

        # 3. Create Order
        order = MutualFundOrder(
            tenant_id=tenant_id,
            user_id=user_id,
            scheme_code=scheme_code,
            type=raw_type, # PRESERVE original type (SIP, TOPUP, etc.)
            amount=abs(float(data['amount'])),
            units=abs(float(data['units'])),
            nav=abs(float(data['nav'])),
            order_date=txn_date,
            external_id=external_id,
            folio_number=data.get('folio_number'),
            import_source=data.get('import_source', 'MANUAL')
        )
        db.add(order)
        
        # 3. Update Holding
        return MutualFundService._update_holding_with_order(db, tenant_id, order, data.get('folio_number'))

    @staticmethod
    def _update_holding_with_order(db: Session, tenant_id: str, order: MutualFundOrder, folio_number: Optional[str] = None):
        """Internal helper to shared between live ingestion and recalculation"""
        user_id = order.user_id
        scheme_code = order.scheme_code
        
        # Find/Create Holding
        query = db.query(MutualFundHolding).filter(
            MutualFundHolding.tenant_id == tenant_id,
            MutualFundHolding.user_id == user_id,
            MutualFundHolding.scheme_code == scheme_code
        )
        
        if folio_number:
            query = query.filter(MutualFundHolding.folio_number == folio_number)
        else:
            query = query.filter(MutualFundHolding.folio_number.is_(None))
            
        holding = query.first()

        if not holding:
            holding = MutualFundHolding(
                tenant_id=tenant_id,
                user_id=user_id,
                scheme_code=scheme_code,
                folio_number=folio_number,
                units=0,
                average_price=0
            )
            db.add(holding)
            db.flush() 
        else:
            # REVIVAL: If holding was soft-deleted, bring it back as we have an active order for it
            if holding.is_deleted:
                holding.is_deleted = False
                holding.deleted_at = None
                holding.units = 0
                holding.average_price = 0
                holding.invested_value = 0
                holding.current_value = 0
            
            if folio_number:
                holding.folio_number = folio_number
        
        # Update Balance with hardened regex matching
        o_type = str(order.type).upper().strip()
        
        # Regex patterns for word-boundary matching
        withdrawal_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_WITHDRAWAL_KEYWORDS) + r')\b'
        investment_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_INVESTMENT_KEYWORDS) + r')\b'
        
        is_withdrawal = bool(re.search(withdrawal_pattern, o_type))
        is_investment = not is_withdrawal and bool(re.search(investment_pattern, o_type))
        
        if is_investment:
            current_units = Decimal(str(holding.units or 0.0))
            current_avg = Decimal(str(holding.average_price or 0.0))
            
            order_units = Decimal(str(order.units))
            order_amount = Decimal(str(order.amount))
            txn_cost = order_amount if order_amount > 0 else (Decimal(str(order.nav)) * order_units)
            
            total_cost = (current_avg * current_units) + txn_cost
            total_units = current_units + order_units
            
            holding.average_price = total_cost / total_units if total_units > 0 else Decimal("0.0")
            holding.units = total_units
            holding.invested_value = total_units * Decimal(str(holding.average_price))
        elif is_withdrawal:
            current_units = Decimal(str(holding.units or 0.0))
            new_units = max(Decimal("0.0"), current_units - Decimal(str(order.units)))
            holding.units = new_units
            # For withdrawals, invested value (cost) reduces proportionally to units
            holding.invested_value = new_units * Decimal(str(holding.average_price or 0.0))
        
        # Update NAV Info
        if not holding.last_nav or Decimal(str(holding.last_nav)) == 0:
            holding.last_nav = order.nav
            holding.last_updated_at = order.order_date
        
        holding.current_value = Decimal(str(holding.units)) * Decimal(str(holding.last_nav or 0.0))

        # Ensure holding has an ID before linking
        if not holding.id:
            db.flush()  # Force ID generation
        
        order.holding_id = holding.id
        db.flush() 
        return order

    @staticmethod
    def cleanup_duplicates(db: Session, tenant_id: str):
        """Find and remove duplicate orders, then rebuild holdings."""
        with db_write_lock:
            # 1. Find duplicate groups
            from sqlalchemy import func
            duplicates = db.query(
                MutualFundOrder.scheme_code, 
                MutualFundOrder.order_date, 
                MutualFundOrder.units, 
                MutualFundOrder.amount, 
                MutualFundOrder.type
            ).filter(MutualFundOrder.tenant_id == tenant_id).group_by(
                MutualFundOrder.scheme_code, 
                MutualFundOrder.order_date, 
                MutualFundOrder.units, 
                MutualFundOrder.amount, 
                MutualFundOrder.type
            ).having(func.count('*') > 1).all()
            
            removed_count = 0
            for sc, d, u, a, t in duplicates:
                all_matches = db.query(MutualFundOrder).filter(
                    MutualFundOrder.tenant_id == tenant_id,
                    MutualFundOrder.scheme_code == sc,
                    MutualFundOrder.order_date == d,
                    MutualFundOrder.units == u,
                    MutualFundOrder.amount == a,
                    MutualFundOrder.type == t
                ).order_by(MutualFundOrder.created_at).all()
                
                to_delete = all_matches[1:]
                for order in to_delete:
                    db.delete(order)
                    removed_count += 1
                    
            MutualFundService._safe_commit(db)
            
            # 2. Recalculate holdings (nested call, same lock thread)
            # Actually _update_holding_with_order is used inside recalculate_holdings
            # We call the internal logic to avoid re-taking the lock if it's already held by us
            # But threading.Lock() is NOT re-entrant. 
            # I should use an RLock or call an internal method.
            MutualFundService._recalculate_holdings_logic(db, tenant_id)
            
            return removed_count

    @staticmethod
    def recalculate_holdings(db: Session, tenant_id: str, user_id: Optional[str] = None):
        with db_write_lock:
            return MutualFundService._recalculate_holdings_logic(db, tenant_id, user_id)

    @staticmethod
    def _recalculate_holdings_logic(db: Session, tenant_id: str, user_id: Optional[str] = None, scheme_code: Optional[str] = None):
        """Internal logic without lock for nested calls"""
        # 1. Get all active orders sorted by date
        query = db.query(MutualFundOrder).filter(
            MutualFundOrder.tenant_id == tenant_id,
            MutualFundOrder.is_deleted == False
        )
        if user_id:
            query = query.filter(MutualFundOrder.user_id == user_id)
        if scheme_code:
            query = query.filter(MutualFundOrder.scheme_code == scheme_code)
        
        orders = query.order_by(MutualFundOrder.order_date).all()
        
        # 2. Reset existing holdings instead of deleting (Preserves UUIDs)
        # We include deleted holdings here to allow the clean logic to "revive" them
        h_query = db.query(MutualFundHolding).filter(
            MutualFundHolding.tenant_id == tenant_id
        )
        if user_id:
            h_query = h_query.filter(MutualFundHolding.user_id == user_id)
        if scheme_code:
            h_query = h_query.filter(MutualFundHolding.scheme_code == scheme_code)
        
        # We reset metrics to 0 and then rebuild. This allows _update_holding_with_order 
        # to find and update the existing record based on (scheme_code, folio_number).
        h_query.update({
            "units": 0,
            "average_price": 0,
            "invested_value": 0,
            "current_value": 0
        }, synchronize_session=False)
        db.flush()
        
        # 3. Process each order (rebuilds the metrics on the same UUIDs)
        processed_orders = []
        for order in orders:
            MutualFundService._update_holding_with_order(db, tenant_id, order, order.folio_number)
            processed_orders.append(order)
        
        # 4. Clean up: Soft-delete holdings that ended up with zero units and no non-deleted orders
        # (This handles the case where all transactions for a fund were deleted)
        zero_holdings = h_query.filter(MutualFundHolding.units == 0).all()
        for h in zero_holdings:
            # Final check: does it have ANY active orders?
            active_order_count = db.query(MutualFundOrder).filter(
                MutualFundOrder.holding_id == h.id,
                MutualFundOrder.is_deleted == False
            ).count()
            
            if active_order_count == 0:
                h.is_deleted = True
                h.deleted_at = timezone.utcnow()
        
        # 5. Special Commit
        MutualFundService._safe_commit(db)
        return len(processed_orders)

    @staticmethod
    def delete_holding(db: Session, tenant_id: str, holding_id: str):
        with db_write_lock:
            # Detect Aggregate (Grouped) Deletion (group- prefix OR numeric scheme_code)
            is_aggregate = holding_id.startswith("group-") or holding_id.startswith("group_") or holding_id.isdigit()
            
            if is_aggregate:
                # Extract scheme_code (supports both hyphen, underscore, and raw numeric formats)
                if holding_id.isdigit():
                    scheme_code = holding_id
                else:
                    delimiter = "-" if "-" in holding_id else "_"
                    scheme_code = holding_id.split(delimiter)[1]
                
                # HARDENING: Find ALL holdings for this scheme to ensure we clear the state completely
                holdings = db.query(MutualFundHolding).filter(
                    MutualFundHolding.tenant_id == tenant_id,
                    MutualFundHolding.scheme_code == scheme_code
                ).all()
                
                for h in holdings:
                    h.is_deleted = True
                    h.deleted_at = timezone.utcnow()
                
                # HARDENING: Delete EVERY active order for this scheme/tenant.
                # This catches orphaned transactions that might not have a holding_id.
                db.query(MutualFundOrder).filter(
                    MutualFundOrder.scheme_code == scheme_code,
                    MutualFundOrder.tenant_id == tenant_id,
                    MutualFundOrder.is_deleted == False
                ).update({
                    "is_deleted": True,
                    "deleted_at": timezone.utcnow()
                }, synchronize_session=False)
                
                MutualFundService._safe_commit(db)
                return True

            # Handle Single Folio Deletion
            holding = db.query(MutualFundHolding).filter(
                MutualFundHolding.id == holding_id,
                MutualFundHolding.tenant_id == tenant_id
            ).first()
            
            if not holding:
                raise Exception("Holding not found")
            
            scheme_code = holding.scheme_code
            folio_number = holding.folio_number

            # Soft delete the holding
            holding.is_deleted = True
            holding.deleted_at = timezone.utcnow()
            
            # HARDENING: Delete associated orders by holding_id OR folio/scheme match.
            # This ensures orphaned/mislinked orders for this folio are also cleared.
            order_query = db.query(MutualFundOrder).filter(
                MutualFundOrder.tenant_id == tenant_id,
                MutualFundOrder.scheme_code == scheme_code,
                MutualFundOrder.is_deleted == False
            )
            
            if folio_number:
                order_query = order_query.filter(
                    (MutualFundOrder.holding_id == holding_id) | 
                    (MutualFundOrder.folio_number == folio_number)
                )
            else:
                order_query = order_query.filter(
                    (MutualFundOrder.holding_id == holding_id) | 
                    (MutualFundOrder.folio_number.is_(None))
                )

            order_query.update({
                "is_deleted": True,
                "deleted_at": timezone.utcnow()
            }, synchronize_session=False)
            
            MutualFundService._safe_commit(db)
            return True

    @staticmethod
    def get_portfolio(db: Session, tenant_id: str, user_id: Optional[str] = None):
        
        query = db.query(MutualFundHolding).filter(
            MutualFundHolding.tenant_id == tenant_id,
            MutualFundHolding.is_deleted == False
        )
        if user_id:
            query = query.filter(MutualFundHolding.user_id == user_id)
        
        holdings = query.all()
        results = []
        
        # Check for updates needed (Stale > 24h or None)
        updates_made = False
        today = timezone.utcnow().date()
        
        # Removed async fetching logic
        
        # NAV updates are now handled via local cache and triggered in the background
        
        # Phase 1: Update Holdings (Write Lock)
        updates_made = False
        with db_write_lock:
            try:
                for h in holdings:
                    # Get latest NAV from local cache
                    nav_data = NAVService.get_latest_nav(h.scheme_code)
                    
                    if nav_data:
                        latest_nav = Decimal(str(nav_data["nav"]))
                        nav_date_obj = nav_data["nav_date_obj"]
                        
                        has_changed = False
                        # NAV Update
                        if not h.last_nav or abs(Decimal(str(h.last_nav)) - latest_nav) > Decimal("0.0001"):
                            h.last_nav = latest_nav
                            has_changed = True
                        
                        # Value Update
                        current_units = Decimal(str(h.units or 0.0))
                        new_value = current_units * latest_nav
                        if not h.current_value or abs(Decimal(str(h.current_value)) - new_value) > Decimal("0.01"):
                            h.current_value = new_value
                            has_changed = True
                        
                        # Date Update
                        if not h.last_updated_at or h.last_updated_at != nav_date_obj:
                            h.last_updated_at = nav_date_obj
                            has_changed = True
                            
                        if has_changed:
                            updates_made = True
                
                if updates_made:
                    MutualFundService._safe_commit(db)
            except Exception as e:
                db.rollback()

        # Phase 2: Build Results (Read-Only)
        
        for h in holdings:
            try:
                # Fetch sparkline from market cache
                sparkline = NAVService.get_sparkline(h.scheme_code, days=30)
                
                # Accessing properties triggers reload if needed. 
                # Catch ObjectDeletedError if a concurrent process removed the record.
                units = Decimal(str(h.units or 0.0))
                avg_price = Decimal(str(h.average_price or 0.0))
                current_val = Decimal(str(h.current_value or 0.0))
                invested = units * avg_price
                pl = (current_val - invested) if current_val > 0 else Decimal("0.0")
                last_updated_str = h.last_updated_at.strftime("%d-%b-%Y") if h.last_updated_at else "N/A"
                
                # Fetch meta
                meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == h.scheme_code).first()
                
                # Latest NAV handling
                last_nav = Decimal(str(h.last_nav or 0.0))
                
            except (ObjectDeletedError, Exception):
                # Skip if record was deleted concurrently
                continue

            results.append({
                "id": str(h.id),
                "scheme_name": h.scheme_name,
                "scheme_code": h.scheme_code,
                "category": meta.category if meta else "Other",
                "folio_number": h.folio_number,
                "units": units,
                "average_price": avg_price,
                "current_value": current_val,
                "invested_value": invested,
                "profit_loss": pl,
                "profit_loss_pct": round(float(pl / invested * 100) if invested > 0 else 0, 2),
                "last_nav": last_nav,
                "last_updated_at": last_updated_str,
                "goal_id": str(h.goal_id) if h.goal_id else None,
                "goal_name": h.goal.name if h.goal else None,
                "sparkline": sparkline
            })

            
        return results

    @staticmethod
    def get_holding_details(db: Session, tenant_id: str, holding_id: str):
        
        # Joined query to get user name
        result = db.query(MutualFundHolding, User.full_name, User.avatar).outerjoin(
            User, MutualFundHolding.user_id == User.id
        ).filter(
            MutualFundHolding.id == holding_id,
            MutualFundHolding.tenant_id == tenant_id,
            MutualFundHolding.is_deleted == False
        ).first()
        
        if not result:
            return None
            
        holding, user_name, user_avatar = result
        meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == holding.scheme_code).first()
        
        # Fetch Goal info if linked
        goal_info = None
        # 1. Fetch Metadata & Orders
        if holding.goal_id:
            goal = db.query(InvestmentGoal).filter(InvestmentGoal.id == holding.goal_id).first()
            if goal:
                goal_info = {
                    "id": goal.id,
                    "name": goal.name,
                    "icon": goal.icon,
                    "color": goal.color,
                    "target_amount": float(goal.target_amount),
                    "is_completed": goal.is_completed
                }
        
        orders = db.query(MutualFundOrder).filter(
            MutualFundOrder.holding_id == holding.id,
            MutualFundOrder.tenant_id == tenant_id,
            MutualFundOrder.is_deleted == False
        ).order_by(MutualFundOrder.order_date.desc()).all()

        # 2. Fetch Full NAV History (with Cache-First + Live Fallback)
        nav_history = []
        try:
            start_date = None
            if orders:
                earliest_order = orders[-1].order_date
                start_date = earliest_order.date()
            else:
                start_date = (timezone.utcnow() - timedelta(days=365)).date()

            today = timezone.utcnow().date()
            nav_history = NAVService.get_nav_history(holding.scheme_code, start_date, today)
            
            # If cache is empty, use fetch_live_nav_history as fallback
            if not nav_history:
                live_data = NAVService.fetch_live_nav_history(holding.scheme_code, days=365*5) # 5y fallback
                nav_history = live_data.get("history", [])
                
                # Still trigger a background sync to populate the database cache
                threading.Thread(target=NAVService.sync_nav_history, args=(holding.scheme_code,)).start()

        except Exception as e:
            logger.error(f"Failed to fetch NAV history for {holding.scheme_code}: {e}")

        # 3. Calculate current value based on latest NAV if missing/stale
        current_value = Decimal(str(holding.current_value or 0))
        if nav_history and (current_value == 0 or holding.last_updated_at < timezone.utcnow() - timedelta(hours=24)):
            latest_nav = Decimal(str(nav_history[-1]['value']))
            current_value = Decimal(str(holding.units or 0)) * latest_nav

        # 4. Calculate XIRR for this specific fund
        cash_flows = []
        total_invested = Decimal('0.0')
        for order in orders:
            o_type = str(order.type).upper().strip()
            
            # Rule: Skip Reinvestments (They are not fresh capital flows)
            if any(kw in o_type for kw in MutualFundService.MF_REINVESTMENT_KEYWORDS):
                continue
            
            # Note: For fund-specific XIRR, internal switches ARE included 
            # because they represent capital entry/exit for THIS fund.
            
            amount = Decimal(str(order.amount))
            if amount <= 0:
                amount = Decimal(str(order.units)) * Decimal(str(order.nav))
            
            order_date = order.order_date.date() if hasattr(order.order_date, 'date') else order.order_date
            
            withdrawal_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_WITHDRAWAL_KEYWORDS) + r')\b'
            investment_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_INVESTMENT_KEYWORDS) + r')\b'
            
            is_withdrawal = bool(re.search(withdrawal_pattern, o_type))
            is_investment = not is_withdrawal and bool(re.search(investment_pattern, o_type))

            if is_investment:
                cash_flows.append((order_date, -float(amount)))
                total_invested += amount
            elif is_withdrawal:
                cash_flows.append((order_date, float(amount)))
        
        if current_value > 0:
            cash_flows.append((timezone.utcnow().date(), float(current_value)))
            
        xirr_value = None
        try:
            if len(cash_flows) >= 2:
                sum_out = sum(cf[1] for cf in cash_flows if cf[1] < 0)
                if abs(sum_out) > 0.01:
                    xirr_decimal = xirr(cash_flows)
                    if xirr_decimal is not None and -0.99 < xirr_decimal < 10:
                        xirr_value = round(xirr_decimal * 100, 2)
                    else:
                        xirr_value = None
        except:
            xirr_value = None

        # Format orders for response
        orders_list = []
        for o in orders:
            orders_list.append({
                "id": o.id,
                "type": MutualFundService._normalize_txn_type(o.type),
                "amount": Decimal(str(o.amount)),
                "units": Decimal(str(o.units)),
                "nav": Decimal(str(o.nav)),
                "date": o.order_date.strftime("%Y-%m-%d"),
                "status": o.status
            })

        # 5. Build Response Object
        holding_response = {
            "id": holding.id,
            "scheme_name": meta.scheme_name if meta else "Unknown Fund",
            "scheme_code": holding.scheme_code,
            "isin_growth": meta.isin_growth if meta else None,
            "isin_reinvest": meta.isin_reinvest if meta else None,
            "fund_house": meta.fund_house if meta else None,
            "folio_number": holding.folio_number,
            "category": meta.category if meta else "Other",
            "user_id": holding.user_id,
            "user_name": user_name or "Unassigned",
            "user_avatar": user_avatar,
            "goal": goal_info,
            "units": Decimal(str(holding.units or 0)),
            "average_price": Decimal(str(holding.average_price or 0)),
            "current_value": current_value,
            "invested_value": Decimal(str(holding.units or 0)) * Decimal(str(holding.average_price or 0)),
            "profit_loss": current_value - (Decimal(str(holding.units or 0)) * Decimal(str(holding.average_price or 0))),
            "last_nav": Decimal(str(nav_history[-1]['value'])) if nav_history else Decimal(str(holding.last_nav or 0)),
            "last_updated_at": holding.last_updated_at.strftime("%Y-%m-%d") if holding.last_updated_at else None,
            "xirr": xirr_value,
            "transactions": orders_list,
            "nav_history": nav_history
        }

        # 6. Benchmark Comparison Logic
        benchmarks_list = []
        if meta and meta.category:
            bm = BenchmarkService.get_or_create_benchmark_mapping(db, meta.category)
            if bm:
                style = {
                    "color": bm.styling_color,
                    "style": bm.styling_style,
                    "dashArray": bm.styling_dash_array,
                }
                try:
                    # Use same start_date as fund history
                    fund_start_date = None
                    if nav_history:
                        fund_start_date = datetime.strptime(nav_history[0]['date'], "%Y-%m-%d").date()

                    # Use Cached Benchmark History
                    bm_history = NAVService.get_nav_history(bm.benchmark_symbol, fund_start_date or start_date, today)
                    
                    if not bm_history:
                        threading.Thread(target=NAVService.sync_nav_history, args=(bm.benchmark_symbol,)).start()
                    else:
                        benchmarks_list.append({
                            "symbol": bm.benchmark_symbol,
                            "label": bm.benchmark_label,
                            "styling": style,
                            "history": bm_history
                        })
                except Exception as e:
                    logger.warning(f"Failed to fetch cached benchmark history for {bm.benchmark_label}: {e}")

        holding_response["benchmarks"] = benchmarks_list
        return holding_response

    @staticmethod
    def get_scheme_details(db: Session, tenant_id: str, scheme_code: str):
        
        # 1. Fetch Metadata
        meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == scheme_code).first()
        
        # 2. Fetch All Holdings for this Scheme
        holdings = db.query(MutualFundHolding).filter(
            MutualFundHolding.tenant_id == tenant_id,
            MutualFundHolding.scheme_code == scheme_code,
            MutualFundHolding.is_deleted == False
        ).all()
            
        # 3. Fetch All Orders for this Scheme
        orders = db.query(MutualFundOrder).filter(
            MutualFundOrder.tenant_id == tenant_id,
            MutualFundOrder.scheme_code == scheme_code,
            MutualFundOrder.is_deleted == False
        ).order_by(MutualFundOrder.order_date.desc()).all()
        
        # 4. Fetch Full NAV History (with Cache-First + Live Fallback)
        nav_history = []
        try:
            start_date = None
            if orders:
                earliest_order = orders[-1].order_date
                start_date = earliest_order.date() if hasattr(earliest_order, 'date') else earliest_order
            else:
                start_date = (timezone.utcnow() - timedelta(days=365)).date()
            
            today = timezone.utcnow().date()
            nav_history = NAVService.get_nav_history(scheme_code, start_date, today)
            
            if not nav_history:
                live_data = NAVService.fetch_live_nav_history(scheme_code, days=365*5)
                nav_history = live_data.get("history", [])
                threading.Thread(target=NAVService.sync_nav_history, args=(scheme_code,)).start()
        except Exception as e:
            logger.error(f"Failed to fetch NAV history for scheme {scheme_code}: {e}")

        # 5. Aggregation Logic
        total_units = Decimal('0.0')
        total_current_value = Decimal('0.0')
        total_invested_value = Decimal('0.0')
        
        user_ids = set()
        folio_numbers = set()
        
        for h in holdings:
            u = Decimal(str(h.units or 0))
            avg = Decimal(str(h.average_price or 0))
            total_units += u
            total_invested_value += (u * avg)
            
            if h.user_id: user_ids.add(h.user_id)
            if h.folio_number: folio_numbers.add(h.folio_number)

        # Update total_current_value based on latest NAV from history
        if nav_history:
            latest_nav = Decimal(str(nav_history[-1]['value']))
            total_current_value = total_units * latest_nav
        else:
            total_current_value = sum(Decimal(str(h.current_value or 0)) for h in holdings)
        
        # Weighted Average Price
        avg_price = total_invested_value / total_units if total_units > 0 else Decimal('0.0')
        profit_loss = total_current_value - total_invested_value
        
        # 6. XIRR Calculation (Combined)
        cash_flows = []
        for order in orders:
            o_type = str(order.type).upper().strip()
            
            # Rule: Skip Reinvestments
            if any(kw in o_type for kw in MutualFundService.MF_REINVESTMENT_KEYWORDS):
                continue
            
            amount = Decimal(str(order.amount))
            if amount <= 0:
                amount = Decimal(str(order.units)) * Decimal(str(order.nav))
            
            order_date = order.order_date.date() if hasattr(order.order_date, 'date') else order.order_date
            
            withdrawal_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_WITHDRAWAL_KEYWORDS) + r')\b'
            investment_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_INVESTMENT_KEYWORDS) + r')\b'
            
            is_withdrawal = bool(re.search(withdrawal_pattern, o_type))
            is_investment = not is_withdrawal and bool(re.search(investment_pattern, o_type))

            if is_investment:
                cash_flows.append((order_date, -float(amount)))
            elif is_withdrawal:
                cash_flows.append((order_date, float(amount)))
        
        if total_current_value > 0:
            cash_flows.append((timezone.utcnow().date(), float(total_current_value)))
            
        xirr_value = None
        try:
            if len(cash_flows) >= 2:
                sum_out = sum(cf[1] for cf in cash_flows if cf[1] < 0)
                if abs(sum_out) > 0.01:
                    xirr_decimal = xirr(cash_flows)
                    if xirr_decimal is not None and -0.99 < xirr_decimal < 10:
                        xirr_value = round(xirr_decimal * 100, 2)
                    else:
                        xirr_value = None
        except:
            xirr_value = None

        # 7. Formatting & User Info
        owners_map = {}
        all_users = db.query(User).filter(User.tenant_id == tenant_id).all()
        user_lookup = {str(u.id): u for u in all_users}
        
        for uid in user_ids:
            if uid and str(uid) in user_lookup:
                u = user_lookup[str(uid)]
                owners_map[str(uid)] = {
                    "id": str(u.id),
                    "name": u.full_name,
                    "avatar": u.avatar
                }
        
        owners_list = list(owners_map.values())
        
        # Enrich transactions with user info
        enriched_orders = []
        for o in orders:
            u_info = None
            if o.user_id and str(o.user_id) in user_lookup:
                u = user_lookup[str(o.user_id)]
                u_info = {"id": str(u.id), "name": u.full_name, "avatar": u.avatar}
            elif o.holding_id:
                # Fallback: try to find user via holding if not on order
                # This might be expensive loop-in-loop, but dataset is small per scheme
                parent_holding = next((h for h in holdings if h.id == o.holding_id), None)
                if parent_holding and parent_holding.user_id:
                     u = user_lookup.get(str(parent_holding.user_id))
                     if u:
                         u_info = {"id": str(u.id), "name": u.full_name, "avatar": u.avatar}

            enriched_orders.append({
                "id": o.id,
                "type": MutualFundService._normalize_txn_type(o.type),
                "amount": float(o.amount),
                "units": float(o.units),
                "nav": float(o.nav),
                "date": o.order_date.strftime("%Y-%m-%d"),
                "status": o.status,
                "user": u_info
            })

        user_name = "Multiple Members" if len(user_ids) > 1 else None
        user_avatar = None
        if len(user_ids) == 1:
            uid = list(user_ids)[0]
            if uid and str(uid) in user_lookup:
                u = user_lookup[str(uid)]
                user_name = u.full_name
                user_avatar = u.avatar

        scheme_response = {
            "id": f"group-{scheme_code}", 
            "scheme_name": meta.scheme_name if meta else "Unknown Fund",
            "scheme_code": scheme_code,
            "isin_growth": meta.isin_growth if meta else None,
            "isin_reinvest": meta.isin_reinvest if meta else None,
            "fund_house": meta.fund_house if meta else None,
            "folio_number": f"{len(folio_numbers)} Folios" if len(folio_numbers) > 1 else (list(folio_numbers)[0] if folio_numbers else "N/A"),
            "category": meta.category if meta else "Other",
            "user_id": list(user_ids)[0] if len(user_ids) == 1 else "multi",
            "user_name": user_name or "Unassigned",
            "user_avatar": user_avatar,
            "units": total_units,
            "average_price": avg_price,
            "current_value": total_current_value,
            "invested_value": total_invested_value,
            "profit_loss": profit_loss,
            "last_nav": Decimal(str(holdings[0].last_nav or 0)) if holdings else Decimal('0.0'),
            "last_updated_at": holdings[0].last_updated_at.strftime("%Y-%m-%d") if holdings and holdings[0].last_updated_at else None,
            "xirr": xirr_value,
            "transactions": enriched_orders,
            "nav_history": nav_history,
            "is_aggregate": True,
            "owners": owners_list
        }

        # --- Aggregate Benchmark Logic ---
        benchmarks_list = []
        if meta and meta.category:
            bm = BenchmarkService.get_or_create_benchmark_mapping(db, meta.category)
            if bm:
                style = {
                    "color": bm.styling_color,
                    "style": bm.styling_style,
                    "dashArray": bm.styling_dash_array,
                }
                try:
                    fund_start_date = None
                    if nav_history:
                        fund_start_date = datetime.strptime(nav_history[0]['date'], "%Y-%m-%d").date()
                    
                    bm_history = NAVService.get_nav_history(bm.benchmark_symbol, fund_start_date or start_date, today)
                    
                    if not bm_history:
                        threading.Thread(target=NAVService.sync_nav_history, args=(bm.benchmark_symbol,)).start()
                    else:
                        benchmarks_list.append({
                            "label": bm.benchmark_label,
                            "symbol": bm.benchmark_symbol,
                            "styling": style,
                            "history": bm_history
                        })
                except Exception: 
                    pass

        scheme_response["benchmarks"] = benchmarks_list
        return scheme_response

    @staticmethod
    def get_scheme_info(db: Session, tenant_id: str, scheme_code: str):
        """Fetch general scheme information without requiring a holding."""
        # 1. Fetch Metadata from DB
        meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == scheme_code).first()
        
        # 2. On-the-fly NAV History via NAVService (No DB Caching)
        # This adheres to the requirement of not caching data for funds the user doesn't own.
        live_data = NAVService.fetch_live_nav_history(scheme_code, days=365)
        nav_history = live_data.get("history", [])
        mf_meta = live_data.get("meta", {})
        
        # Resolve Names/AMC from DB or Live Meta as fallback
        scheme_name = meta.scheme_name if meta else mf_meta.get("scheme_name", "Unknown Fund")
        fund_house = meta.fund_house if meta else mf_meta.get("fund_house", "Unknown AMC")
        category = meta.category if meta else mf_meta.get("scheme_type", "Mutual Fund")
        
        # Latest NAV derivation (Rule 64 compliance)
        latest_nav = Decimal("0.0")
        if nav_history:
            latest_nav = Decimal(str(nav_history[-1]['value']))
        elif meta and meta.last_nav:
            latest_nav = Decimal(str(meta.last_nav))

        # Hash-based mock metrics for polished Explore UI
        code_hash = sum(ord(c) for c in str(scheme_code))
        risk_level = ['Low', 'Moderate', 'High', 'Very High'][code_hash % 4]
        aum = f"{(1000 + (code_hash % 9000)):,} Cr"
        trending = (code_hash % 7 == 0)
        rating = 3 + (code_hash % 3)
        returns_3y = Decimal(f"{12.0 + (code_hash % 8) + ((code_hash % 100) / 100.0):.2f}")

        return {
            "id": f"explore_{scheme_code}", 
            "scheme_name": scheme_name,
            "scheme_code": scheme_code,
            "isin_growth": meta.isin_growth if meta else None,
            "isin_reinvest": meta.isin_reinvest if meta else None,
            "fund_house": fund_house,
            "category": category,
            "risk_level": risk_level,
            "aum": aum,
            "trending": trending,
            "rating": rating,
            "returns_3y": returns_3y,
            "last_nav": latest_nav,
            "nav_history": nav_history,
            "is_aggregate": False
        }


    @staticmethod
    def update_holding(db: Session, tenant_id: str, holding_id: str, data: dict):
        with db_write_lock:
            holding = db.query(MutualFundHolding).filter(
                MutualFundHolding.id == holding_id,
                MutualFundHolding.tenant_id == tenant_id
            ).first()
            
            if not holding:
                # Fallback: if holding_id is numeric, attempt scheme-level update for all holdings in this scheme
                if holding_id.isdigit():
                    holdings = db.query(MutualFundHolding).filter(
                        MutualFundHolding.scheme_code == holding_id,
                        MutualFundHolding.tenant_id == tenant_id
                    ).all()
                    if not holdings: return None
                    
                    for h in holdings:
                        if "user_id" in data:
                            h.user_id = data["user_id"]
                            db.query(MutualFundOrder).filter(
                                MutualFundOrder.holding_id == h.id
                            ).update({"user_id": data["user_id"]})
                        if "goal_id" in data:
                            h.goal_id = data["goal_id"]
                    
                    db.flush()
                    MutualFundService._safe_commit(db)
                    return holdings[0] # Return first one as representative
                return None
                
            if "user_id" in data:
                holding.user_id = data["user_id"]
                # Also update all orders for this holding to reflect the user change
                db.query(MutualFundOrder).filter(
                    MutualFundOrder.holding_id == holding.id,
                    MutualFundOrder.tenant_id == tenant_id
                ).update({"user_id": data["user_id"]})
            
            if "goal_id" in data:
                holding.goal_id = data["goal_id"]

            db.flush()
            MutualFundService._safe_commit(db)
            return holding


    @staticmethod
    def get_portfolio_analytics(db: Session, tenant_id: str, user_id: Optional[str] = None):
        """
        Calculate portfolio analytics: allocation, top performers, XIRR
        """
        
        # Get portfolio data
        query = db.query(MutualFundHolding).filter(
            MutualFundHolding.tenant_id == tenant_id,
            MutualFundHolding.is_deleted == False
        )
        if user_id:
            query = query.filter(MutualFundHolding.user_id == user_id)
        holdings = query.all()
        
        if not holdings:
            return {
                "asset_allocation": {"equity": 0, "debt": 0, "hybrid": 0, "other": 0},
                "category_allocation": {},
                "top_gainers": [],
                "top_losers": [],
                "xirr": 0,
                "total_invested": 0,
                "current_value": 0
            }
        
        # Calculate asset allocation
        allocation = {
            "equity": Decimal("0.0"),
            "debt": Decimal("0.0"),
            "hybrid": Decimal("0.0"),
            "other": Decimal("0.0")
        }
        category_allocation = {}
        total_value = Decimal("0.0")
        

        # Bulk fetch metas for all holdings to avoid N+1 queries
        scheme_codes = list(set(h.scheme_code for h in holdings))
        metas = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code.in_(scheme_codes)).all()
        meta_map = {m.scheme_code: m for m in metas}

        # 1. Standard aggregations (Allocation + Total Value)
        for h in holdings:
            meta = meta_map.get(h.scheme_code)
            raw_category = meta.category if meta else "Other"
            asset_type = categorize_fund(raw_category)
            current_val = Decimal(str(h.current_value or 0.0))
            
            allocation[asset_type] += current_val
            
            # Category-wise (Sector proxy)
            if raw_category not in category_allocation:
                category_allocation[raw_category] = Decimal("0.0")
            category_allocation[raw_category] += current_val
            
            total_value += current_val
        
        # 2. Portfolio Sparkline (Historical Trend)
        sparkline = []
        try:
            cutoff = timezone.utcnow().date() - timedelta(days=30)
            cached_points = (
                db.query(PortfolioTimelineCache)
                .filter(
                    PortfolioTimelineCache.tenant_id == tenant_id,
                    PortfolioTimelineCache.snapshot_date >= cutoff,
                )
                .order_by(PortfolioTimelineCache.snapshot_date.asc())
                .all()
            )
            if cached_points:
                sparkline = [float(p.portfolio_value) for p in cached_points]
                # Append today's real-time value to sparkline for UI completeness
                sparkline.append(float(total_value))
        except Exception:
            pass

        # 3. Robust Day Change (Latest NAV vs Previous NAV for each holding)
        # This handles the case where Today vs Yesterday in cache might be 0 due to 
        # NAV only updating at midnight.
        day_change = Decimal("0.0")
        day_change_percent = Decimal("0.0")
        scheme_deltas = {} # Cache deltas to avoid N+1 queries if multiple holdings/folios exist for same scheme
        
        for h in holdings:
            s_code = h.scheme_code
            if s_code not in scheme_deltas:
                try:
                    # Fetches delta between N1 (latest) and N0 (previous)
                    delta_info = NAVService.get_latest_nav_delta(s_code)
                    scheme_deltas[s_code] = delta_info.get("delta", Decimal("0.0"))
                except Exception:
                    scheme_deltas[s_code] = Decimal("0.0")
            
            units = Decimal(str(h.units or 0.0))
            day_change += (units * scheme_deltas[s_code])
        
        if total_value > 0:
            # We calculate percentage based on the "previous" value (Current - Change)
            prev_total_value = total_value - day_change
            if prev_total_value > 0:
                day_change_percent = (day_change / prev_total_value) * 100
            else:
                day_change_percent = Decimal("0.0")

        # Convert allocation to percentages
        if total_value > 0:
            allocation = {k: round(float((v / total_value) * 100), 2) for k, v in allocation.items()}
            category_allocation = {k: round(float((v / total_value) * 100), 2) for k, v in category_allocation.items()}
        
        # Get portfolio with P/L for top performers
        portfolio_data = MutualFundService.get_portfolio(db, tenant_id, user_id)
        
        # Calculate P/L percentage for sorting
        for item in portfolio_data:
            invested = Decimal(str(item.get('invested_value', 0)))
            if invested > 0:
                item['pl_percent'] = round(float((Decimal(str(item['profit_loss'])) / invested) * 100), 2)
            else:
                item['pl_percent'] = 0
        
        # Sort by P/L percentage
        sorted_by_pl = sorted(portfolio_data, key=lambda x: x['pl_percent'], reverse=True)
        
        top_gainers = sorted_by_pl[:5]
        top_losers = list(reversed(sorted_by_pl[-5:]))
        
        # Calculate XIRR
        # Get all transactions for EXISTING holdings only (Same as timeline)
        h_q = db.query(MutualFundHolding.id).filter(MutualFundHolding.tenant_id == tenant_id)
        if user_id:
            h_q = h_q.filter(MutualFundHolding.user_id == user_id)
        active_holding_ids = [h.id for h in h_q.all()]
        
        o_q = db.query(MutualFundOrder).filter(
            MutualFundOrder.tenant_id == tenant_id,
            MutualFundOrder.holding_id.in_(active_holding_ids),
            MutualFundOrder.is_deleted == False
        )
        if user_id:
            o_q = o_q.filter(MutualFundOrder.user_id == user_id)
        
        orders = o_q.all()
        
        xirr_value = None
        total_invested = Decimal("0.0")
        
        if orders and len(orders) > 0:
            cash_flows = []
            
            # Check if we have history or just summary balances
            non_summary_count = sum(1 for o in orders if "SUMMARY BALANCE" not in str(o.type).upper())
            
            for order in orders:
                o_type = str(order.type).upper().strip()
                
                # Rule: Skip Reinvestments (They are not fresh capital flows)
                if any(kw in o_type for kw in MutualFundService.MF_REINVESTMENT_KEYWORDS):
                    continue
                
                # Rule: Skip Summary Balances if we have real history (prevent double counting)
                if "SUMMARY BALANCE" in o_type and non_summary_count > 0:
                    continue

                # Rule: Skip internal transfers for Portfolio-wide XIRR
                # (They net out anyway if both sides exist, but this is safer for partial data)
                if any(kw in o_type for kw in MutualFundService.MF_INTERNAL_KEYWORDS):
                    continue

                # Use units * nav if amount is 0 (fallback for older imports)
                amount = Decimal(str(order.amount))
                if amount <= 0:
                    amount = Decimal(str(order.units)) * Decimal(str(order.nav))
                
                # Convert order_date to date if it's datetime
                order_date = order.order_date.date() if hasattr(order.order_date, 'date') else order.order_date
                
                # Regex patterns for word-boundary matching
                withdrawal_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_WITHDRAWAL_KEYWORDS) + r')\b'
                investment_pattern = r'\b(' + '|'.join(re.escape(k) for k in MutualFundService.MF_INVESTMENT_KEYWORDS) + r')\b'
                
                is_withdrawal = bool(re.search(withdrawal_pattern, o_type))
                is_investment = not is_withdrawal and bool(re.search(investment_pattern, o_type))

                if is_investment:
                    cash_flows.append((order_date, -float(amount)))  # Outflow is negative
                    total_invested += amount
                elif is_withdrawal:
                    cash_flows.append((order_date, float(amount)))  # Inflow is positive
            
            # Add current value as final inflow at today's date
            if total_value > 0:
                cash_flows.append((timezone.utcnow().date(), float(total_value)))
            
            try:
                # Need at least one negative (outflow) and one positive (inflow) for XIRR
                sum_out = sum(cf[1] for cf in cash_flows if cf[1] < 0)
                if len(cash_flows) >= 2 and abs(sum_out) > 0.01:
                    xirr_decimal = xirr(cash_flows)
                    # Sanitize result (Newton-Raphson can return extreme values if it fails to converge)
                    if xirr_decimal is not None and -0.99 < xirr_decimal < 10:
                        xirr_value = round(xirr_decimal * 100, 2)
                    else:
                        xirr_value = None
            except Exception:
                xirr_value = None
        
        return {
            "asset_allocation": allocation,
            "category_allocation": category_allocation,
            "top_gainers": top_gainers,
            "top_losers": top_losers,
            "xirr": xirr_value,
            "total_invested": round(float(total_invested), 2),
            "current_value": round(float(total_value), 2),
            "profit_loss": round(float(total_value - total_invested), 2),
            "profit_loss_percent": round(float(((total_value - total_invested) / total_invested * 100) if total_invested > 0 else 0), 2),
            "sparkline": sparkline,
            "day_change": round(float(day_change), 2),
            "day_change_percent": round(float(day_change_percent), 2),
            "active_schemes_count": len(holdings)
        }
    
    @staticmethod
    def clear_timeline_cache(db: Session, tenant_id: str, from_date=None):
        """
        Clear timeline cache for a tenant.
        Call this when transactions are added/deleted to invalidate cache.
        
        Args:
            tenant_id: Tenant ID
            from_date: Clear cache from this date onwards (defaults to all)
        """
        query = db.query(PortfolioTimelineCache).filter(
            PortfolioTimelineCache.tenant_id == tenant_id
        )
        
        if from_date:
            query = query.filter(PortfolioTimelineCache.snapshot_date >= from_date)
        
        deleted_count = query.delete()
        db.commit()
        return deleted_count
    
    @staticmethod
    def get_performance_timeline(db: Session, tenant_id: str, period: str = "1y", granularity: str = "1w", 
                                 user_id: Optional[str] = None, scheme_code: Optional[str] = None, 
                                 holding_id: Optional[str] = None):
        """
        Calculate portfolio value over time with smart caching.
        
        Returns timeline data with portfolio value and invested amount at weekly intervals.
        """
        
        # Get all transactions for EXISTING holdings only
        # This prevents orphaned orders from deleted holdings from inflating the timeline
        holdings_query = db.query(MutualFundHolding.id).filter(
            MutualFundHolding.tenant_id == tenant_id,
            MutualFundHolding.is_deleted == False
        )
        if user_id:
            holdings_query = holdings_query.filter(MutualFundHolding.user_id == user_id)
        if scheme_code:
            holdings_query = holdings_query.filter(MutualFundHolding.scheme_code == scheme_code)
        if holding_id:
            holdings_query = holdings_query.filter(MutualFundHolding.id == holding_id)
            
        holdings = holdings_query.all()
        active_holding_ids = [h.id for h in holdings]
        
        orders_query = db.query(MutualFundOrder).filter(
            MutualFundOrder.tenant_id == tenant_id,
            MutualFundOrder.holding_id.in_(active_holding_ids),
            MutualFundOrder.is_deleted == False
        )
        if user_id:
            orders_query = orders_query.filter(MutualFundOrder.user_id == user_id)
        
        orders = orders_query.order_by(MutualFundOrder.order_date.asc()).all()
        
        if not orders:
            return {
                "timeline": [],
                "period": period,
                "total_return_percent": 0
            }
        
        # Variables for hash calculation and state tracking
        unique_schemes = list(set(str(o.scheme_code) for o in orders))
        latest_txn_update = max(o.created_at for o in orders) if orders else timezone.utcnow().date()
        
        hash_input = ",".join(unique_schemes)
        # Portfolio hash with version suffix (v9) for robust classification fix
        hash_input += f"|count:{len(orders)}|last_upd:{latest_txn_update.isoformat()}|v:9"
        
        if user_id:
            hash_input += f"|user:{user_id}"
        if scheme_code:
            hash_input += f"|scheme:{scheme_code}"
        if holding_id:
            hash_input += f"|holding:{holding_id}"
            
        portfolio_hash = hashlib.md5(hash_input.encode()).hexdigest()
        
        # Determine date range and granularity
        end_date = timezone.utcnow().date() - timedelta(days=1)
        start_date = calculate_start_date(period, orders[0].order_date)
        
        # Ensure at least 2 points for sparklines/trends even for brand new portfolios
        if start_date >= end_date:
            start_date = end_date - timedelta(days=1)
        
        # Snapshot interval based on granularity
        if granularity == "1d":
            snapshot_days = 1
        elif granularity == "1m":
            snapshot_days = 30 # Approximation
        else:
            snapshot_days = 7  # Default to weekly
            # Optimization: Don't force shift the first point to Monday! 
            # This ensures the chart starts exactly on the first purchase date.
            pass
        
        # Try to fetch cached snapshots
        cached_snapshots = db.query(PortfolioTimelineCache).filter(
            PortfolioTimelineCache.tenant_id == tenant_id,
            PortfolioTimelineCache.portfolio_hash == portfolio_hash,
            PortfolioTimelineCache.snapshot_date >= start_date,
            PortfolioTimelineCache.snapshot_date < end_date  # Don't cache today
        ).all()
        
        # Convert cached snapshots to dict for easy lookup
        cache_dict = {}
        for snap in cached_snapshots:
            # Self-Healing: Ignore cached entries with 0 value if investment exists (indicates failed NAV fetch previously)
            if snap.portfolio_value == 0 and snap.invested_value > 0:
                continue
            
            import json
            benchmarks_data = {}
            if snap.benchmarks_json:
                try:
                    benchmarks_data = json.loads(snap.benchmarks_json)
                except Exception:
                    # Silent fallback for non-critical failures (consistent with repo pattern)
                    pass
            
            # Legacy fallback
            if not benchmarks_data and snap.benchmark_value:
                benchmarks_data = {"120716": float(snap.benchmark_value)}
                
            cache_dict[snap.snapshot_date.date()] = {
                "date": snap.snapshot_date.date().isoformat(),
                "value": float(snap.portfolio_value),
                "invested": float(snap.invested_value),
                "benchmarks": benchmarks_data
            }
        
        # Identify benchmarks to track
        # Always track Nifty 50
        primary_bm_code = "120716"
        tracked_benchmarks = {
            primary_bm_code: {
                "label": "Nifty 50 Index",
                "styling": {"color": "#10B981", "style": "solid", "dashArray": ""}
            }
        }
        
        # Get category benchmarks for all unique schemes in this timeline
        scheme_metas = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code.in_(unique_schemes)).all()
        scheme_to_bm = {} # {scheme_code: bm_code}
        
        for m in scheme_metas:
            bm = BenchmarkService.get_or_create_benchmark_mapping(db, m.category)
            if bm:
                scheme_to_bm[m.scheme_code] = bm.benchmark_symbol
                if bm.benchmark_symbol not in tracked_benchmarks:
                    tracked_benchmarks[bm.benchmark_symbol] = {
                        "label": bm.benchmark_label,
                        "styling": {
                            "color": bm.styling_color,
                            "style": bm.styling_style,
                            "dashArray": bm.styling_dash_array
                        }
                    }
        
        # Generate snapshots
        timeline = []
        current_date = start_date
        
        # Linear-time performance variables
        running_holdings = {} # {scheme_code: units}
        running_invested = Decimal('0.0')
        # Multi-benchmark shadow units
        running_bm_units = {code: Decimal('0.0') for code in tracked_benchmarks.keys()}
        order_idx = 0
        
        # Pre-populate bulk_nav_data from local cache
        bulk_nav_data = {}
        all_involved_schemes = unique_schemes + list(tracked_benchmarks.keys())
        
        for sc in all_involved_schemes:
            # Fetch from cache; synchronizing is done in background from router
            hist = NAVService.get_nav_history(sc, start_date - timedelta(days=10), end_date)
            bulk_nav_data[sc] = {h["date"]: h["value"] for h in hist}

        def find_closest_nav(nav_map, target_date):
            if not nav_map: return Decimal('0.0')
            target_str = target_date.isoformat() # Using ISO for consistency
            if target_str in nav_map: return nav_map[target_str]
            # Look back up to 10 days for closest available NAV (holidays/weekends)
            for i in range(1, 10):
                prev_date = target_date - timedelta(days=i)
                prev_str = prev_date.isoformat()
                if prev_str in nav_map: return nav_map[prev_str]
            # Fallback to the first available NAV in map
            return next(iter(nav_map.values())) if nav_map else Decimal('0.0')
        
        while current_date <= end_date:
            # IMPORTANT: Advance transaction state
            while order_idx < len(orders):
                o = orders[order_idx]
                o_date = o.order_date.date() if hasattr(o.order_date, 'date') else o.order_date
                if o_date <= current_date:
                    s_code = str(o.scheme_code)
                    amt = float(o.amount)
                    if amt <= 0: amt = float(o.units) * float(o.nav)
                    
                    o_type = str(o.type).upper().strip()
                    is_withdrawal = any(kw in o_type for kw in ["SELL", "CREDIT", "REDEMP", "PAYOUT", "OUT", "SWITCH-OUT", "STP-OUT", "STP - OUT", "SWITCH - OUT"])
                    is_investment = not is_withdrawal and any(kw in o_type for kw in ["BUY", "DEBIT", "SIP", "TOPUP", "PURCHASE", "INVEST", "REINV", "SWITCH-IN", "STP-IN", "STP - IN", "SWITCH - IN", "ADDITIONAL"])
                    
                    if is_investment:
                        running_holdings[s_code] = running_holdings.get(s_code, Decimal('0.0')) + Decimal(str(o.units))
                        running_invested += Decimal(str(amt))
                    elif is_withdrawal:
                        running_holdings[s_code] = running_holdings.get(s_code, Decimal('0.0')) - Decimal(str(o.units))
                        running_invested -= Decimal(str(amt))
                        
                    # Accumulate ALL tracked benchmarks Shadow Units
                    for bm_code in tracked_benchmarks.keys():
                        try:
                            hist_bm_nav = find_closest_nav(bulk_nav_data.get(bm_code, {}), o_date)
                            if hist_bm_nav > 0:
                                if is_investment: 
                                    running_bm_units[bm_code] += (Decimal(str(amt)) / hist_bm_nav)
                                elif is_withdrawal: 
                                    running_bm_units[bm_code] -= (Decimal(str(amt)) / hist_bm_nav)
                        except Exception: 
                            # Skip benchmark shadow unit updates if NAV lookups fail (e.g. holiday or missing mapping)
                            pass
                    order_idx += 1
                else:
                    break

            if current_date in cache_dict and current_date < end_date:
                timeline.append(cache_dict[current_date])
            else:
                # Calculate portfolio value
                portfolio_value = Decimal('0.0')
                for s_code, units in running_holdings.items():
                    if units > Decimal('1e-6'):
                        nav = find_closest_nav(bulk_nav_data.get(s_code, {}), current_date)
                        portfolio_value += units * nav
                
                # Multi-Benchmark Values
                benchmarks_values = {}
                for bm_code in tracked_benchmarks.keys():
                    try:
                        bm_nav = find_closest_nav(bulk_nav_data.get(bm_code, {}), current_date)
                        benchmarks_values[bm_code] = round(max(0, running_bm_units[bm_code] * bm_nav), 2)
                    except Exception: 
                        # Fallback to zero if benchmark value cannot be computed for this snapshot
                        benchmarks_values[bm_code] = 0.0

                snapshot_data = {
                    "date": current_date.isoformat(),
                    "value": round(portfolio_value, 2),
                    "invested": round(running_invested, 2),
                    "benchmarks": benchmarks_values
                }
                timeline.append(snapshot_data)
                
                # Save to cache if not today
                if current_date < end_date:
                    if not (portfolio_value == 0 and running_invested > 0):
                        from datetime import datetime as dt
                        import json
                        
                        primary_bm_val = benchmarks_values.get(primary_bm_code, 0.0)
                        
                        cache_entry = PortfolioTimelineCache(
                            tenant_id=tenant_id,
                            snapshot_date=dt.combine(current_date, dt.min.time()),
                            portfolio_hash=portfolio_hash,
                            portfolio_value=round(portfolio_value, 2),
                            invested_value=round(running_invested, 2),
                            benchmark_value=primary_bm_val, # For backward compatibility
                            benchmarks_json=json.dumps({k: float(v) for k, v in benchmarks_values.items()})
                        )
                        db.add(cache_entry)
            
            if granularity == "1m":
                current_date = add_months(current_date, 1)
            else:
                current_date = current_date + timedelta(days=snapshot_days)
            
            if current_date > end_date:
                break
        
        # Calculate total return
        total_return_percent = 0
        if timeline and timeline[-1]["invested"] > 0:
            total_return_percent = (
                (timeline[-1]["value"] - timeline[-1]["invested"]) / 
                timeline[-1]["invested"] * 100
            )
        
        # Commit cache
        try:
            with db_write_lock:
                MutualFundService._safe_commit(db)
        except Exception as e:
            # Rollback if cache persistence fails to ensure session integrity
            logger.error(f"Failed to persist performance timeline cache: {e}")
            db.rollback()
        
        # Consolidate benchmark timelines
        benchmarks_response = {} # {bm_label: [{date, value}, ...]}
        for bm_code, info in tracked_benchmarks.items():
            bm_label = info["label"]
            style = info["styling"]
            
            benchmarks_response[bm_label] = {
                "label": bm_label,
                "symbol": bm_code,
                "styling": style,
                "data": []
            }
            
            for p in timeline:
                if "benchmarks" in p and bm_code in p["benchmarks"]:
                    benchmarks_response[bm_label]["data"].append({
                        "date": p["date"],
                        "value": p["benchmarks"][bm_code]
                    })
        
        return {
            "timeline": timeline,
            "benchmarks": list(benchmarks_response.values()),
            "period": period,
            "granularity": granularity,
            "total_return_percent": round(total_return_percent, 2)
        }

    # --------------------------------------------------------------------------
    # Management & Correction Logic (Modular Extensions)
    # --------------------------------------------------------------------------

    @staticmethod
    def bulk_delete_transactions(db: Session, tenant_id: str, transaction_ids: list[str]):
        """
        Soft-delete multiple transactions and trigger holding recalculation.
        """
        with db_write_lock:
            # 1. Fetch relevant orders to find affected holdings
            orders = db.query(MutualFundOrder).filter(
                MutualFundOrder.id.in_(transaction_ids),
                MutualFundOrder.tenant_id == tenant_id
            ).all()

            if not orders:
                return 0

            affected_tenant_ids = {o.tenant_id for o in orders}
            affected_user_ids = {o.user_id for o in orders if o.user_id}

            # 2. Perform soft-delete
            now = timezone.utcnow()
            for order in orders:
                order.is_deleted = True
                order.deleted_at = now

            MutualFundService._safe_commit(db)

            # 3. Trigger recalculation for all affected users/tenants
            for t_id in affected_tenant_ids:
                if affected_user_ids:
                    for u_id in affected_user_ids:
                        MutualFundService._recalculate_holdings_logic(db, t_id, u_id)
                else:
                    MutualFundService._recalculate_holdings_logic(db, t_id)

            return len(orders)

    @staticmethod
    def update_transaction(db: Session, tenant_id: str, transaction_id: str, data: dict):
        """
        Update a historical transaction and trigger holding recalculation.
        """
        with db_write_lock:
            order = db.query(MutualFundOrder).filter(
                MutualFundOrder.id == transaction_id,
                MutualFundOrder.tenant_id == tenant_id,
                MutualFundOrder.is_deleted == False
            ).first()

            if not order:
                raise Exception("Transaction not found")

            # Update fields
            if "date" in data:
                order.order_date = datetime.fromisoformat(data["date"].replace('Z', '+00:00'))
            if "units" in data:
                order.units = Decimal(str(data["units"]))
            if "nav" in data:
                order.nav = Decimal(str(data["nav"]))
            if "amount" in data:
                order.amount = Decimal(str(data["amount"]))
            if "type" in data:
                order.type = MutualFundService._normalize_txn_type(data["type"])

            MutualFundService._safe_commit(db)

            # Recalculate holding impact
            MutualFundService._recalculate_holdings_logic(db, tenant_id, order.user_id)
            return order
    
