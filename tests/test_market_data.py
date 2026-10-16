"""تست تحلیلگر قیمت TGJU.

همه‌ی تست‌ها آفلاین‌اند: HTML خام TGJU با یک fixture شبیه‌سازی می‌شود تا خرابیِ
تحلیل‌گر بعد از تغییر احتمالی ساختار سایت، بدون تماس با اینترنت دیده شود.
"""

import time

import pytest
from bs4 import BeautifulSoup

from lib import market_data as md

# --- fixture: نمونه‌ی واقعی‌شکل از ردیف‌های TGJU ---------------------------------
# نکات مهمی که در متن HTML تکرار شده‌اند (هر کدام قبلاً یک باگ واقعی بوده):
#   1. ردیف تزئینی ویجت تبدیل: هیچ data-price روی <tr> ندارد.
#   2. ردیف واقعی یوان، داخل خودش متن «ین ژاپن» دارد (ویجت مخفی).
#   3. ردیف مثقالی طلای ۱۸ عیار باید با tgju_exclude رد شود.
#   4. «انس نقره» قیمت دلاری است و نباید جای گرم نقره بیاید.
TGJU_HTML = """
<table>
  <tr>
    <td>مبدل ارز</td>
    <td><span>۱ دلار = ۱۸۲ تومان</span></td>
  </tr>
  <tr data-price="2643050">
    <td>دلار آمریکا</td>
    <td>۲۶۴,۳۰۵</td>
    <td><span class="change">(0.68%)</span></td>
  </tr>
  <tr data-price="0">
    <td>یورو</td>
    <td>نامعتبر</td>
  </tr>
  <tr data-price="9999999999999999999">
    <td>پوند انگلیس</td>
    <td>عدد بی‌معنی</td>
  </tr>
  <tr data-price="700000">
    <td>یوان چین</td>
    <td>تبدیل ین ژاپن به یوان چین</td>
    <td>(1.25%)</td>
  </tr>
  <tr data-price="500000">
    <td>ین ژاپن (100 ین)</td>
    <td>(-0.31%)</td>
  </tr>
  <tr data-price="77777777">
    <td>طلای 18 عیار مثقالی</td>
    <td>(3.5%)</td>
  </tr>
  <tr data-price="12345670">
    <td>طلای 18 عیار</td>
    <td>(1.10%)</td>
  </tr>
  <tr data-price="888888888">
    <td>انس نقره</td>
    <td>(0.9%)</td>
  </tr>
  <tr data-price="188880">
    <td>گرم نقره 999</td>
    <td>(0.42%)</td>
  </tr>
</table>
"""


def _soup(html=TGJU_HTML):
    return BeautifulSoup(html, "html.parser")


@pytest.fixture
def tgju(monkeypatch):
    """جایگزینِ _fetch: هر دو نشانی TGJU همین HTML را برمی‌گردانند."""
    monkeypatch.setattr(md, "_fetch", lambda url: _soup())
    md._CACHE["combined"] = {}
    md._CACHE["ts"] = 0
    return md._fetch_fiat()


# --- واحدهای کوچک ---------------------------------------------------------------


def test_row_name_is_first_cell_not_whole_row():
    row = _soup().find_all("tr")[4]  # ردیف یوان چین با ویجت مخفی «ین ژاپن»
    assert md._row_name(row) == "یوان چین"


def test_row_matches_is_not_a_loose_substring():
    row = _soup().find_all("tr")[4]
    # alias کوتاه «ین» نباید به ردیف یوان چین وصل شود
    assert md._row_matches(row, ["ین"]) is False
    assert md._row_matches(row, ["یوان چین", "یوان"]) is True


def test_row_matches_accepts_parenthesised_unit_suffix():
    row = _soup().find_all("tr")[5]  # «ین ژاپن (100 ین)»
    assert md._row_matches(row, ["ین ژاپن"]) is True


def test_extract_price_requires_data_price():
    rows = _soup().find_all("tr")
    assert md._extract_price(rows[0]) is None          # ردیف تزئینی ویجت
    assert md._extract_price(rows[1]) == 2643050.0


def test_extract_price_rejects_zero_and_absurd_values():
    rows = _soup().find_all("tr")
    assert md._extract_price(rows[2]) is None          # data-price="0"
    assert md._extract_price(rows[3]) is None          # بزرگ‌تر از 1e15


def test_extract_change_reads_parenthesised_percent():
    rows = _soup().find_all("tr")
    assert md._extract_change(rows[1]) == pytest.approx(0.68)
    assert md._extract_change(rows[5]) == pytest.approx(-0.31)
    assert md._extract_change(rows[0]) == 0.0          # بدون درصد


def test_extract_change_normalizes_persian_digits():
    row = _soup('<tr data-price="100"><td>دلار</td><td>(۰.۶۸%)</td></tr>').find("tr")
    assert md._extract_change(row) == pytest.approx(0.68)


# --- _fetch_fiat: قرارداد تومانی و استثناها -------------------------------------


def test_fiat_prices_are_converted_from_rial_to_toman(tgju):
    # TGJU ریال می‌دهد؛ خروجی باید تومان باشد
    assert tgju["usd"]["price"] == pytest.approx(264305.0)
    assert tgju["usd"]["change"] == pytest.approx(0.68)
    assert tgju["usd"]["unit"] == "تومان"
    assert tgju["usd"]["source"] == "TGJU"
    assert tgju["usd"]["type"] == "fiat"


