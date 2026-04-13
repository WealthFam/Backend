from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from backend.app.modules.finance.services.investment_goal_service import InvestmentGoalService
from backend.app.modules.finance import schemas as finance_schemas
from backend.app.modules.auth import models as auth_models

class MobileInvestmentGoalService:
    @staticmethod
    def get_goals(db: Session, tenant_id: str, user_id: Optional[str] = None) -> List[Dict]:
        """
        Fetch investment goals with progress and metadata optimized for mobile.
        """
        goals_progress = InvestmentGoalService.get_goals(db, tenant_id, user_id=user_id)
        
        # We can further enrich this for mobile if needed, but the core service already provides progress.
        # Let's just ensure it's a list of dicts that mobile expects.
        return [g.model_dump() for g in goals_progress]

    @staticmethod
    def get_goal(db: Session, goal_id: str, tenant_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch a single goal with full details.
        """
        # The core service doesn't have a specific get_goal_with_progress single method,
        # but we can filter the list or implement one.
        all_goals = InvestmentGoalService.get_goals(db, tenant_id, user_id=user_id)
        goal = next((g for g in all_goals if str(g.id) == goal_id), None)
        return goal.model_dump() if goal else None

    @staticmethod
    def create_goal(db: Session, goal_in: finance_schemas.InvestmentGoalCreate, tenant_id: str) -> Dict:
        db_goal = InvestmentGoalService.create_goal(db, goal_in, tenant_id)
        return finance_schemas.InvestmentGoalRead.model_validate(db_goal).model_dump()

    @staticmethod
    def update_goal(db: Session, goal_id: str, update: finance_schemas.InvestmentGoalUpdate, tenant_id: str) -> Optional[Dict]:
        db_goal = InvestmentGoalService.update_goal(db, goal_id, update, tenant_id)
        return finance_schemas.InvestmentGoalRead.model_validate(db_goal).model_dump() if db_goal else None

    @staticmethod
    def delete_goal(db: Session, goal_id: str, tenant_id: str) -> bool:
        return InvestmentGoalService.delete_goal(db, goal_id, tenant_id)

    @staticmethod
    def link_holding(db: Session, goal_id: str, holding_id: str, tenant_id: str) -> bool:
        return InvestmentGoalService.link_holding_to_goal(db, holding_id, goal_id, tenant_id)

    @staticmethod
    def unlink_holding(db: Session, holding_id: str, tenant_id: str) -> bool:
        return InvestmentGoalService.link_holding_to_goal(db, holding_id, None, tenant_id)
