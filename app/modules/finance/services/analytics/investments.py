from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from backend.app.modules.finance import models
from backend.app.core import timezone

class InvestmentAnalytics:
    @staticmethod
    def get_family_wealth(db: Session, tenant_id: str):
        # Get all users in the tenant
        from backend.app.modules.auth.models import User
        family_members = db.query(User).filter(User.tenant_id == tenant_id).all()
        
        # Get all accounts in the tenant
        accounts = db.query(models.Account).filter(
            models.Account.tenant_id == tenant_id,
            models.Account.is_deleted == False
        ).all()
        
        # Calculate breakdown
        member_wealth = []
        shared_wealth = {
            "net_worth": Decimal(0),
            "assets": Decimal(0),
            "liabilities": Decimal(0),
            "account_count": 0
        }
        
        total_assets = Decimal(0)
        total_liabilities = Decimal(0)
        
        for user in family_members:
            user_assets = Decimal(0)
            user_liabilities = Decimal(0)
            user_accounts = [a for a in accounts if a.owner_id == str(user.id)]
            
            for acc in user_accounts:
                bal = Decimal(acc.balance or 0)
                if acc.type in ['CREDIT_CARD', 'LOAN']:
                    user_liabilities += bal
                else:
                    user_assets += bal
            
            member_wealth.append({
                "user_id": str(user.id),
                "name": user.full_name or user.email.split('@')[0],
                "role": user.role,
                "net_worth": user_assets - user_liabilities,
                "assets": user_assets,
                "liabilities": user_liabilities,
                "account_count": len(user_accounts)
            })
            
            total_assets += user_assets
            total_liabilities += user_liabilities
            
        # Shared accounts (owner_id is None)
        shared_accounts = [a for a in accounts if a.owner_id is None]
        for acc in shared_accounts:
            bal = Decimal(acc.balance or 0)
            if acc.type in ['CREDIT_CARD', 'LOAN']:
                shared_wealth["liabilities"] += bal
            else:
                shared_wealth["assets"] += bal
                
        shared_wealth["net_worth"] = shared_wealth["assets"] - shared_wealth["liabilities"]
        shared_wealth["account_count"] = len(shared_accounts)
        
        total_assets += shared_wealth["assets"]
        total_liabilities += shared_wealth["liabilities"]
        
        return {
            "total_net_worth": float(total_assets - total_liabilities),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "members": [
                {**m, "net_worth": float(m["net_worth"]), "assets": float(m["assets"]), "liabilities": float(m["liabilities"])}
                for m in member_wealth
            ],
            "shared": {**shared_wealth, "net_worth": float(shared_wealth["net_worth"]), "assets": float(shared_wealth["assets"]), "liabilities": float(shared_wealth["liabilities"])}
        }

    @staticmethod
    def get_investment_summary(db: Session, tenant_id: str, start_date: datetime, end_date: datetime, user_id: str = None):
        # Summary of investments for a specific period
        query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.is_deleted == False,
                models.Transaction.date >= start_date,
                models.Transaction.date <= end_date,
                models.Category.type == 'investment',
                models.Transaction.exclude_from_reports == False
            )
        if user_id:
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(
                             models.Account.is_deleted == False,
                             or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
                         )
                         
        total = abs(Decimal(query.scalar() or 0))
        return total
