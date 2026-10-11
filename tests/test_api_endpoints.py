"""تست اندپوینت‌های ورسل (روی HTTP واقعی، آفلاین).

هر تست، کلاس `handler` واقعی همان فایل `api/*.py` را روی یک پورت لوپ‌بک بالا
می‌آورد و فقط منبع بیرونی (TGJU/CoinGecko/RSS/AI) را جایگزین می‌کند؛ پس مسیر،
کد وضعیت، هدرها و قرارداد JSON دقیقاً همان چیزی است که ورسل سرو می‌کند.
"""

import json

import pytest

from _helpers import request, serve

from api import history as history_api


class FakeResp:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")


# --- /api/market ----------------------------------------------------------------


def test_market_returns_only_currencies_that_have_a_price(monkeypatch):
    import api.market as market_api

    fake = {
        "usd": {
            "code": "usd", "name": "دلار آمریکا", "short": "دلار", "flag": "🇺🇸",
            "price": 264305.0, "change": 0.68, "unit": "تومان", "source": "TGJU",
            "type": "fiat",
        },
        "btc": {
            "code": "btc", "name": "بیت‌کوین", "short": "BTC", "flag": "₿",
            "price": 2.2e10, "change": 1.5, "unit": "تومان",
            "source": "CoinGecko + TGJU", "type": "crypto", "usd_price": 85000.0,
        },
    }
    monkeypatch.setattr(market_api, "get_market", lambda: fake)

    with serve("api.market") as base:
        resp = request(base + "/api/market")

    assert resp.status == 200
    body = resp.json()
    assert body["success"] is True
    assert body["source"] == "TGJU + CoinGecko"
    codes = [c["code"] for c in body["currencies"]]
    assert codes == ["usd", "btc"]          # فقط نمادهای موجود در بازار
    assert body["currencies"][1]["usd_price"] == pytest.approx(85000.0)
    assert resp.headers["Cache-Control"] == "public, max-age=10"
    assert resp.headers["Access-Control-Allow-Origin"] == "*"


def test_market_reports_500_when_the_source_explodes(monkeypatch):
    import api.market as market_api

    def boom():
        raise RuntimeError("tgju down")

    monkeypatch.setattr(market_api, "get_market", boom)

    with serve("api.market") as base:
        resp = request(base + "/api/market")

    assert resp.status == 500
    assert resp.json()["success"] is False


# --- /api/history ---------------------------------------------------------------


@pytest.fixture
def history_upstream(monkeypatch):
    """نرخ دلار ثابت + سری CoinGecko ساختگی."""
    monkeypatch.setattr(history_api, "get_market", lambda: {"usd": {"price": 200000.0}})
    history_api._CACHE.clear()

    def fake_get(url, params=None, headers=None, timeout=None):
        assert "coingecko" in url
        assert params["vs_currency"] == "usd"
        return FakeResp({"prices": [[1, 10.0], [2, 10.5], [3, 11.0]]})

    monkeypatch.setattr(history_api.requests, "get", fake_get)
    return history_api


def test_history_scales_crypto_prices_into_toman(history_upstream):
    result = history_upstream.get_history("btc", 7)

    assert result["success"] is True
    assert result["unit"] == "تومان"
    assert result["days"] == 7
    assert result["source"] == "CoinGecko + TGJU"
    assert result["prices"] == pytest.approx([2_000_000.0, 2_100_000.0, 2_200_000.0])


def test_history_rejects_unknown_and_non_crypto_codes(history_upstream):
    unknown = history_upstream.get_history("zzz", 7)
    assert unknown["success"] is False
    assert unknown["reason"] == "unknown_code"

    fiat = history_upstream.get_history("usd", 7)   # ارز فیات تاریخچه‌ی عمومی ندارد
    assert fiat["success"] is False
    assert fiat["reason"] == "history_not_available"


def test_history_without_a_dollar_rate_fails_cleanly(monkeypatch):
    monkeypatch.setattr(history_api, "get_market", lambda: {})
    history_api._CACHE.clear()
    result = history_api.get_history("btc", 7)
    assert result["success"] is False
    assert result["reason"] == "usd_rate_unavailable"


def test_history_reports_upstream_errors(monkeypatch):
    monkeypatch.setattr(history_api, "get_market", lambda: {"usd": {"price": 200000.0}})
    history_api._CACHE.clear()

    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResp({}, status_code=429, text="rate limited")

    monkeypatch.setattr(history_api.requests, "get", fake_get)
    result = history_api.get_history("btc", 7)
    assert result["success"] is False
    assert result["reason"] == "upstream_error"


