import re
import time
import requests
from bs4 import BeautifulSoup
from .currencies import CURRENCIES
from .utils import clean_text, normalize_digits, parse_number

TGJU_URL = "https://gem.tgju.org/currency"
TGJU_GOLD_URL = "https://www.tgju.org/"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

_CACHE = {"combined": {}, "ts": 0}
_TTL = 10

def _row_name(row):
    """نام ردیف = متن اولین سلول (نه کل ردیف).

    در بعضی ردیف‌های TGJU ویجت‌های مخفی (مثل لیست تبدیل ارز) داخل ردیف هستند و
    متن آن‌ها نام چندین ارز را دارد؛ اگر کل متن ردیف مقایسه شود، مثلاً «ین ژاپن»
    اشتباهاً به ردیف «یوان چین» وصل می‌شود.
    """
    for cell in row.find_all(["td", "th"]):
        txt = clean_text(cell.get_text(" ", strip=True))
        if txt:
            return txt
    return ""


def _row_matches(row, aliases):
    """تطبیق دقیق یا با مرز کلمه (نه زیررشته‌ی آزاد)."""
    name = _row_name(row).lower()
    if not name:
        return False
    for alias in aliases:
        alias = clean_text(alias).lower()
        if not alias:
            continue
        if name == alias:
            return True
        # مثل «ین ژاپن (100 ین)» یا «گرم نقره ۹۹۹»
        if name.startswith(alias + " ") or name.startswith(alias + "("):
            return True
    return False

# درصد تغییر مثل "(0.68%)" یا "(-0.31%)" در ردیف‌های TGJU
_CHANGE_RE = re.compile(r"\(\s*([-+]?[\d.,]+)\s*%\)")


def _extract_price(row):
    """قیمت فقط از data-price خوانده می‌شود.

    قبلاً اگر این ویژگی نبود، بزرگ‌ترین عدد داخل ردیف برگردانده می‌شد؛ همین کار
    باعث می‌شد ردیف‌های تزئینی صفحه (مثل ویجت تبدیل یا فوتر) به‌جای قیمت واقعی
    طلا و نقره بیایند و مثلاً «طلای ۱۸ عیار» ۱۸۲ تومان نمایش داده شود.
    """
    dp = row.get("data-price")
    if not dp:
        return None
    price = parse_number(dp)
    if price is None or price <= 0 or price > 1e15:
        return None
    return price


def _extract_change(row):
    """درصد تغییر ۲۴ ساعته‌ی همان ردیف (قبلاً برای ارز و طلا همیشه صفر بود)."""
    txt = clean_text(row.get_text(" ", strip=True))
    m = _CHANGE_RE.search(txt)
    if not m:
        return 0.0
    raw = normalize_digits(m.group(1)).replace(",", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0

def _fetch(url):
    r = requests.get(f"{url}?_={time.time()}",
                     headers={"User-Agent": UA, "Cache-Control": "no-cache"}, timeout=12)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def _fetch_fiat():
    rows = []
    try:
        rows.extend(_fetch(TGJU_URL).find_all("tr"))
    except Exception as e:
        print("TGJU cur:", e)
    try:
        rows.extend(_fetch(TGJU_GOLD_URL).find_all("tr"))
    except Exception as e:
        print("TGJU gold:", e)

    result = {}
    for code, info in CURRENCIES.items():
        if info.get("type") != "fiat":
            continue
        found, change = None, 0.0
        excludes = info.get("tgju_exclude", [])
        for row in rows:
            if not _row_matches(row, info.get("tgju", [])):
                continue
            name = _row_name(row).lower()
            if any(clean_text(e).lower() in name for e in excludes):
                continue
            p = _extract_price(row)
            if not p:          # ردیف بدون data-price = ردیف قیمت واقعی نیست
                continue
            found, change = p, _extract_change(row)
            break
        if not found:
            continue
        # TGJU فقط ین را «(100 ین)» قیمت می‌دهد؛ وون و بقیه به ازای یک واحد هستند
        if code == "jpy":
            found /= 100
        result[code] = {
            "code": code, "name": info["name"], "short": info["short"],
            "flag": info["flag"], "price": found / 10, "change": change,
            "unit": "تومان", "source": "TGJU", "type": "fiat",
        }
    return result

def _fetch_crypto(usd_toman):
    if not usd_toman:
        return {}
    ids = [i["coingecko"] for i in CURRENCIES.values()
           if i.get("type") == "crypto" and i.get("coingecko")]
    try:
        r = requests.get(f"{COINGECKO_URL}?_={time.time()}",
                         params={"ids": ",".join(ids), "vs_currencies": "usd",
                                 "include_24hr_change": "true"}, timeout=15)
        data = r.json()
    except Exception as e:
        print("CoinGecko:", e)
        return {}

    result = {}
    for code, info in CURRENCIES.items():
        if info.get("type") != "crypto":
            continue
        if code in ("usdt", "usdc"):
            usd_price, change = 1.0, 0.0
        else:
            coin = data.get(info.get("coingecko"), {})
            usd_price = coin.get("usd")
            change = coin.get("usd_24h_change", 0.0)
        if usd_price is None:
            continue
        result[code] = {
            "code": code, "name": info["name"], "short": info["short"],
            "flag": info["flag"], "price": float(usd_price) * float(usd_toman),
            "usd_price": float(usd_price), "change": float(change or 0),
            "unit": "تومان", "source": "CoinGecko + TGJU", "type": "crypto",
        }
    return result

def get_market(force=False):
    now = time.time()
    if not force and _CACHE["combined"] and (now - _CACHE["ts"]) < _TTL:
        return _CACHE["combined"]
    fiat = _fetch_fiat()
    usd_toman = fiat.get("usd", {}).get("price")
    crypto = _fetch_crypto(usd_toman)
    combined = {**fiat, **crypto}
    _CACHE["combined"] = combined
    _CACHE["ts"] = now
    return combined