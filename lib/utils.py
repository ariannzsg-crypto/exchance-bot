import re
from datetime import datetime

def normalize_digits(text):
    if not text:
        return ""
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return str(text).translate(table)

def clean_text(text):
    text = normalize_digits(text or "")
    text = text.replace("\u200c", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()

def parse_number(text):
    if text is None:
        return None
    text = normalize_digits(str(text))
    text = text.replace(",", "").replace("٬", "").replace("٫", ".")
    text = re.sub(r"[^\d.\-]", "", text)
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None

def now_iso():
    return datetime.now().isoformat()