def test_history_upstream_result_is_cached(monkeypatch, history_upstream):
    calls = {"n": 0}
    real_get = history_upstream.requests.get

    def counting_get(*a, **k):
        calls["n"] += 1
        return real_get(*a, **k)

    monkeypatch.setattr(history_upstream.requests, "get", counting_get)
    history_upstream.get_history("btc", 7)
    history_upstream.get_history("btc", 7)
    assert calls["n"] == 1


def test_history_endpoint_maps_the_days_parameter(monkeypatch):
    calls = []

    def fake_get_history(code, days):
        calls.append({"code": code, "days": days})
        return {"success": True, "prices": [1, 2], "unit": "تومان", "days": days}

    monkeypatch.setattr(history_api, "get_history", fake_get_history)

    with serve("api.history") as base:
        allowed = request(base + "/api/history?code=BTC&days=30")
        too_big = request(base + "/api/history?code=btc&days=99999")
        not_a_number = request(base + "/api/history?code=btc&days=abc")

    assert allowed.status == 200 and allowed.json()["success"] is True
    assert calls[0] == {"code": "BTC", "days": 30}       # کد همان‌طور که آمده رد می‌شود
    assert calls[1]["days"] == 7                          # مقدار غیرمجاز → پیش‌فرض ۷
    assert calls[2]["days"] == 7                          # مقدار غیرعددی → پیش‌فرض ۷
    assert too_big.json()["days"] == 7
    assert not_a_number.json()["days"] == 7


def test_history_endpoint_returns_json_contract_for_unknown_symbol(monkeypatch):
    monkeypatch.setattr(history_api, "get_history",
                        lambda code, days: {"success": False, "reason": "unknown_code"})

    with serve("api.history") as base:
        resp = request(base + "/api/history?code=zzz")

    assert resp.status == 200
    assert resp.json() == {"success": False, "reason": "unknown_code"}
    assert resp.headers["Cache-Control"] == "no-store"


def test_history_endpoint_survives_a_handler_exception(monkeypatch):
    def boom(code, days):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(history_api, "get_history", boom)

    with serve("api.history") as base:
        resp = request(base + "/api/history?code=btc")

    assert resp.status == 200
    assert resp.json()["success"] is False
    assert resp.json()["reason"] == "server_error"


# --- /api/news ------------------------------------------------------------------


def test_news_endpoint_returns_items(monkeypatch):
    import api.news as news_api

    payload = {"success": True, "count": 1,
               "items": [{"id": "tgju_1", "title": "خبر", "link": "https://x", "summary": ""}]}
    monkeypatch.setattr(news_api, "get_news", lambda: payload)

    with serve("api.news") as base:
        resp = request(base + "/api/news")

    assert resp.status == 200
    assert resp.json()["items"][0]["title"] == "خبر"
    assert resp.headers["Cache-Control"] == "public, max-age=300"


def test_news_endpoint_reports_failure(monkeypatch):
    import api.news as news_api

    def boom():
        raise RuntimeError("feed down")

    monkeypatch.setattr(news_api, "get_news", boom)

    with serve("api.news") as base:
        resp = request(base + "/api/news")

    assert resp.status == 500
    assert resp.json()["success"] is False


# --- /api/fear_greed ------------------------------------------------------------


def test_fear_greed_endpoint_parses_the_index(monkeypatch):
    import api.fear_greed as fg_api

    monkeypatch.setattr(fg_api.requests, "get",
                        lambda *a, **k: FakeResp({"data": [{"value": "61",
                                                            "value_classification": "Greed"}]}))

    with serve("api.fear_greed") as base:
        resp = request(base + "/api/fear_greed")

    assert resp.status == 200
    assert resp.json() == {"success": True, "data": {"value": 61, "classification": "Greed"}}


def test_fear_greed_endpoint_stays_200_when_upstream_fails(monkeypatch):
    import api.fear_greed as fg_api

    def boom(*a, **k):
        raise RuntimeError("alternative.me down")

    monkeypatch.setattr(fg_api.requests, "get", boom)

    with serve("api.fear_greed") as base:
        resp = request(base + "/api/fear_greed")

    assert resp.status == 200                    # قرارداد فعلی: خطا داخل بدنه، نه ۵۰۰
    assert resp.json()["success"] is False


# --- /api/chart -----------------------------------------------------------------


def test_chart_returns_a_quickchart_url_for_a_known_symbol(monkeypatch):
    import api.chart as chart_api

    monkeypatch.setattr(chart_api, "get_market",
                        lambda: {"usd": {"name": "دلار", "price": 264305.0, "change": 0.68}})

    with serve("api.chart") as base:
        light = request(base + "/api/chart?code=usd")
        dark = request(base + "/api/chart?code=usd&theme=dark")

    assert light.status == 200
    assert light.json()["chart_url"].startswith("https://quickchart.io/chart?")
    assert "bkg=f8f5ff" in light.json()["chart_url"]
    assert "bkg=0e0a1e" in dark.json()["chart_url"]


