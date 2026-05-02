from fastapi import APIRouter
from .accounts import router as accounts_router
from .transactions import router as transactions_router
from .categories import router as categories_router
from .budgets import router as budgets_router
from .recurring import router as recurring_router
from .analytics import router as analytics_router
from .mutual_funds import router as mutual_funds_router
from .loans import router as loans_router
from .expense_groups import router as expense_groups_router
from .investment_goals import router as investment_goals_router
from .search import router as search_router
from .statements import router as statements_router

router = APIRouter()

@router.get("/ping")
def ping():
    return {"ping": "pong"}

router.include_router(accounts_router, tags=["Accounts"])
router.include_router(transactions_router, tags=["Transactions"])
router.include_router(categories_router, tags=["Categories"])
router.include_router(budgets_router, tags=["Budgets"])
router.include_router(recurring_router, tags=["Recurring"])
router.include_router(analytics_router, tags=["Analytics"])
router.include_router(mutual_funds_router, tags=["Mutual Funds"])
router.include_router(loans_router, tags=["Loans"])
router.include_router(expense_groups_router)
router.include_router(investment_goals_router)
router.include_router(search_router)
router.include_router(statements_router)
