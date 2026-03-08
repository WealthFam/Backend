import asyncio

from sqlalchemy.orm import Session

from backend.app.core.websockets import manager
from backend.app.modules.notifications.models import Alert
from backend.app.modules.notifications.schemas import AlertSchema

class NotificationService:
    @staticmethod
    def create_alert(db: Session, tenant_id: str, title: str, body: str, user_id: str = None, category: str = "INFO"):
        alert = Alert(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            body=body,
            category=category
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Real-time Broadcast via WebSocket
        try:
            # We use asyncio.create_task or just await if in async context. 
            # Since services are often called from sync code, we might need a helper.
            # However, for now, let's just try to broadcast.
            loop = asyncio.get_event_loop()
            if loop.is_running():
                data = AlertSchema.model_validate(alert).model_dump()
                # Ensure datetime is serializable
                data['created_at'] = data['created_at'].isoformat() if data.get('created_at') else None
                asyncio.create_task(manager.broadcast_to_tenant(tenant_id, {
                    "type": "NOTIFICATION",
                    "payload": data
                }))
        except Exception as e:
            # Don't fail the transaction if broadcast fails
            pass

        return alert

    @staticmethod
    def broadcast_alert(db: Session, tenant_id: str, title: str, body: str, category: str = "INFO"):
        from backend.app.modules.auth.models import User, UserRole
        
        # Find All Adults in Tenant
        recipients = db.query(User).filter(
            User.tenant_id == tenant_id,
            User.role != UserRole.CHILD.value if hasattr(UserRole.CHILD, 'value') else User.role != UserRole.CHILD
        ).all()

        for recipient in recipients:
            NotificationService.create_alert(
                db, 
                tenant_id, 
                title, 
                body, 
                user_id=str(recipient.id), 
                category=category
            )

    @staticmethod
    def notify_transaction(db: Session, tenant_id: str, amount: float, description: str, account_name: str, user_id: str = None):
        from backend.app.modules.auth.models import User

        symbol = "₹"
        abs_amount = abs(amount)
        type_str = "Spent" if amount < 0 else "Received"
        
        spender_name = "Family"
        if user_id:
            spender = db.query(User).filter(User.id == user_id).first()
            if spender:
                spender_name = spender.full_name or spender.email.split('@')[0]

        title = f"💸 {type_str} {symbol}{abs_amount:,.0f}"
        body = f"{description}\nvia {account_name} by {spender_name}"
        
        return NotificationService.broadcast_alert(db, tenant_id, title, body, category="EXPENSE")

    @staticmethod
    def notify_triage(db: Session, tenant_id: str, amount: float, description: str, account_name: str):
        symbol = "₹"
        abs_amount = abs(amount)
        
        title = "📂 Triage Required"
        body = f"Review {symbol}{abs_amount:,.0f} at {description}\nAccount: {account_name}"
        
        return NotificationService.broadcast_alert(db, tenant_id, title, body, category="INFO")

    @staticmethod
    def notify_milestone(db: Session, tenant_id: str, goal_name: str, progress: float, user_name: str):
        title = "🎯 Goal Milestone!"
        body = f"{user_name} reached {progress:.0f}% of the '{goal_name}' goal!"
        return NotificationService.broadcast_alert(db, tenant_id, title, body, category="MILESTONE")

    @staticmethod
    def notify_new_account(db: Session, tenant_id: str, account_name: str, account_type: str):
        title = "🏦 New Account Added"
        body = f"A new {account_type} account '{account_name}' has been linked to the family."
        return NotificationService.broadcast_alert(db, tenant_id, title, body, category="ACCOUNT")

    @staticmethod
    def notify_budget_alert(db: Session, tenant_id: str, category: str, message: str):
        title = "⚠️ Budget Alert"
        body = f"Alert for {category}: {message}"
        return NotificationService.broadcast_alert(db, tenant_id, title, body, category="BUDGET_ALERT")

    @staticmethod
    def check_all_alerts(db: Session, tenant_id: str):
        """Helper to run all scheduled checks for a tenant"""
        from backend.app.modules.finance.services.investment_goal_service import InvestmentGoalService
        # Check Milestones
        InvestmentGoalService.check_goal_milestones(db, tenant_id)
        
        # Check Budgets
        NotificationService.check_budget_alerts(db, tenant_id)

    @staticmethod
    def check_budget_alerts(db: Session, tenant_id: str):
        """Check all budgets for a tenant and trigger alerts for 80%, 100%, 120%"""
        from backend.app.modules.finance.services.budget_service import BudgetService
        from backend.app.modules.notifications.models import Alert
        from datetime import date
        
        today = date.today()
        budgets = BudgetService.get_budgets(db, tenant_id, today.year, today.month)
        
        for b in budgets:
            if b.category == "OVERALL" or b.amount_limit == 0:
                continue
            
            percentage = b.percentage
            milestone = None
            if percentage >= 120: milestone = 120
            elif percentage >= 100: milestone = 100
            elif percentage >= 80: milestone = 80
            
            if not milestone:
                continue
                
            # Avoid duplicate alerts for the same milestone in the same month
            existing = db.query(Alert).filter(
                Alert.tenant_id == tenant_id,
                Alert.category == "BUDGET_ALERT",
                Alert.body.contains(f"{milestone}%"),
                Alert.body.contains(f"for {b.category}"),
                Alert.created_at >= date(today.year, today.month, 1)
            ).first()
            
            if existing:
                continue
                
            msg = f"Your spending in '{b.category}' is {percentage:.0f}% of your limit."
            NotificationService.notify_budget_alert(db, tenant_id, b.category, msg)

    @staticmethod
    def send_daily_summary(db: Session, tenant_id: str):
        """Aggregate today's stats and send a daily pulse summary"""
        from backend.app.modules.finance.models import Transaction
        from backend.app.core import timezone
        from datetime import timedelta
        
        now = timezone.utcnow()
        summary_start = now - timedelta(hours=24)
        
        # Aggregate spending
        txns = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.date >= summary_start,
            Transaction.amount < 0,
            Transaction.exclude_from_reports == False,
            Transaction.is_transfer == False
        ).all()
        
        total_spent = sum(abs(t.amount) for t in txns)
        count = len(txns)
        
        if count == 0:
            return # Maybe don't notify if nothing happened, or send a "Safe day!" message
            
        symbol = "₹"
        title = "🌙 Daily Pulse Summary"
        body = f"Total Spent Today: {symbol}{total_spent:,.0f} across {count} transactions."
        
        # Add a tip or budget status?
        from backend.app.modules.finance.services.analytics_service import AnalyticsService
        metrics = AnalyticsService.get_mobile_summary_lightweight(db, tenant_id)
        if metrics.get("budget_health"):
            bh = metrics["budget_health"]
            body += f"\nMonthly Budget: {bh['percentage']:.0f}% used."

        return NotificationService.broadcast_alert(db, tenant_id, title, body, category="INFO")
