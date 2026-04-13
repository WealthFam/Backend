import re
import json
from datetime import datetime

class PatternGenerator:
    """
    Generates regex patterns from labeled training data.
    These patterns are then pushed to the External Parser Service configuration.
    This logic remains local to support the interactive training feedback loop.
    """
    @staticmethod
    def generate_regex_and_config(raw_content: str, labels: dict, txn_type: str = "DEBIT"):
        """
        Attempts to find labels in raw_content and generate a robust regex.
        Supports variety of formats for amounts and dates.
        """
        clean_content = " ".join(raw_content.split())
        
        mapping = {"type": txn_type}
        if labels.get("category") and labels.get("category") != "Uncategorized":
            mapping["category"] = labels.get("category")
            
        group_idx = 1
        
        # 1. Prepare search variations for each field
        search_fields = []
        
        # Amount: Try different precision variations
        amt = labels.get("amount")
        if amt is not None:
            try:
                amt_float = float(amt)
                variations = [
                    f"{amt_float:.2f}",
                    f"{amt_float:.1f}",
                    str(int(amt_float)),
                    f"{amt_float:,.2f}" # Commas
                ]
                search_fields.append(("amount", list(set(variations))))
            except: pass
            
        # Date: Try common SMS date formats for the given date
        dt = labels.get("date")
        if dt:
            if isinstance(dt, str):
                try:
                    # Handle ISO format from frontend
                    dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                except: pass
            
            if isinstance(dt, (datetime,)):
                variations = [
                    dt.strftime("%d/%m/%y"),
                    dt.strftime("%d-%m-%y"),
                    dt.strftime("%d/%m/%Y"),
                    dt.strftime("%d-%m-%Y"),
                    dt.strftime("%d %b %y"),
                    dt.strftime("%d %b %Y"),
                    dt.strftime("%d-%b-%y"),
                    dt.strftime("%d/%m"),
                    dt.strftime("%d %B")
                ]
                search_fields.append(("date", list(set(variations))))

        # Others
        for key in ["recipient", "account_mask", "ref_id"]:
            val = labels.get(key)
            if val:
                search_fields.append((key, [str(val)]))

        # 2. Find best hits in content (longest match wins to handle overlaps)
        hits = [] # List of (start, end, key)
        used_ranges = []
        
        # Priority search order to avoid mask/ref-id collisions
        for key, variations in search_fields:
            best_match = None
            # Sort variations by length descending
            for var in sorted(variations, key=len, reverse=True):
                if not var or len(var) < 1: continue
                
                # Check if it exists in content
                match = re.search(re.escape(var), clean_content, re.IGNORECASE)
                if match:
                    start, end = match.span()
                    # Check overlap with already found fields
                    if any(start < ue and end > us for us, ue in used_ranges):
                        continue
                    
                    best_match = (start, end, key)
                    break
            
            if best_match:
                hits.append(best_match)
                used_ranges.append((best_match[0], best_match[1]))
        
        # Sort hits by start position
        hits.sort()
        
        # 3. Construct regex with anchors
        regex_parts = []
        last_pos = 0
        
        def process_anchor(text: str) -> str:
            if not text: return ""
            # Escape the anchor text for regex safety
            escaped = re.escape(text)
            
            # Handle both literal spaces and escaped spaces (\ ) from various python versions
            # Ensure literal spaces are replaced by flexible whitespace match \s*
            escaped = escaped.replace(r'\ ', r'\s*').replace(' ', r'\s*')
            
            # Make digit sequences (dates, IDs, OTPs) flexible
            # This allows the anchor to match different codes/dates in the same message structure
            escaped = re.sub(r'\d{2,}', r'\\d+', escaped)
            return escaped

        for start, end, key in hits:
            # Add text between the last match and this one
            regex_parts.append(process_anchor(clean_content[last_pos:start]))
            # Add the capture group
            regex_parts.append("(.*?)")
            mapping[key] = group_idx
            group_idx += 1
            last_pos = end
            
        # Add remaining tail
        regex_parts.append(process_anchor(clean_content[last_pos:]))
            
        final_regex = "".join(regex_parts)
        # Ensure it matches the whole line or segment
        return final_regex, json.dumps(mapping)
