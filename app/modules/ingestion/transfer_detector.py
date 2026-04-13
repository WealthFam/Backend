import json
import re
from typing import Optional, List
from backend.app.modules.finance.models import CategoryRule, Account

class TransferDetector:
    """
    Modular logic for detecting if a transaction is a self-transfer to another tracked account.
    """
    
    @staticmethod
    def detect(description: Optional[str], recipient: Optional[str], accounts: List[Account], rules: List[CategoryRule] = None) -> (bool, Optional[str]):
        """
        Analyzes description and recipient to find a destination account ID.
        Returns (is_transfer, to_account_id).
        """
        if not description and not recipient:
            return False, None
            
        text = f"{description or ''} {recipient or ''}".lower()
        
        # 0. Check Rules first (User defined/learned)
        if rules:
            for rule in rules:
                if not rule.is_transfer: continue
                keywords = json.loads(rule.keywords)
                if any(k.lower() in text for k in keywords):
                    return True, rule.to_account_id

        # 1. Match by Account Mask (e.g., *1234 or XX1234)
        for acc in accounts:
            if acc.account_mask:
                mask = acc.account_mask.lower().replace('x', '').replace('*', '')
                if mask and len(mask) >= 4:
                    patterns = [
                        rf"(?i)(?:card|a/c|acc|to|paying|bill\s*for)\s*(?:[x\*]*){mask}",
                        rf"{mask}"
                    ]
                    for p in patterns:
                        if re.search(p, text):
                            return True, acc.id
            
            # 2. Match by Account Name (direct match)
            if len(acc.name) > 3 and acc.name.lower() in text:
                return True, acc.id
                
        return False, None
