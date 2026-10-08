import re
import math
from indic_transliteration import sanscript

def transliterate_tamil(text):
    if not text:
        return text
    # Very basic wrapper, indic_transliteration handles standard unicode
    try:
        return sanscript.transliterate(text, sanscript.TAMIL, sanscript.ITRANS).lower()
    except:
        return text.lower()

def clean_name(raw_name):
    """
    1. Lowercase
    2. Transliterate Tamil to English
    3. Strip punctuation / honorifics (Mr, Mrs, Sri, Smt)
    4. Handle initials (arun.k -> arun k)
    5. Sort tokens for name-order normalization
    """
    if not raw_name:
        return ""
    
    name = raw_name.lower()
    name = transliterate_tamil(name)
    
    # Replace dots with spaces for initials
    name = name.replace(".", " ")
    
    # Remove honorifics
    honorifics = [r'\bmr\b', r'\bmrs\b', r'\bms\b', r'\bsri\b', r'\bsmt\b', r'\bdr\b']
    for h in honorifics:
        name = re.sub(h, '', name)
        
    # Remove non-alphanumeric except spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    # Remove extra spaces
    name = " ".join(name.split())
    
    # Normalize order by sorting tokens (useful for 'Arun Kumar' vs 'Kumar Arun')
    # We will keep both the sorted and original cleaned version for matching.
    return name

def parse_age(raw_age):
    """
    Parses messy age inputs into (age_min, age_max).
    Supports: "40", "40-45", "about 40", "40s"
    """
    if not raw_age:
        return None, None
        
    raw_age = str(raw_age).lower().strip()
    
    # Range: "40-45"
    if "-" in raw_age:
        parts = raw_age.split("-")
        try:
            return int(re.sub(r'\D', '', parts[0])), int(re.sub(r'\D', '', parts[1]))
        except:
            pass
            
    # "40s" -> 40 to 49
    if raw_age.endswith("s"):
        try:
            base = int(re.sub(r'\D', '', raw_age))
            return base, base + 9
        except:
            pass
            
    # "about 40", "~40" -> +- 3 years
    if "about" in raw_age or "~" in raw_age or "approx" in raw_age:
        try:
            val = int(re.sub(r'\D', '', raw_age))
            return max(0, val - 3), val + 3
        except:
            pass
            
    # Exact: "40"
    try:
        val = int(re.sub(r'\D', '', raw_age))
        return val, val
    except:
        return None, None

def clean_record(record_data):
    """Main function to clean an incoming record."""
    cleaned = record_data.copy()
    
    # Name
    raw_name = cleaned.get("name", "")
    cleaned["name_cleaned"] = clean_name(raw_name)
    if cleaned["name_cleaned"]:
        cleaned["name_sorted"] = " ".join(sorted(cleaned["name_cleaned"].split()))
    
    # Age
    raw_age = cleaned.get("age_raw")
    a_min, a_max = parse_age(raw_age)
    if a_min is not None:
        cleaned["age_min"] = a_min
    if a_max is not None:
        cleaned["age_max"] = a_max
        
    # Gender (Normalize to M/F/Unknown)
    gender = str(cleaned.get("gender", "")).lower()
    if gender in ["m", "male", "boy", "man"]:
        cleaned["gender"] = "M"
    elif gender in ["f", "female", "girl", "woman"]:
        cleaned["gender"] = "F"
    else:
        cleaned["gender"] = "Unknown"
        
    return cleaned
