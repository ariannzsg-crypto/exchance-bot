"""تست‌های ویجت قیمت، صفحه‌ی تنظیمش و اعلان اختصاصی.

این‌ها «تست استاتیک» هستند: مانیفست، منابع XML و کد جاوای اندروید را می‌خوانند.
دلیلش ساده است — ویجت و اعلان را نمی‌شود روی CI بدون شبیه‌ساز اجرا کرد، ولی
می‌شود مطمئن شد چیزی که به APK می‌رود سیم‌کشیِ درست دارد: گیرنده‌ی ثبت‌شده،
منابع موجود، شناسه‌های هم‌خوان، و رشته‌های هر دو زبان.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from _helpers import ROOT

MAIN = ROOT / "android" / "app" / "src" / "main"
JAVA = MAIN / "java" / "com" / "exchance" / "app"
WIDGET_JAVA = JAVA / "widget"
RES = MAIN / "res"
NS = "{http://schemas.android.com/apk/res/android}"


def attr(node, name):
    return node.get(NS + name) if node is not None else None


@pytest.fixture(scope="module")
def manifest():
    return ET.parse(MAIN / "AndroidManifest.xml").getroot()


def components(root, tag):
    return {attr(c, "name"): c for c in root.find("application").findall(tag)}


def actions_of(component, child="intent-filter"):
    return {attr(a, "name") for a in component.find(child).findall("action")}


def values_of(path: Path, include_untranslatable=False):
    """رشته/رنگ‌های یک فایل values.

    رشته‌های {@code translatable="false"} (مثل آدرس API) عمداً فقط در زبان
    پیش‌فرض هستند و در سنجش هم‌ترازی ترجمه‌ها شمرده نمی‌شوند.
    """
    out = {}
    for el in ET.parse(path).getroot():
        if el.tag not in ("string", "color") or not el.get("name"):
            continue
        if el.get("translatable") == "false" and not include_untranslatable:
            continue
        out[el.get("name")] = el.text or ""
    return out


# --- مانیفست -------------------------------------------------------------------


def test_manifest_registers_the_widget_with_a_config_screen(manifest):
    receivers = components(manifest, "receiver")
    widget = receivers[".widget.PriceWidgetProvider"]
    assert attr(widget, "exported") == "true", "سیستم باید بتواند APPWIDGET_UPDATE بفرستد"
    assert "android.appwidget.action.APPWIDGET_UPDATE" in actions_of(widget)

    meta = widget.find("meta-data")
    assert attr(meta, "name") == "android.appwidget.provider"
    assert attr(meta, "resource") == "@xml/ex_price_widget_info"

    config = components(manifest, "activity")[".widget.WidgetConfigActivity"]
    assert attr(config, "exported") == "true", "لانچر بیرون از اپ است و باید بتواند بازش کند"
    assert "android.appwidget.action.APPWIDGET_CONFIGURE" in actions_of(config)


def test_manifest_rearms_alerts_after_a_reboot(manifest):
    boot = components(manifest, "receiver")[".widget.BootReceiver"]
    assert "android.intent.action.BOOT_COMPLETED" in actions_of(boot)
    perms = {attr(p, "name") for p in manifest.findall("uses-permission")}
    assert "android.permission.RECEIVE_BOOT_COMPLETED" in perms
    assert "android.permission.POST_NOTIFICATIONS" in perms
    assert "android.permission.INTERNET" in perms


def test_an_app_update_rearms_alerts_too(manifest):
    """آپدیت اپ هم آلارم‌ها را پاک می‌کند، نه فقط ریبوت گوشی."""
    boot = components(manifest, "receiver")[".widget.BootReceiver"]
    assert "android.intent.action.MY_PACKAGE_REPLACED" in actions_of(boot)
    receiver = (WIDGET_JAVA / "BootReceiver.java").read_text(encoding="utf-8")
    assert "ACTION_MY_PACKAGE_REPLACED" in receiver


# --- منابع ویجت -----------------------------------------------------------------


def test_widget_info_refreshes_and_points_at_real_files():
    info = ET.parse(RES / "xml" / "ex_price_widget_info.xml").getroot()
    layout = attr(info, "initialLayout").split("/")[1]
    assert (RES / "layout" / (layout + ".xml")).is_file()

    # کمینه‌ی خود اندروید ۳۰ دقیقه است؛ کمتر بگذاری نادیده گرفته می‌شود
    assert int(attr(info, "updatePeriodMillis")) >= 1800000
    assert attr(info, "configure") == "com.exchance.app.widget.WidgetConfigActivity"
    assert attr(info, "minWidth") and attr(info, "minHeight")
    assert attr(info, "description"), "ویجت باید در انتخابگر توضیح داشته باشد"


def test_every_resource_the_java_uses_really_exists():
    """هر R.type.name در جاوا باید در res اعلام شده باشد (جلوگیری از تایپو)."""
    declared = {"id": set(), "layout": set(), "drawable": set(), "xml": set(), "mipmap": set(),
                "string": set(), "color": set()}

    for folder in RES.iterdir():
        if not folder.is_dir():
            continue
        kind = folder.name.split("-")[0]
        if kind in ("layout", "drawable", "xml", "mipmap"):
            for f in folder.iterdir():
                if f.is_file():
                    declared[kind].add(f.stem)
    for value_file in list((RES / "values").glob("*.xml")) + list((RES / "values-en").glob("*.xml")):
        # در اینجا رشته‌های translatable="false" هم منبع معتبرند
        for name in values_of(value_file, include_untranslatable=True):
            declared["string"].add(name)
        for el in ET.parse(value_file).getroot():
            if el.tag == "color" and el.get("name"):
                declared["color"].add(el.get("name"))
    for xml_file in RES.rglob("*.xml"):
        declared["id"].update(re.findall(r"@\+?id/([A-Za-z_]\w*)", xml_file.read_text(encoding="utf-8")))

    used = set()
    for java_file in JAVA.rglob("*.java"):
        # android.R.* از خود سیستم می‌آید و باید نادیده گرفته شود
        used.update(re.findall(
            r"(?<!android\.)\bR\.(id|layout|drawable|xml|mipmap|string|color)\.([A-Za-z_]\w*)",
            java_file.read_text(encoding="utf-8")))

    assert used, "هیچ ارجاعی به R پیدا نشد — مطمئن شو مسیرها درست است"
    missing = sorted(f"R.{kind}.{name}" for kind, name in used if name not in declared[kind])
    assert missing == [], f"منابع استفاده‌شده ولی تعریف‌نشده: {missing}"


def test_widget_shows_flag_price_and_change():
    layout = (RES / "layout" / "ex_widget_price.xml").read_text(encoding="utf-8")
    provider = (WIDGET_JAVA / "PriceWidgetProvider.java").read_text(encoding="utf-8")
    for view_id in ("ex_widget_flag", "ex_widget_name", "ex_widget_price", "ex_widget_change"):
        assert view_id in layout, f"شناسه‌ی {view_id} در چیدمان نیست"
        assert view_id in provider, f"کد {view_id} را پر نمی‌کند"
    assert "Money.price" in provider and "Money.change" in provider


# --- رفتار پس‌زمینه -------------------------------------------------------------


def test_each_widget_tap_target_is_unique():
    """درخواست‌کد ثابت، اکسترای ویجت‌های مختلف را روی هم می‌نویسد."""
    provider = (WIDGET_JAVA / "PriceWidgetProvider.java").read_text(encoding="utf-8")
    assert '("open:" + code).hashCode()' in provider
    assert '("cfg:" + widgetId).hashCode()' in provider
    assert "getActivity(context, 12," not in provider, "کد ثابت ۱۲ همه‌ی ویجت‌ها را یکی می‌کند"
    assert "getActivity(context, 13," not in provider, "تنظیم هر ویجت باید شناسه‌ی خودش را بگیرد"


def test_tapping_a_widget_opens_that_symbol_in_the_app():
    """ویجت کد نماد را می‌فرستد؛ اپ باید واقعاً همان نمودار را باز کند."""
    js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    main = (JAVA / "MainActivity.java").read_text(encoding="utf-8")
    assert 'getStringExtra("ex_symbol")' in main
    assert "exOpenSymbol" in main, "صفحه‌ی وب باید نماد را از پل بگیرد"
    # مقدار اکسترا قبل از رفتن داخل جاوااسکریپت پالایش می‌شود
    assert 'replaceAll("[^a-z0-9_-]"' in main
    assert "window.exOpenSymbol" in js
    assert "pendingNativeSymbol" in js, "اگر قیمت‌ها نرسیده باشند باید نگه دارد"
    assert "openPendingNativeSymbol();" in js


def test_widget_reports_unavailable_instead_of_loading_forever():
    provider = (WIDGET_JAVA / "PriceWidgetProvider.java").read_text(encoding="utf-8")
    store = (WIDGET_JAVA / "PriceStore.java").read_text(encoding="utf-8")
    assert "PriceStore.attemptedAt(context)" in provider
    assert "R.string.ex_widget_error" in provider
    assert "R.string.ex_widget_loading" in provider
    assert "markAttempt" in provider and "markAttempt" in store, \
        "هر تلاش شبکه باید ثبت شود تا حالت «در حال گرفتن» پایان داشته باشد"
    assert "ATTEMPT_AT" in store and "ATTEMPT_OK" in store


def test_unchanged_price_is_grey_not_green_or_red():
    provider = (WIDGET_JAVA / "PriceWidgetProvider.java").read_text(encoding="utf-8")
    notifier = (WIDGET_JAVA / "Notifier.java").read_text(encoding="utf-8")
    for code in (provider, notifier):
        assert "R.color.ex_text_dim" in code, "تغییر صفر باید خاکستری باشد"
        assert "change < 0" in code


def test_crypto_widget_shows_the_usd_price_too():
    provider = (WIDGET_JAVA / "PriceWidgetProvider.java").read_text(encoding="utf-8")
    assert "price.usd" in provider
    assert "unitText(price)" in provider


def test_refresh_survives_the_broadcast_and_stays_off_the_main_thread():
    provider = (WIDGET_JAVA / "PriceWidgetProvider.java").read_text(encoding="utf-8")
    assert "goAsync()" in provider, "بدون goAsync پروسه وسط درخواست کشته می‌شود"
    assert "Thread(" in provider and "PriceApi.fetch" in provider
    assert "MIN_INTERVAL_MS" in provider, "بدون محدودیت فاصله، درخواست‌ها پشت‌سرهم می‌شوند"
    assert "Alerts.evaluate" in provider, "بعد از هر تازه‌سازی باید حدها بررسی شوند"


def test_alerts_fire_once_per_crossing():
    alerts = (WIDGET_JAVA / "Alerts.java").read_text(encoding="utf-8")
    assert "HYSTERESIS" in alerts
    assert "firedHigh" in alerts and "firedLow" in alerts
    store = (WIDGET_JAVA / "PriceStore.java").read_text(encoding="utf-8")
    assert "setFiredHigh" in store and "setFiredLow" in store
    # حد تازه باید دوباره مسلح شود
    assert "_high_fired" in store and "_low_fired" in store


def test_alert_checks_run_periodically_without_an_exact_alarm_permission():
    scheduler = (WIDGET_JAVA / "AlertScheduler.java").read_text(encoding="utf-8")
    assert "setInexactRepeating" in scheduler, "آلارم دقیق در اندروید ۱۲+ اجازه‌ی جدا می‌خواهد"
    assert "cancel" in scheduler, "اگر کاربر حدها را پاک کند، آلارم باید لغو شود"
    receiver = (WIDGET_JAVA / "AlertAlarmReceiver.java").read_text(encoding="utf-8")
    assert "refreshAsync" in receiver


# --- اعلان ---------------------------------------------------------------------


def test_notification_has_its_own_channel_and_custom_layout():
    notifier = (WIDGET_JAVA / "Notifier.java").read_text(encoding="utf-8")
    assert "NotificationChannel" in notifier and "IMPORTANCE_HIGH" in notifier
    assert "setCustomContentView" in notifier
    assert "R.layout.ex_notification_price" in notifier
    assert "R.drawable.ex_stat_price" in notifier
    assert "canNotify" in notifier, "بدون بررسی اجازه، اعلان در اندروید ۱۳ خاموش می‌ماند"

    layout = (RES / "layout" / "ex_notification_price.xml").read_text(encoding="utf-8")
    for view_id in ("ex_notif_flag", "ex_notif_name", "ex_notif_price", "ex_notif_change", "ex_notif_note"):
        assert view_id in layout, f"شناسه‌ی {view_id} در چیدمان اعلان نیست"
        assert view_id in notifier, f"اعلان {view_id} را پر نمی‌کند"


def test_notification_strings_exist_in_every_language():
    fa = values_of(RES / "values" / "ex_strings.xml")
    en = values_of(RES / "values-en" / "ex_strings.xml")
    assert set(fa) == set(en), "رشته‌های ویجت/اعلان بین فارسی و انگلیسی ناهم‌ترازند"
    for key in ("ex_widget_label", "ex_config_high", "ex_config_low",
                "ex_notif_channel", "ex_notif_high_title", "ex_notif_low_title", "ex_notif_body"):
        assert fa.get(key) and en.get(key), key


# --- صفحه‌ی تنظیم ---------------------------------------------------------------


def test_config_screen_saves_the_symbol_and_the_thresholds():
    config = (WIDGET_JAVA / "WidgetConfigActivity.java").read_text(encoding="utf-8")
    assert "AppWidgetManager.EXTRA_APPWIDGET_ID" in config
    assert "setResult(RESULT_CANCELED)" in config, "تا «ذخیره» نزنیم ویجت نباید اضافه شود"
    assert "PriceStore.setWidgetCode" in config
    assert '"✓ "' in config and "notifyDataSetChanged()" in config, \
        "ردیف انتخاب‌شده باید نشانه داشته باشد"
    assert "PriceStore.setAlerts" in config
    assert "AlertScheduler.sync" in config
    assert "POST_NOTIFICATIONS" in config, "وقتی کاربر حد گذاشت باید اجازه‌ی اعلان را بخواهد"
    assert "PriceApi.fetch" in config, "فهرست نمادها باید از همان API بیاید"


# --- قرارداد با API -------------------------------------------------------------


def test_widget_reads_exactly_the_keys_the_api_sends(monkeypatch):
    """ویجت این کلیدها را از JSON می‌خواند.

    اگر نام کلیدی در API عوض شود، ویجت بی‌صدا «قیمت در دسترس نیست» می‌ماند و
    هیچ‌کس نمی‌فهمد چرا. پس همان نام‌ها را روی پاسخ واقعیِ /api/market قفل می‌کنیم.
    """
    import api.market as market_api

    from _helpers import request, serve

    fake = {
        "usd": {
            "code": "usd", "name": "دلار آمریکا", "short": "دلار", "flag": "🇺🇸",
            "price": 264305.0, "change": 0.68, "unit": "تومان", "type": "fiat",
        },
        "btc": {
            "code": "btc", "name": "بیت‌کوین", "short": "BTC", "flag": "₿",
            "price": 2.2e10, "change": 1.5, "unit": "تومان",
            "type": "crypto", "usd_price": 85000.0,
        },
    }
    monkeypatch.setattr(market_api, "get_market", lambda: fake)

    with serve("api.market") as base:
        resp = request(base + "/api/market")

    assert resp.status == 200
    rows = resp.json()["currencies"]
    assert [r["code"] for r in rows] == ["usd", "btc"]

    api_java = (WIDGET_JAVA / "PriceApi.java").read_text(encoding="utf-8")
    keys = set(re.findall(r'opt(?:String|Double)\("([a-z_]+)"', api_java))
    assert "code" in keys and "price" in keys, "کلیدهای JSON در PriceApi.java پیدا نشد"
    assert '"/api/market"' in api_java, "ویجت باید همین اندپوینت را بخواند"

    for row in rows:
        missing = sorted(k for k in keys if k not in row)
        assert missing == [], f"{row['code']}: این کلیدها در پاسخ API نیستند {missing}"

    # خط دلاری ویجت فقط وقتی معنا دارد که رمزارزها قیمت دلاری بدهند
    crypto = next(r for r in rows if r["code"] == "btc")
    assert isinstance(crypto["usd_price"], (int, float))


def test_widget_and_app_agree_on_the_api_host():
    """ویجت بومی و اپ وب باید یک سرور را صدا بزنند، وگرنه اپ به API نمی‌رسد."""
    api = values_of(RES / "values" / "ex_strings.xml", include_untranslatable=True)["ex_api_base"].strip()
    config_js = (ROOT / "web" / "config.js").read_text(encoding="utf-8")
    match = re.search(r'DEPLOYED_API\s*=\s*"([^"]+)"', config_js)
    assert match, "DEPLOYED_API در web/config.js پیدا نشد"
    assert match.group(1).rstrip("/") == api.rstrip("/")
