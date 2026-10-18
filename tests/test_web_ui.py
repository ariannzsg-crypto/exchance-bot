"""تست رابط کاربری وب: انیمیشن ورود، پرچم‌ها، تب طلا و ترجمه‌ها.

اینجا سروری اجرا نمی‌شود؛ هرچه بررسی می‌شود متن خودِ فایل‌های `web/` است — یعنی
همان چیزی که مرورگر و اپ اندروید واقعاً دریافت می‌کنند. هدف، گرفتن خرابی‌های
ساکتی است که فقط با چشم دیده می‌شوند: پرده‌ای که گیر می‌کند، پرچمی که جا افتاده،
یا کلید ترجمه‌ای که در یکی از زبان‌ها نیست.
"""

import re

import pytest

from _helpers import ROOT

WEB = ROOT / "web"

FLAG_RE = re.compile(r"[\U0001F1E6-\U0001F1FF]{2}")


@pytest.fixture(scope="module")
def html():
    return (WEB / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js():
    return (WEB / "app.js").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sw():
    return (WEB / "sw.js").read_text(encoding="utf-8")


def splash_block(html):
    """بخش CSS و بخش نشانه‌گذاری پرده‌ی ورود."""
    style = re.search(r"\.splash \{.*?\n\}", html, re.S).group(0)
    markup = re.search(r'<div class="splash".*?\n</div>\n', html, re.S).group(0)
    return style, markup


def i18n_blocks(js):
    """سه دیکشنری زبان را از app.js جدا می‌کند."""
    parts = re.split(r"\n    (fa|en|ar): \{", js)
    blocks = {}
    for i in range(1, len(parts), 2):
        body = re.split(r"\n    [a-z]{2}: \{|\n\};", parts[i + 1])[0]
        blocks[parts[i]] = set(re.findall(r"\b([a-zA-Z][a-zA-Z0-9]*):\s*\"", body))
    return blocks


# --- انیمیشن ورود ---------------------------------------------------------------


def test_splash_covers_the_whole_screen_above_everything(html):
    style, markup = splash_block(html)
    assert 'id="splash"' in markup
    assert "position: fixed" in style and "inset: 0" in style
    # باید روی توست‌ها و مودال‌ها هم بنشیند
    z = int(re.search(r"z-index:\s*(\d+)", style).group(1))
    assert z > 2000, "پرده باید بالاتر از توست (z-toast=2000) باشد"


def test_splash_cannot_get_stuck_without_javascript(html):
    style, _ = splash_block(html)
    # جایگزین ایمن: اگر app.js اجرا نشود، خودِ CSS پرده را کنار می‌برد
    assert "animation: splashSafety" in style
    assert "@keyframes splashSafety" in html
    noscript_hidden = re.search(r"@keyframes splashSafety \{[^}]*\}", html, re.S).group(0)
    assert "visibility: hidden" in noscript_hidden and "pointer-events: none" in noscript_hidden


def test_splash_orbit_is_full_of_flag_emojis(html):
    _, markup = splash_block(html)
    orbit = re.search(r'<div class="splash-orbit".*?</div>', markup, re.S).group(0)
    assert len(FLAG_RE.findall(orbit)) >= 8, "حلقه‌ی ورود باید پرچم‌ها را نشان دهد"
    for mark in ("🥇", "₿"):
        assert mark in orbit, f"نشانه‌ی {mark} در حلقه‌ی ورود نیست"
    flags_row = re.search(r'<div class="splash-flags".*?</div>', markup, re.S).group(0)
    assert len(FLAG_RE.findall(flags_row)) >= 4
    for mark in ("🥇", "🪙", "₿"):
        assert mark in flags_row, f"نشانه‌ی {mark} در ردیف نشانه‌های ورود نیست"


def test_splash_holds_for_about_a_second_then_leaves(js):
    assert "function initSplash()" in js and "function finishSplash()" in js
    assert re.search(r"initSplash\(\);", js), "initSplash در راه‌اندازی صدا زده نمی‌شود"
    hold = re.search(r"prefersReducedMotion\.matches \? (\d+) : (\d+);", js)
    assert hold, "مدت نگه‌داشتن پرده پیدا نشد"
    reduced, normal = int(hold.group(1)), int(hold.group(2))
    assert 150 <= reduced <= 400, "برای کاربر کم‌حرکت پرده باید تقریباً فوری برود"
    assert 700 <= normal <= 2500, "ورود نه آنی باشد نه آزاردهنده"
    # کاربر باید بتواند با کلیک/کلید از پرده بگذرد
    for ev in ("pointerdown", "keydown", "touchstart"):
        assert f'"{ev}"' in js


def test_app_sections_enter_in_a_stagger_after_the_splash(html, js):
    assert 'classList.add("booted")' in js
    assert "body.booted .app > *" in html
    assert re.search(r"body\.booted \.app > \*:nth-child\(n\+9\)", html)
    assert "@keyframes bootUp" in html


def test_reduced_motion_turns_the_entry_animation_off(html):
    blocks = re.findall(r"@media \(prefers-reduced-motion: reduce\) \{.*?\n\}", html, re.S)
    splash_blocks = [b for b in blocks if ".splash-inner" in b]
    assert splash_blocks, "بلوک کم‌حرکتِ پرده پیدا نشد"
    block = splash_blocks[0]
    assert ".splash-orbit" in block and "animation: none !important" in block
    assert "body.booted .app > * { animation: none !important; }" in block
    # محوی ۴۲۰ms هم باید خاموش شود، وگرنه کاربر کم‌حرکت همان انیمیشن را می‌بیند
    splash_rule = re.search(r"\.splash \{[^}]*\}", block).group(0)
    assert "transition: none" in splash_rule, "در حالت کم‌حرکت، محوی پرده باید حذف شود"


def test_reduced_motion_removes_the_splash_right_away(js):
    """وقتی محوی خاموش است، گره‌ی پرده نباید ۷۰۰ms در DOM بماند."""
    assert re.search(r"prefersReducedMotion\.matches \? 0 : 700", js), \
        "حذف پرده باید در حالت کم‌حرکت فوری باشد"


# --- کش سرویس‌ورکر ---------------------------------------------------------------


def test_new_frontend_lands_outside_the_old_service_worker_cache(html, sw):
    assert re.search(r'/app\.js\?v=\d+', html), "برای رد شدن از کش SW شماره‌ی نسخه لازم است"
    assert re.search(r'/config\.js\?v=\d+', html)
    assert '"/app.js",' in sw and '"/index.html",' in sw
    assert 'const VERSION = "ex-v' in sw


# --- پرچم‌ها و تب طلا ------------------------------------------------------------


def test_flag_strip_makes_every_flagged_symbol_one_tap_away(html, js):
    assert 'id="flagStrip"' in html and 'role="group"' in html
    assert "function renderFlagStrip()" in js
    assert re.search(r"renderTicker\(currencies\);\n    renderFlagStrip\(\);", js), \
        "نوار پرچم بعد از رسیدن قیمت‌ها ساخته نمی‌شود"
    assert 'class="flag-chip' in js and "c.flag" in js


def test_flags_are_used_in_tabs_and_compare_and_news(html, js):
    assert 'data-i18n="tabFiat"' in html and 'data-i18n="tabCrypto"' in html
    for lang in ("فارسی", "English", "عربية"):
        pass  # پرچم زبان‌ها در HTML است؛ پایین‌تر بررسی می‌شود
    lang_buttons = re.search(r'<div id="langPop".*?</div>', html, re.S).group(0)
    assert len(FLAG_RE.findall(lang_buttons)) == 3, "هر زبان باید پرچم خودش را داشته باشد"
    assert 'class="cl-flag"' in js and "a.flag" in js and "b.flag" in js
    assert "item.source_flag" in js, "پرچم منبع خبر باید رندر شود"
    for marker in ("mr-flag", "vi-top", "tf"):
        assert marker in js


def test_gold_tab_filters_by_group_not_by_type(html, js):
    assert 'data-category="gold"' in html
    assert "function groupOf(c)" in js
    assert "groupOf(c) === activeCategory" in js, "فیلتر تب‌ها باید از گروه استفاده کند"
    # پاسخ‌های قدیمیِ کش‌شده که group ندارند نباید تب طلا را خراب کنند
    assert 'return "crypto" : "fiat"' in js or 'String(c.type || "fiat") === "crypto"' in js
    market = (ROOT / "api" / "market.py").read_text(encoding="utf-8")
    assert '"group": item.get("group"' in market, "اندپوینت باید group را برگرداند"


def test_symbol_card_shows_the_flag_next_to_the_code(js):
    assert 't("symbolCode")' in js
    assert 't("goldLabel")' in js and "function typeLabelOf(c)" in js


# --- اشتراک‌گذاری نمودار ---------------------------------------------------------


def test_share_card_draws_the_real_chart_and_price(js):
    """تصویر ارسالی باید همان نمودار و قیمت باشد، نه فقط یک عدد روی زمینه."""
    assert "function drawShareCard(c, points, timeframe)" in js
    assert "function drawShareChart(ctx, values, box, color)" in js
    assert "drawShareChart(ctx, chartValues" in js, "کارت باید نمودار را بکشد"
    # نمودارِ کارت از همان نقاطی می‌آید که در مودال انتخاب شده است
    assert "opts.points" in js and "liveChartData" in js
    assert "prepareChartPoints(getHistory(c), code" in js, "برای کارت‌ها باید تاریخچه بخواند"
    assert "W = 1080, H = 1080" in js
    assert '"EXCHANCE"' in js and 't("unit")' in js
    assert 'SHARE_TF_KEY' in js and "t(tfKey)" in js, "بازه‌ی زمانی روی کارت بیاید"
    # رنگ نمودار با جهت قیمت هماهنگ است
    assert 'trend.cls === "up" ? "#30a46c"' in js


def test_share_sheet_shows_a_preview_and_actions(html, js):
    assert 'id="shareModal"' in html and 'id="sharePreview"' in html
    assert 'id="shareSend"' in html and 'id="shareSave"' in html and 'id="shareCopy"' in html
    assert 'data-close-share="1"' in html, "کلیک روی پس‌زمینه باید مودال را ببندد"
    assert "sharePreview.src = shareState.url" in js, "پیش‌نمایش باید عکس واقعیِ ساخته‌شده باشد"
    assert "shareSend.addEventListener(\"click\", sendShareImage)" in js
    assert "shareSave.addEventListener(\"click\", downloadShareImage)" in js
    assert "shareCopy.addEventListener(\"click\", copyShareText)" in js
    # حافظه‌ی blob باید آزاد شود تا باز و بسته کردن مودال نشتی نداشته باشد
    assert "URL.revokeObjectURL(shareState.url)" in js


def test_android_sends_the_png_through_the_native_share_sheet(js):
    """WebView اندروید فایل را با navigator.share نمی‌فرستد؛ مسیر بومی لازم است."""
    assert 'cap.nativePromise("Filesystem", "writeFile"' in js
    assert 'directory: "CACHE"' in js and "recursive: true" in js
    assert 'cap.nativePromise("Share", "share"' in js
    assert "files: [saved.uri]" in js, "فایل باید با URI واقعی فایل به شیت برود"
    assert "function blobToBase64(blob)" in js
    # ترتیب فالبک: بومی، بعد Web Share، بعد دانلود
    body = js[js.index("async function sendShareImage()"):js.index("function downloadShareImage()")]
    assert body.index("nativeShareImage(s)") < body.index("navigator.share") < body.index("downloadShareImage()")
    assert 'e.name === "AbortError"' in body, "بستن شیت توسط کاربر خطا نیست"


def test_slow_history_does_not_lock_the_timeframe_buttons(js):
    """وقتی سرویس تاریخچه جواب نمی‌دهد، نمودار و دکمه‌ها نباید قفل شوند."""
    assert "new AbortController()" in js and "ctrl.abort()" in js
    assert "clearTimeout(timer)" in js, "تایمر باید بعد از پاسخ یا خطا هم پاک شود"
    assert 'synthPoints(currentChart.code + ":" + tf' in js, \
        "در نبود داده، نمودار باید با بازه‌ی جدید بازسازی شود نه بازه‌ی قبلی"


def test_every_card_and_the_chart_modal_can_share(html, js):
    assert 'class="share-btn"' in js and 'card.querySelector(".share-btn")' in js
    assert 'openShare(c, { timeframe: "7d" })' in js
    assert 'openShare(c, { points: liveChartData, timeframe: currentTimeframe })' in js, \
        "دکمه‌ی مودال باید همان بازه‌ای را بفرستد که کاربر می‌بیند"
    assert ".card .share-btn" in html
    assert ".card .cmp-btn { left: 50px; }" in html and ".card .share-btn { left: 90px; }" in html, \
        "دکمه‌ها روی موبایل نباید روی هم بیفتند"


def test_shared_link_opens_that_symbol_right_away(js):
    assert "function shareUrlFor(code)" in js and '"/?code="' in js
    assert "window.SHARE_BASE || API_BASE || location.origin" in js, \
        "در اپ، لینک باید به سایت دیپلوی‌شده اشاره کند نه localhost"
    assert 'new URLSearchParams(location.search).get("code")' in js
    assert "openSharedChartFromUrl();" in js
    call_site = js.index("renderVolatility();\n    openSharedChartFromUrl();")
    assert call_site > 0, "بعد از رسیدن قیمت‌ها باید لینک را باز کند"
    assert "openChart(found);" in js and "history.replaceState" in js


# --- ترجمه‌ها -------------------------------------------------------------------


def test_every_i18n_key_used_in_the_ui_exists_in_all_languages(html, js):
    blocks = i18n_blocks(js)
    assert set(blocks) == {"fa", "en", "ar"}

    used = set(re.findall(r'data-i18n(?:-placeholder|-aria)?="([^"]+)"', html))
    used |= set(re.findall(r'\bt\("([^"]+)"\)', js))
    assert len(used) > 60, "کلیدهای ترجمه کم‌تر از حد انتظار است"

    for lang, keys in blocks.items():
        missing = sorted(k for k in used if k not in keys)
        assert missing == [], f"کلیدهای بدون ترجمه در «{lang}»: {missing}"

    sizes = {lang: len(keys) for lang, keys in blocks.items()}
    assert len(set(sizes.values())) == 1, f"تعداد کلیدها بین زبان‌ها یکی نیست: {sizes}"
