from sqlalchemy.orm import Session
from backend.app.modules.notifications.models import Alert

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
