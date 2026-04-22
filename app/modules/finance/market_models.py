import uuid
from sqlalchemy import Column, String, Numeric, DateTime, UniqueConstraint
from backend.app.core.market_database import MarketBase
from backend.app.core import timezone
from backend.app.core.timezone import UTCDateTime

class MutualFundNAVHistory(MarketBase):
    __tablename__ = "mutual_fund_nav_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_code = Column(String, nullable=False, index=True)
    nav_date = Column(DateTime, nullable=False, index=True) # Date part only (but stored as DateTime for consistency)
    nav = Column(Numeric(15, 4), nullable=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    __table_args__ = (
        UniqueConstraint('scheme_code', 'nav_date', name='uix_scheme_date'),
    )
