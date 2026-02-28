from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, model_validator
from datetime import datetime
from decimal import Decimal

class ParsedTransaction(BaseModel):
    amount: Decimal
    date: datetime
    description: str
    type: str # DEBIT or CREDIT
    account_mask: Optional[str] = None # Last 4 digits if available
    recipient: Optional[str] = None
    category: Optional[str] = None
    ref_id: Optional[str] = None
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    raw_message: str
    source: str = "SMS" # SMS, EMAIL, etc.
    is_ai_parsed: bool = False # Flag to indicate if AI was used

    @model_validator(mode='after')
    def generate_fallback_ref(self) -> 'ParsedTransaction':
        if not self.ref_id:
            # Format: YYYYMMDDHHMMSS-MASK-AMOUNT
            # We use a hash-like prefix to indicate it's generated
            date_str = self.date.strftime("%Y%m%d%H%M%S")
            mask = self.account_mask or "XXXX"
            # Ensure amount is stringified cleanly
            amt_str = f"{self.amount:.2f}"
            self.ref_id = f"GEN-{date_str}-{mask}-{amt_str}"
        return self

class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str, date_hint: Optional[datetime] = None) -> Optional[ParsedTransaction]:
        """
        Parse raw content (SMS body or CSV row) into a structured transaction.
        Returns None if parsing fails or content is irrelevant.
        """
        pass

class BaseSmsParser(BaseParser):
    @abstractmethod
    def can_handle(self, sender: str, message: str) -> bool:
        """
        Determine if this parser can handle the given SMS.
        """
        pass

class BaseEmailParser(BaseParser):
    @abstractmethod
    def can_handle(self, subject: str, body: str) -> bool:
        """
        Determine if this parser can handle the given Email.
        """
        pass
