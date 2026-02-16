from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DeviceRegister(BaseModel):
    device_id: str
    device_name: str
    fcm_token: Optional[str] = None

class DeviceBase(BaseModel):
    device_id: str
    device_name: str

class DeviceResponse(DeviceBase):
    id: str
    tenant_id: str
    is_approved: bool
    is_enabled: bool
    is_ignored: bool
    last_seen_at: datetime
    created_at: datetime
    user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class MobileLoginRequest(BaseModel):
    username: str
    password: str
    device_id: str  # Mandatory for mobile login
    device_name: str

class MobileLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    device_status: DeviceResponse
    user_role: Optional[str] = "ADULT" # Default to ADULT for safety/compat, but should be explicit

class ToggleApprovalRequest(BaseModel):
    is_approved: bool

class ToggleEnabledRequest(BaseModel):
    is_enabled: bool

class AssignUserRequest(BaseModel):
    user_id: Optional[str] = None

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_ignored: Optional[bool] = None
    user_id: Optional[str] = None

class DashboardSummary(BaseModel):
    today_total: float
    monthly_total: float
    currency: str = "INR"

class BudgetSummary(BaseModel):
    limit: float
    spent: float
    percentage: float

class CategorySpending(BaseModel):
    name: str
    amount: float

class RecentTransaction(BaseModel):
    id: str
    date: datetime
    description: str
    amount: float
    category: str
    account_name: Optional[str] = None
    account_owner_name: Optional[str] = None
    is_hidden: bool = False

class SpendingTrendItem(BaseModel):
    date: str
    amount: float
    daily_limit: float

class CategoryPieItem(BaseModel):
    name: str
    value: float
    color: Optional[str] = None

class MobileDashboardResponse(BaseModel):
    summary: DashboardSummary
    budget: BudgetSummary
    spending_trend: List[SpendingTrendItem]
    category_distribution: List[CategoryPieItem]
    recent_transactions: List[RecentTransaction]
    pending_triage_count: int = 0

class MemberResponse(BaseModel):
    id: str
    name: str
    role: str
    avatar_url: Optional[str] = None

class TransactionResponse(BaseModel):
    items: List[RecentTransaction]
    next_page: Optional[int] = None

class FundHolding(BaseModel):
    scheme_code: str
    scheme_name: str
    units: float
    current_value: float
    invested_value: float
    profit_loss: float
    last_updated: str
    xirr: Optional[float] = None
    allocation_percentage: Optional[float] = None # Calculated on fly

class MobileFundsResponse(BaseModel):
    total_invested: float
    total_current: float
    total_pl: float
    xirr: Optional[float] = None
    holdings: List[FundHolding]

class Category(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    type: str = "expense"

class UpdateTransactionCategoryRequest(BaseModel):
    category: str
    create_rule: bool = False
    rule_keywords: Optional[List[str]] = None
