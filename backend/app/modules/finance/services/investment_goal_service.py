from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.modules.finance import models, schemas
from decimal import Decimal

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
            models.InvestmentGoal.tenant_id == tenant_id
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
                models.MutualFundHolding.tenant_id == tenant_id
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
            goal_data = schemas.InvestmentGoalRead.from_orm(goal)

            results.append(schemas.InvestmentGoalProgress(
                **goal_data.dict(exclude={'holdings', 'assets'}),
                holdings=[h.dict() for h in processed_holdings],
                assets=[a.dict() for a in processed_assets],
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
            models.InvestmentGoal.tenant_id == tenant_id
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
            models.InvestmentGoal.tenant_id == tenant_id
        ).first()
        if not db_goal:
            return False
            
        # Unlink holdings
        db.query(models.MutualFundHolding).filter(
            models.MutualFundHolding.goal_id == goal_id
        ).update({models.MutualFundHolding.goal_id: None})
        
        db.delete(db_goal)
        db.commit()
        return True

    @staticmethod
    def link_holding_to_goal(db: Session, holding_id: str, goal_id: Optional[str], tenant_id: str) -> bool:
        holding = db.query(models.MutualFundHolding).filter(
            models.MutualFundHolding.id == holding_id,
            models.MutualFundHolding.tenant_id == tenant_id
        ).first()
        if not holding:
            return False
            
        holding.goal_id = goal_id
        db.commit()
        return True

    @staticmethod
    def add_asset(db: Session, goal_id: str, asset: schemas.GoalAssetCreate, tenant_id: str) -> Optional[models.GoalAsset]:
        goal = db.query(models.InvestmentGoal).filter(
            models.InvestmentGoal.id == goal_id,
            models.InvestmentGoal.tenant_id == tenant_id
        ).first()
        if not goal:
            return None
            
        data = asset.model_dump()
        if data.get('linked_account_id') == '':
            data['linked_account_id'] = None

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