def test_chart_returns_404_for_unknown_symbol(monkeypatch):
    import api.chart as chart_api

    monkeypatch.setattr(chart_api, "get_market", lambda: {})

    with serve("api.chart") as base:
        resp = request(base + "/api/chart?code=zzz")

    assert resp.status == 404


# --- /api/ai_chat ---------------------------------------------------------------


def test_ai_chat_passes_market_context_to_the_model(monkeypatch):
    import api.ai_chat as chat_api

    captured = {}

    def fake_ai_chat(message, history=None, lang="fa", market_ctx=""):
        captured.update(message=message, history=history, lang=lang, market_ctx=market_ctx)
        return {"success": True, "reply": "دلار ۲۶۴٬۳۰۵ تومان است", "ai_powered": True}

    monkeypatch.setattr(chat_api, "ai_chat", fake_ai_chat)
    monkeypatch.setattr(chat_api, "get_market", lambda: {
        "usd": {"name": "دلار آمریکا", "price": 264305.0},
        "btc": {"name": "بیت‌کوین", "price": 2.2e10},
    })

    with serve("api.ai_chat") as base:
        resp = request(base + "/api/ai_chat", method="POST",
                       payload={"message": "قیمت دلار؟", "lang": "fa"})

    assert resp.status == 200
    assert resp.json()["reply"].startswith("دلار")
    assert captured["message"] == "قیمت دلار؟"
    assert "دلار آمریکا: 264,305 تومان" in captured["market_ctx"]
    assert "بیت‌کوین" in captured["market_ctx"]


def test_ai_chat_rejects_an_empty_message(monkeypatch):
    import api.ai_chat as chat_api

    monkeypatch.setattr(chat_api, "get_market", lambda: {})

    with serve("api.ai_chat") as base:
        resp = request(base + "/api/ai_chat", method="POST", payload={"message": "   "})

    assert resp.status == 400


def test_ai_chat_maps_provider_failure_to_500(monkeypatch):
    import api.ai_chat as chat_api

    monkeypatch.setattr(chat_api, "get_market", lambda: {})
    monkeypatch.setattr(chat_api, "ai_chat", lambda **k: {"success": False,
                                                          "message": "شلوغ است"})

    with serve("api.ai_chat") as base:
        resp = request(base + "/api/ai_chat", method="POST", payload={"message": "سلام"})

    assert resp.status == 500
    assert resp.json()["message"] == "شلوغ است"


def test_ai_chat_preflight_allows_browser_calls(monkeypatch):
    with serve("api.ai_chat") as base:
        resp = request(base + "/api/ai_chat", method="OPTIONS")

    assert resp.status == 200
    assert resp.headers["Access-Control-Allow-Origin"] == "*"
    assert "POST" in resp.headers["Access-Control-Allow-Methods"]


# --- قرارداد استقرار روی ورسل ----------------------------------------------------


def test_vercel_config_points_at_real_files():
    """جلوگیری از باگ قبلی: مسیر فرانت‌اند و نام فایل فانکشن باید یکی باشند."""
    from _helpers import ROOT

    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    assert config["outputDirectory"] == "web"
    assert (ROOT / "web" / "index.html").is_file()

    for path in config["functions"]:
        assert (ROOT / path).is_file(), f"فانکشن اعلام‌شده وجود ندارد: {path}"

    # مقصد rewrite یک «مسیر» است نه مسیر فایل: /api/ai_chat → api/ai_chat.py
    for rule in config["rewrites"]:
        name = rule["destination"].strip("/").split("/")[-1]
        assert (ROOT / "api" / f"{name}.py").is_file(), \
            f"مقصد rewrite فایل واقعی ندارد: {rule['destination']}"


def test_frontend_js_only_calls_existing_endpoints():
    """مسیرهای /api/... در فرانت‌اند باید معادل فایل واقعی در api/ داشته باشند."""
    import re
    from _helpers import ROOT

    js = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "web").glob("*.js"))
    called = set(re.findall(r"/api/([a-z0-9_-]+)", js))
    assert called, "هیچ فراخوانی API در فرانت‌اند پیدا نشد"

    available = {p.stem for p in (ROOT / "api").glob("*.py")}
    rewrites = {r["source"].split("/")[-1] for r in
                json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["rewrites"]}

    for name in called:
        assert name in available or name in rewrites, f"مسیر بی‌مقصد در فرانت‌اند: /api/{name}"
