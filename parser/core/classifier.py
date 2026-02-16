import re

class FinancialClassifier:
    
    # Keywords that suggest a financial transaction
    POSITIVE_KEYWORDS = [
        r"\bdebited\b", r"\bcredited\b", r"\bspent\b", r"\bpaid\b", r"\bsent\b", 
        r"\breceived\b", r"\btxn\b", r"\btransaction\b", r"\bacct\b", r"\ba/c\b", 
        r"\bbank\b", r"\bupi\b", r"\bwithdraw\b", r"\bpurchase\b", r"\bbill\b", 
        r"\bpayment\b", r"\btransfer\b"
    ]

    # Keywords that suggest noise (OTP, Promos, Notifications)
    NEGATIVE_KEYWORDS = [
        r"otp", r"login", r"password", r"verification code", 
        r"lucky winner", r"loan offer", r"apply now", r"your statement is ready",
        r"pre-approved", r"congratulations", r"cashback points", r"exclusive offer",
        r"click here", r"know more", r"vouchers", r"reward points", r"kyc update"
    ]

    # Weak signals that are common in spam but also in bank footers
    CLEANUP_KEYWORDS = [
        r"click here", r"know more", r"unsubscribe", r"mobile app", r"social media"
    ]

    @staticmethod
    def is_financial(content: str, source: str = "SMS") -> bool:
        """
        Heuristic check: filters noise while preserving valid bank alerts.
        """
        content_lower = content.lower()
        
        # 1. High-Confidence Noise Check (Fast Fail)
        # OTPs and Login alerts are never transactions we want to track
        for kw in [r"otp", r"login", r"password", r"verification code", r"kyc update"]:
            if re.search(kw, content_lower):
                return False
        
        # 2. Positive Scoring
        score = 0
        strong_signals = {r"debited", r"credited", r"rs.", r"inr", r"spent", r"paid", r"received"}
        has_strong_signal = False
        
        for kw in FinancialClassifier.POSITIVE_KEYWORDS:
            if re.search(kw, content_lower):
                score += 1
                if kw in strong_signals:
                    has_strong_signal = True
        
        # Currency bonus
        if "rs." in content_lower or "inr" in content_lower:
            score += 2
            has_strong_signal = True

        # 3. Negative Scoring (Penalties instead of fast-fail for common footer noise)
        penalty = 0
        for kw in FinancialClassifier.NEGATIVE_KEYWORDS + FinancialClassifier.CLEANUP_KEYWORDS:
            if re.search(kw, content_lower):
                penalty += 0.5 # Soft penalty
        
        # Threshold Logic:
        # - If it has a strong signal (debited/credited + rs.), we usually want it.
        # - Otherwise, positive score must outweigh noise.
        if has_strong_signal:
            return True
        
        return (score - penalty) >= 1
