from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.modules.finance import models, schemas

class InvestmentGoalService:
    @staticmethod
    def get_goals(db: Session, tenant_id: str, user_id: Optional[str] = None) -> List[schemas.InvestmentGoalProgress]:
        # Sanitization
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
            
        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_
        
        query = db.query(models.InvestmentGoal).options(
            joinedload(models.InvestmentGoal.assets).joinedload(models.GoalAsset.linked_account),
            joinedload(models.InvestmentGoal.holdings).joinedload(models.MutualFundHolding.meta)
        ).filter(
            models.InvestmentGoal.tenant_id == tenant_id,
            models.InvestmentGoal.is_deleted == False
        )
        
        if user_id:
            query = query.filter(or_(models.InvestmentGoal.owner_id == user_id, models.InvestmentGoal.owner_id == None))
            
        goals = query.all()
        
        results = []
        for goal in goals:
            # 1. Process MF Holdings (Explicit Query)
            mf_holdings = db.query(models.MutualFundHolding).options(
                joinedload(models.MutualFundHolding.meta)
            ).filter(
                models.MutualFundHolding.goal_id == goal.id,
                models.MutualFundHolding.tenant_id == tenant_id,
                models.MutualFundHolding.is_deleted == False
            ).all()

            mf_amount = Decimal('0.0')
            processed_holdings = []
            for h in mf_holdings:
                # Calculate amount
                h_val = Decimal('0.0')
                if h.current_value:
                    h_val = Decimal(str(h.current_value))
                elif h.units and h.last_nav:
                    h_val = Decimal(str(float(h.units) * float(h.last_nav)))
                
                mf_amount += h_val
                
                # Build detail object
                processed_holdings.append(schemas.GoalHoldingRead(
                    id=h.id,
                    scheme_name=h.scheme_name,
                    folio_number=h.folio_number,
                    current_value=h_val
                ))
            
            # 2. Process Assets (Explicit Query)
            goal_assets = db.query(models.GoalAsset).options(
                joinedload(models.GoalAsset.linked_account)
            ).filter(
                models.GoalAsset.goal_id == goal.id,
                models.GoalAsset.tenant_id == tenant_id
            ).all()

            asset_amount = Decimal('0.0')
            processed_assets = []
            for a in goal_assets:
                # Calculate amount
                asset_val = Decimal('0.0')
                type_str = str(a.type.value if hasattr(a.type, 'value') else a.type).upper()
                if type_str == "BANK_ACCOUNT" and a.linked_account:
                    if not a.linked_account.is_deleted:
                        asset_val = Decimal(str(a.linked_account.balance or 0))
                elif type_str == "MANUAL":
                    asset_val = Decimal(str(a.manual_amount or 0))
                
                asset_amount += asset_val
                
                # Build detail object
                processed_assets.append(schemas.GoalAssetRead(
                    id=a.id,
                    goal_id=goal.id,
                    type=type_str,
                    name=a.name,
                    display_name=a.display_name,
                    manual_amount=a.manual_amount,
                    current_value=asset_val,
                    created_at=a.created_at
                ))

            current_amount = mf_amount + asset_amount
            progress = 0.0
            if goal.target_amount > 0:
                progress = min(float(current_amount) / float(goal.target_amount) * 100, 100.0)
            
            # Convert to schema
            goal_data = schemas.InvestmentGoalRead.model_validate(goal)

            results.append(schemas.InvestmentGoalProgress(
                **goal_data.model_dump(exclude={'holdings', 'assets'}),
                holdings=processed_holdings,
                assets=processed_assets,
                current_amount=current_amount,
                progress_percentage=progress,
                holdings_count=len(processed_holdings),
                remaining_amount=max(Decimal('0.0'), goal.target_amount - current_amount)
            ))
        
        return results

    @staticmethod
    def create_goal(db: Session, goal: schemas.InvestmentGoalCreate, tenant_id: str) -> models.InvestmentGoal:
        data = goal.model_dump()
        if data.get('owner_id') in [None, "null", "undefined", ""]:
            data['owner_id'] = None
            
        db_goal = models.InvestmentGoal(
            **data,
            tenant_id=tenant_id
        )
        db.add(db_goal)
        db.commit()
        db.refresh(db_goal)
        return db_goal

    @staticmethod
    def update_goal(db: Session, goal_id: str, update: schemas.InvestmentGoalUpdate, tenant_id: str) -> Optional[models.InvestmentGoal]:
        db_goal = db.query(models.InvestmentGoal).filter(
            models.InvestmentGoal.id == goal_id,
            models.InvestmentGoal.tenant_id == tenant_id,
            models.InvestmentGoal.is_deleted == False
        ).first()
        if not db_goal:
            return None
            
        data = update.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(db_goal, k, v)
            
        db.commit()
        db.refresh(db_goal)
        return db_goal

    @staticmethod
    def delete_goal(db: Session, goal_id: str, tenant_id: str) -> bool:
        db_goal = db.query(models.InvestmentGoal).filter(
            models.InvestmentGoal.id == goal_id,
            models.InvestmentGoal.tenant_id == tenant_id,
            models.InvestmentGoal.is_deleted == False
        ).first()
        if not db_goal:
            return False
            
        now = timezone.utcnow()
        db_goal.is_deleted = True
        db_goal.deleted_at = now
        
        # We don't unlink holdings/assets so they can be restored if the goal is restored
        db.commit()
        return True

    @staticmethod
    def link_holding_to_goal(db: Session, holding_id: str, goal_id: Optional[str], tenant_id: str) -> bool:
        # Check for aggregate ID (e.g. group_123456)
        actual_id = holding_id
        if holding_id.startswith("group_"):
            actual_id = holding_id.replace("group_", "")
        
        # If actual_id is numeric, it's a scheme_code (aggregate view)
        if actual_id.isdigit():
            holdings = db.query(models.MutualFundHolding).filter(
                models.MutualFundHolding.scheme_code == actual_id,
                models.MutualFundHolding.tenant_id == tenant_id,
                models.MutualFundHolding.is_deleted == False
            ).all()
            if not holdings:
                return False
            for h in holdings:
                h.goal_id = goal_id
            db.commit()
            return True

        # Otherwise treat as standard holding ID
        holding = db.query(models.MutualFundHolding).filter(
            models.MutualFundHolding.id == actual_id,
            models.MutualFundHolding.tenant_id == tenant_id,
            models.MutualFundHolding.is_deleted == False
        ).first()
        if not holding:
            return False

        # Validate target goal if provided
        if goal_id:
            goal = db.query(models.InvestmentGoal).filter(
                models.InvestmentGoal.id == goal_id,
                models.InvestmentGoal.tenant_id == tenant_id,
                models.InvestmentGoal.is_deleted == False
            ).first()
            if not goal:
                return False
            
        holding.goal_id = goal_id
        db.commit()
        return True

    @staticmethod
    def add_asset(db: Session, goal_id: str, asset: schemas.GoalAssetCreate, tenant_id: str) -> Optional[models.GoalAsset]:
        goal = db.query(models.InvestmentGoal).filter(
            models.InvestmentGoal.id == goal_id,
            models.InvestmentGoal.tenant_id == tenant_id,
            models.InvestmentGoal.is_deleted == False
        ).first()
        if not goal:
            return None
            
        data = asset.model_dump()
        if data.get('linked_account_id') == '':
            data['linked_account_id'] = None

        # Validate linked account if provided
        if data.get('linked_account_id'):
            acc = db.query(models.Account).filter(
                models.Account.id == data['linked_account_id'],
                models.Account.tenant_id == tenant_id,
                models.Account.is_deleted == False
            ).first()
            if not acc:
                raise ValueError("Linked account not found or is deleted")

        db_asset = models.GoalAsset(
            **data,
            goal_id=goal_id,
            tenant_id=tenant_id
        )
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset

    @staticmethod
    def remove_asset(db: Session, asset_id: str, tenant_id: str) -> bool:
        db_asset = db.query(models.GoalAsset).filter(
            models.GoalAsset.id == asset_id,
            models.GoalAsset.tenant_id == tenant_id
        ).first()
        if not db_asset:
            return False
        db.delete(db_asset)
        db.commit()
        return True
    @staticmethod
    def check_goal_milestones(db: Session, tenant_id: str):
        """
        Check all goals for a tenant and trigger notifications for milestones (80%, 100%).
        Uses Alert system to prevent duplicate notifications for the same milestone.
        """
        from backend.app.modules.notifications.services import NotificationService
        from backend.app.modules.notifications.models import Alert
        from backend.app.modules.auth.models import User

        goals_progress = InvestmentGoalService.get_goals(db, tenant_id)
        
        for goal in goals_progress:
            # Determine appropriate milestone
            milestone = None
            if goal.progress_percentage >= 100:
                milestone = 100
            elif goal.progress_percentage >= 80:
                milestone = 80
            
            if not milestone:
                continue
            
            # Check if alert already sent today or recently for this milestone
            # We look for an alert with this text/milestone in the last 7 days to avoid spam
            existing_alert = db.query(Alert).filter(
                Alert.tenant_id == tenant_id,
                Alert.category == "MILESTONE",
                Alert.body.contains(f"reached {milestone}%"),
                Alert.body.contains(f"'{goal.name}'")
            ).first()
            
            if existing_alert:
                continue
                
            # Get owner name
            owner_name = "Someone"
            if goal.owner_id:
                owner = db.query(User).filter(User.id == goal.owner_id).first()
                if owner:
                    owner_name = owner.full_name or owner.email.split('@')[0]
            
            NotificationService.notify_milestone(
                db, 
                tenant_id, 
                goal_name=goal.name, 
                progress=milestone, 
                user_name=owner_name
            )
