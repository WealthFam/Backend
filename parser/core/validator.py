from parser.core import timezone
from datetime import datetime, timedelta
from typing import List
from parser.schemas.transaction import Transaction

class TransactionValidator:
    
    @staticmethod
    def validate(txn: Transaction, raw_content: str) -> List[str]:
        warnings = []
        
        # 1. Future Date Check
        # Allow 1 day buffer for timezones
        if txn.date > timezone.utcnow() + timedelta(days=1):
            warnings.append(f"Future date detected: {txn.date}. This might be a parsing error.")
            
        # 2. Currency Mismatch
        # If parser says INR but text has USD, etc.
        if txn.currency == "INR":
            raw_upper = raw_content.upper()
            if "USD" in raw_upper or "$" in raw_upper:
                warnings.append("Potential currency mismatch: USD detected in text but parsed as INR.")
            elif "EUR" in raw_upper or "EURO" in raw_upper:
                warnings.append("Potential currency mismatch: EUR detected in text but parsed as INR.")
                
        return warnings

    @staticmethod
    def enrich_time(txn: Transaction):
        """
        If date is TODAY, and time component is missing (00:00:00), 
        add current time to make sorting better.
        """
        if txn.date.date() == timezone.utcnow().date():
            # Check if time is 00:00/midnight (likely default)
            if txn.date.hour == 0 and txn.date.minute == 0 and txn.date.second == 0:
                 now = timezone.utcnow()
                 txn.date = txn.date.replace(hour=now.hour, minute=now.minute, second=now.second)