def test_jpy_is_per_single_yen_not_per_hundred(tgju):
    # TGJU «(100 ین)» قیمت می‌دهد: ۵۰۰۰۰۰ ریال / ۱۰۰ / ۱۰ = ۵۰۰ تومان
    assert tgju["jpy"]["price"] == pytest.approx(500.0)


def test_currencies_without_a_valid_row_are_omitted(tgju):
    # یورو ردیف نامعتبر داشت و بقیه‌ی ارزها در fixture نیستند
    assert "eur" not in tgju
    assert "pound" not in tgju
    assert "gbp" not in tgju
    assert set(tgju) == {"usd", "jpy", "cny", "gold18", "silver", "silver_oz"}


def test_silver_ounce_keeps_its_dollar_price(tgju):
    # «انس نقره» دلاری است؛ نه با گرم نقره قاطی می‌شود و نه با ضریب ریال→تومان کوچک
    assert tgju["silver_oz"]["price"] == pytest.approx(888888888.0)
    assert tgju["silver_oz"]["unit"] == "دلار"
    assert tgju["silver_oz"]["group"] == "gold"
    assert tgju["silver"]["price"] == pytest.approx(18888.0)


def test_gold_excludes_shekels_and_other_variants(tgju):
    # ردیف «طلای 18 عیار مثقالی» باید رد شود و ردیف ساده بیاید
    assert tgju["gold18"]["price"] == pytest.approx(1234567.0)


def test_silver_uses_gram_row_not_troy_ounce(tgju):
    assert tgju["silver"]["price"] == pytest.approx(18888.0)


def test_hidden_widget_text_does_not_cross_link_currencies(tgju):
    # قبلاً متن ویجت مخفی داخل ردیف یوان باعث می‌شد «ین ژاپن» به یوان وصل شود
    assert tgju["cny"]["price"] == pytest.approx(70000.0)
    assert tgju["cny"]["change"] == pytest.approx(1.25)
    assert tgju["jpy"]["price"] != tgju["cny"]["price"]


def test_fiat_survives_a_dead_upstream(monkeypatch):
    def boom(url):
        raise RuntimeError("network down")

    monkeypatch.setattr(md, "_fetch", boom)
    assert md._fetch_fiat() == {}


# --- _fetch_crypto --------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_crypto_prices_are_usd_times_toman_rate(monkeypatch):
    payload = {
        "bitcoin": {"usd": 85000.0, "usd_24h_change": 1.5},
        "ethereum": {"usd": 3000.0, "usd_24h_change": -0.5},
    }
    monkeypatch.setattr(md.requests, "get", lambda *a, **k: _FakeResponse(payload))

    result = md._fetch_crypto(264305.0)

    assert result["btc"]["price"] == pytest.approx(85000.0 * 264305.0)
    assert result["btc"]["usd_price"] == pytest.approx(85000.0)
    assert result["btc"]["change"] == pytest.approx(1.5)
    assert result["btc"]["source"] == "CoinGecko + TGJU"
    # استیبل‌کوین‌ها بدون تماس با CoinGecko روی یک دلار ثابت می‌مانند
    assert result["usdt"]["usd_price"] == pytest.approx(1.0)
    assert result["usdt"]["price"] == pytest.approx(264305.0)


def test_crypto_is_skipped_without_a_dollar_rate(monkeypatch):
    called = []
    monkeypatch.setattr(md.requests, "get", lambda *a, **k: called.append(1))
    assert md._fetch_crypto(None) == {}
    assert called == []


def test_crypto_survives_a_dead_upstream(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("coingecko down")

    monkeypatch.setattr(md.requests, "get", boom)
    assert md._fetch_crypto(264305.0) == {}


# --- get_market -----------------------------------------------------------------


def test_get_market_caches_and_force_bypasses_cache(monkeypatch):
    calls = {"fiat": 0}

    def fake_fiat():
        calls["fiat"] += 1
        return {"usd": {"price": 100.0}}

    monkeypatch.setattr(md, "_fetch_fiat", fake_fiat)
    monkeypatch.setattr(md, "_fetch_crypto", lambda rate: {"btc": {"price": rate * 2}})
    md._CACHE["combined"] = {}
    md._CACHE["ts"] = 0

    first = md.get_market()
    assert first == {"usd": {"price": 100.0}, "btc": {"price": 200.0}}
    assert calls["fiat"] == 1

    md.get_market()                      # از کش می‌آید
    assert calls["fiat"] == 1

    md.get_market(force=True)            # کش نادیده گرفته می‌شود
    assert calls["fiat"] == 2


def test_get_market_refetches_after_ttl(monkeypatch):
    calls = {"n": 0}

    def fake_fiat():
        calls["n"] += 1
        return {}

    monkeypatch.setattr(md, "_fetch_fiat", fake_fiat)
    monkeypatch.setattr(md, "_fetch_crypto", lambda rate: {})

    md._CACHE["combined"] = {}
    md._CACHE["ts"] = 0
    md.get_market()
    md._CACHE["ts"] = time.time() - md._TTL - 1
    md.get_market()

    assert calls["n"] == 2
