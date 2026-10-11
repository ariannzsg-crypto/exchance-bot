"""تاریخچه‌ی قیمت برای نمودار مودال.

- رمزارزها: داده‌ی واقعی از CoinGecko (market_chart) و تبدیل به تومان با
  نرخ دلار تتر/دلار همان لحظه از TGJU.
- ارز و طلا: سرویس تاریخچه‌ی عمومی و مطمئنی نداریم، پس دروغ نمی‌سازیم و
  success=false برمی‌گردانیم تا فرانت‌اند خودش تصمیم بگیرد.

قرارداد خروجی:
    {"success": true, "prices": [..], "unit": "تومان", "source": "CoinGecko", "days": 7}
    {"success": false, "reason": "history_not_available", "message": "..."}
"""

import json
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests

from lib.currencies import CURRENCIES
from lib.market_data import get_market

COINGECKO_CHART = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
ALLOWED_DAYS = {"1": 1, "7": 7, "30": 30, "90": 90, "365": 365}

_CACHE = {}          # {(code, days): (ts, payload)}
_TTL = 900           # ۱۵ دقیقه


def _usd_toman() -> float | None:
    try:
        usd = (get_market() or {}).get("usd") or {}
        price = usd.get("price")
        return float(price) if price else None
    except Exception:
        return None


def _coingecko_series(coin_id: str, days: int) -> list[float]:
    resp = requests.get(
        COINGECKO_CHART.format(coin_id=coin_id),
        params={"vs_currency": "usd", "days": days},
        headers={"User-Agent": UA},
        timeout=15,
    )
    resp.raise_for_status()
    prices = resp.json().get("prices") or []
    series = []
    for point in prices:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            series.append(float(point[1]))
    return series


def get_history(code: str, days: int = 7) -> dict:
    code = (code or "").strip().lower()
    days = days if days in ALLOWED_DAYS.values() else 7
    info = CURRENCIES.get(code)

    if not info:
        return {"success": False, "reason": "unknown_code", "message": "این نماد شناخته نشد."}

    if info.get("type") != "crypto" or not info.get("coingecko"):
        return {
            "success": False,
            "reason": "history_not_available",
            "message": "تاریخچه‌ی این نماد در دسترس نیست.",
        }

    key = (code, days)
    cached = _CACHE.get(key)
    if cached and (time.time() - cached[0]) < _TTL:
        return cached[1]

    usd_toman = _usd_toman()
    if not usd_toman:
        return {"success": False, "reason": "usd_rate_unavailable", "message": "نرخ دلار در دسترس نیست."}

    try:
        series = _coingecko_series(info["coingecko"], days)
    except Exception as exc:  # noqa: BLE001 - خطای شبکه به کاربر برمی‌گردد
        return {"success": False, "reason": "upstream_error", "message": str(exc)[:120]}

    if len(series) < 2:
        return {"success": False, "reason": "not_enough_data", "message": "داده‌ی کافی نبود."}

    payload = {
        "success": True,
        "code": code,
        "days": days,
        "unit": "تومان",
        "source": "CoinGecko + TGJU",
        "usd_toman": usd_toman,
        "prices": [round(p * usd_toman, 2) for p in series],
    }
    _CACHE[key] = (time.time(), payload)
    return payload


class handler(BaseHTTPRequestHandler):
    def _json(self, obj, status=200, cache="public, max-age=300"):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", cache)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        code = (query.get("code") or [""])[0]
        try:
            raw_days = int((query.get("days") or ["7"])[0])
        except ValueError:
            raw_days = 7
        days = ALLOWED_DAYS.get(str(raw_days), 7)

        try:
            result = get_history(code, days)
        except Exception as exc:  # noqa: BLE001
            self._json({"success": False, "reason": "server_error", "message": str(exc)[:120]},
                       status=200, cache="no-store")
            return

        self._json(result, cache="public, max-age=300" if result.get("success") else "no-store")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
