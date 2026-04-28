import logging
import uuid
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.core.database import db_write_lock
from backend.app.modules.finance.models import MutualFundBenchmark, MutualFundBenchmarkRule

logger = logging.getLogger(__name__)

class BenchmarkService:
    @staticmethod
    def get_or_create_benchmark_mapping(db: Session, category: str) -> MutualFundBenchmark:
        """
        Finds a benchmark for a category, or creates one based on database-driven rules.
        """
        with db_write_lock:
            if not category:
                category = "Unknown"

            # 1. Check existing mapping
            mapping = db.query(MutualFundBenchmark).filter(MutualFundBenchmark.category == category).first()
            if mapping:
                return mapping

            # 2. Rule-based resolution
            rules = db.query(MutualFundBenchmarkRule).order_by(MutualFundBenchmarkRule.priority.asc()).all()
            
            cat_lower = category.lower()
            matched_rule = None
            
            for rule in rules:
                if not rule.keyword or rule.keyword.lower() in cat_lower:
                    matched_rule = rule
                    break
            
            if not matched_rule:
                # Absolute fallback if no rules exist (should not happen after seeding)
                scheme_code = "120716"
                name = "Nifty 50 Index"
                styling = {"color": "#FF9800", "style": "solid", "dashArray": ""}
            else:
                scheme_code = matched_rule.benchmark_symbol
                name = matched_rule.benchmark_label
                styling = {
                    "color": matched_rule.styling_color,
                    "style": matched_rule.styling_style,
                    "dashArray": matched_rule.styling_dash_array
                }

            # 3. Save new mapping
            try:
                new_mapping = MutualFundBenchmark(
                    id=str(uuid.uuid4()),
                    category=category,
                    benchmark_symbol=scheme_code,
                    benchmark_label=name,
                    is_default=(scheme_code == "120716"),
                    styling_color=styling.get("color"),
                    styling_style=styling.get("style", "solid"),
                    styling_dash_array=styling.get("dashArray")
                )
                db.add(new_mapping)
                db.commit()
                db.refresh(new_mapping)
                return new_mapping
            except Exception as e:
                db.rollback()
                # Retry fetch
                mapping = db.query(MutualFundBenchmark).filter(MutualFundBenchmark.category == category).first()
                if mapping:
                    return mapping
                raise e

    @staticmethod
    def get_default_benchmark(db: Session) -> MutualFundBenchmark:
        """Returns the primary benchmark (Nifty 50)"""
        mapping = db.query(MutualFundBenchmark).filter(MutualFundBenchmark.is_default == True).first()
        if not mapping:
            return BenchmarkService.get_or_create_benchmark_mapping(db, "Equity: Large Cap")
        return mapping

    @staticmethod
    def get_all_standard_benchmarks(db: Session) -> List[MutualFundBenchmark]:
        """Returns a list of unique benchmarks defined in rules"""
        # Fetch unique symbols from rules
        rules = db.query(MutualFundBenchmarkRule).order_by(MutualFundBenchmarkRule.priority.asc()).all()
        processed_symbols = set()
        results = []
        
        for rule in rules:
            if rule.benchmark_symbol in processed_symbols:
                continue
            
            # Create a transient benchmark object for the UI (or fetch if exists)
            bm = db.query(MutualFundBenchmark).filter(
                MutualFundBenchmark.benchmark_symbol == rule.benchmark_symbol
            ).first()
            
            if not bm:
                # Synthesize a temporary mapping if it doesn't represent a real category yet
                # but we want it visible in the selection list
                bm = MutualFundBenchmark(
                    benchmark_symbol=rule.benchmark_symbol,
                    benchmark_label=rule.benchmark_label,
                    styling_color=rule.styling_color,
                    styling_style=rule.styling_style,
                    styling_dash_array=rule.styling_dash_array
                )
            results.append(bm)
            processed_symbols.add(rule.benchmark_symbol)
            
        return results

    @staticmethod
    def recalculate_all_mappings(db: Session) -> int:
        """
        Deletes all non-custom mappings and re-resolves them based on current rules.
        """
        with db_write_lock:
            try:
                # Get all current categories
                categories = [r[0] for r in db.query(MutualFundBenchmark.category).all()]
                
                # Clear existing mappings
                db.query(MutualFundBenchmark).delete()
                
                count = 0
                for cat in categories:
                    BenchmarkService.get_or_create_benchmark_mapping(db, cat)
                    count += 1
                
                db.commit()
                return count
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to recalculate benchmark mappings: {e}")
                raise e

    @staticmethod
    def get_all_rules(db: Session) -> List[MutualFundBenchmarkRule]:
        """Fetch all benchmark rules ordered by priority."""
        return db.query(MutualFundBenchmarkRule).order_by(MutualFundBenchmarkRule.priority.asc()).all()

    @staticmethod
    def save_rule(db: Session, payload: dict, rule_id: Optional[str] = None) -> MutualFundBenchmarkRule:
        """Creates or updates a benchmark resolution rule with transactional safety."""
        with db_write_lock:
            try:
                if rule_id:
                    rule = db.query(MutualFundBenchmarkRule).filter(MutualFundBenchmarkRule.id == rule_id).first()
                    if not rule:
                        raise ValueError("Rule not found")
                else:
                    rule = MutualFundBenchmarkRule(id=str(uuid.uuid4()))
                    db.add(rule)
                
                rule.priority = payload.get("priority", 0)
                rule.keyword = payload.get("keyword")
                rule.benchmark_symbol = payload.get("benchmark_symbol")
                rule.benchmark_label = payload.get("benchmark_label")
                rule.styling_color = payload.get("styling_color")
                rule.styling_style = payload.get("styling_style") or "solid"
                rule.styling_dash_array = payload.get("styling_dash_array")
                
                db.commit()
                db.refresh(rule)
                return rule
            except Exception as e:
                db.rollback()
                raise e

    @staticmethod
    def delete_rule(db: Session, rule_id: str):
        """Deletes a rule with transactional safety."""
        with db_write_lock:
            try:
                rule = db.query(MutualFundBenchmarkRule).filter(MutualFundBenchmarkRule.id == rule_id).first()
                if not rule:
                    raise ValueError("Rule not found")
                db.delete(rule)
                db.commit()
            except Exception as e:
                db.rollback()
                raise e
