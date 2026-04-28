from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from .core import CoreAnalytics
from .spending import SpendingAnalytics
from .history import HistoryAnalytics
from .investments import InvestmentAnalytics
from .credit import CreditAnalytics

class AnalyticsService:
    @staticmethod
    def get_summary_metrics(db: Session, tenant_id: str, **kwargs):
        return CoreAnalytics.get_summary_metrics(db, tenant_id, **kwargs)

    @staticmethod
    def get_mobile_summary_metrics(db: Session, tenant_id: str, **kwargs):
        return CoreAnalytics.get_mobile_summary_metrics(db, tenant_id, **kwargs)

    @staticmethod
    def get_detailed_analytics(db: Session, tenant_id: str, **kwargs):
        return SpendingAnalytics.get_detailed_analytics(db, tenant_id, **kwargs)

    @staticmethod
    def get_spending_trend(db: Session, tenant_id: str, **kwargs):
        return SpendingAnalytics.get_spending_trend(db, tenant_id, **kwargs)

    @staticmethod
    def get_merchant_breakdown(db: Session, tenant_id: str, **kwargs):
        return SpendingAnalytics.get_merchant_breakdown(db, tenant_id, **kwargs)

    @staticmethod
    def get_net_worth_timeline(db: Session, tenant_id: str, **kwargs):
        return HistoryAnalytics.get_net_worth_timeline(db, tenant_id, **kwargs)

    @staticmethod
    def get_budget_history(db: Session, tenant_id: str, **kwargs):
        return HistoryAnalytics.get_budget_history(db, tenant_id, **kwargs)

    @staticmethod
    def get_heatmap_data(db: Session, tenant_id: str, **kwargs):
        return HistoryAnalytics.get_heatmap_data(db, tenant_id, **kwargs)

    @staticmethod
    def get_family_wealth(db: Session, tenant_id: str, **kwargs):
        return InvestmentAnalytics.get_family_wealth(db, tenant_id, **kwargs)
        
    @staticmethod
    def get_consolidated_dashboard(db: Session, tenant_id: str, current_user, **kwargs):
        return CoreAnalytics.get_consolidated_dashboard(db, tenant_id, current_user, **kwargs)

    @staticmethod
    def get_mobile_summary_lightweight(db: Session, tenant_id: str, **kwargs):
        return CoreAnalytics.get_mobile_summary_lightweight(db, tenant_id, **kwargs)

    @staticmethod
    def get_spending_forecast(db: Session, tenant_id: str, **kwargs):
        return SpendingAnalytics.get_spending_forecast(db, tenant_id, **kwargs)

    @staticmethod
    def get_balance_forecast(db: Session, tenant_id: str, **kwargs):
        return CoreAnalytics.get_balance_forecast(db, tenant_id, **kwargs)

    @staticmethod
    def get_mobile_dashboard_trends(db: Session, tenant_id: str, *args, **kwargs):
        return SpendingAnalytics.get_mobile_dashboard_trends(db, tenant_id, *args, **kwargs)

    @staticmethod
    def get_mobile_dashboard_categories(db: Session, tenant_id: str, *args, **kwargs):
        return SpendingAnalytics.get_mobile_dashboard_categories(db, tenant_id, *args, **kwargs)

    @staticmethod
    def get_calendar_heatmap(db: Session, tenant_id: str, **kwargs):
        return HistoryAnalytics.get_calendar_heatmap(db, tenant_id, **kwargs)

    @staticmethod
    def get_daily_spending_history(db: Session, tenant_id: str, **kwargs):
        return HistoryAnalytics.get_daily_spending_history(db, tenant_id, **kwargs)

    @staticmethod
    def get_credit_intelligence(db: Session, tenant_id: str, **kwargs):
        # We need to get accounts to analyze them
        from backend.app.modules.finance.services.account_service import AccountService
        accounts = AccountService.get_accounts(db, tenant_id, return_as_dict=False, **kwargs)
        return CreditAnalytics.get_credit_intelligence(db, tenant_id, accounts)
