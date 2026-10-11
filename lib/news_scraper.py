import time
import requests
import feedparser
from bs4 import BeautifulSoup
from .utils import clean_text

_CACHE = {"items": [], "ts": 0}
_TTL = 900
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

RSS = [
    {"id": "irasin", "name": "ایرسا", "flag": "🇮🇷", "lang": "fa", "category": "اقتصاد",
     "url": "https://www.irasin.ir/rss/tp/23"},
    {"id": "sedayebourse", "name": "صدای بورس", "flag": "📈", "lang": "fa", "category": "بورس",
     "url": "https://www.sedayebourse.ir/rss/tp/9042"},
    {"id": "icana", "name": "ایکانا", "flag": "🏛", "lang": "fa", "category": "اقتصاد",
     "url": "https://icana.ir/rss/tp/3"},
]

def _hash(s):
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return format(h, "x")[:12]

def _time(entry):
    for f in ("published_parsed", "updated_parsed"):
        t = entry.get(f)
        if t:
            try:
                return time.strftime("%Y-%m-%dT%H:%M:%S", t[:6])
            except Exception:
                pass
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def _fetch_rss(src):
    try:
        r = requests.get(src["url"], headers={"User-Agent": UA}, timeout=10)
        if r.status_code != 200:
            return []
        feed = feedparser.parse(r.content)
        items = []
        for e in feed.entries[:15]:
            title = clean_text(e.get("title", ""))
            link = e.get("link", "")
            if not title or not link:
                continue
            items.append({
                "id": f"{src['id']}_{_hash(link + title)}",
                "title": title, "link": link,
                "summary": clean_text(e.get("summary", ""))[:240],
                "image": None, "published": _time(e),
                "source_id": src["id"], "source_name": src["name"],
                "source_flag": src["flag"], "lang": src["lang"],
                "category": src["category"],
            })
        return items
    except Exception as e:
        print(f"RSS {src['id']}:", e)
        return []

def _fetch_tgju():
    try:
        r = requests.get("https://www.tgju.org/news", headers={"User-Agent": UA}, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        items, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/news/" not in href or href in ("/news", "/news/"):
                continue
            if not href.startswith("http"):
                href = "https://www.tgju.org" + href
            href = href.split("#")[0].split("?")[0]
            if href in seen:
                continue
            seen.add(href)
            title = clean_text(a.get_text(" ", strip=True))
            if not title or len(title) < 10:
                continue
            items.append({
                "id": f"tgju_{_hash(href + title)}", "title": title, "link": href,
                "summary": "", "image": None,
                "published": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source_id": "tgju", "source_name": "TGJU",
                "source_flag": "📊", "lang": "fa", "category": "اقتصاد",
            })
        return items[:25]
    except Exception as e:
        print("TGJU news:", e)
        return []

def get_news(force=False):
    now = time.time()
    if not force and _CACHE["items"] and (now - _CACHE["ts"]) < _TTL:
        return {"success": True, "items": _CACHE["items"],
                "count": len(_CACHE["items"])}

    items = []
    for s in RSS:
        items.extend(_fetch_rss(s))
    items.extend(_fetch_tgju())

    seen, uniq = set(), []
    for it in items:
        k = it.get("link") or it["id"]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)

    uniq.sort(key=lambda x: x["published"], reverse=True)
    uniq = uniq[:150]
    _CACHE["items"] = uniq
    _CACHE["ts"] = now

    return {"success": True, "items": uniq, "count": len(uniq)}