import sys
import os

# Add backend to path
sys.path.append(os.getcwd())

from backend.app.modules.ingestion.ai_service import AIService

test_cases = [
    "UPI/ZOMATO/TXN12345/BANGALORE",
    "VPA Q821044812 Shivraj Singh Chandravali Thakur",
    "VPA Q110131023 Suresh Pandi",
    "SWIGGY*ORDER_99",
    "AMAZON PAY INDIA PAYMT",
    "TRANSFER TO MRS ANITA",
    "IMPS/123456789/FOOD",
    "NEFT/P12345678/RENT",
    "PVR CINEMAS 1234",
    "A", # should be too short
    "1234567890", # should be junk
]

print(f"{'Original': <50} | {'Cleaned'}")
print("-" * 80)
for tc in test_cases:
    cleaned = AIService.heuristic_clean_merchant(tc)
    print(f"{tc: <50} | {cleaned}")
