"""کلاینت هوش مصنوعی — سازگار با OpenAI (`/chat/completions`).

پیش‌فرض روی سرویس Top-Tools-Ai تنظیم است و در صورت خطا/کندی،
مدل‌های جانشین و در نهایت Gemini (اختیاری) امتحان می‌شوند.

نکته‌ی مهم درباره‌ی زمان پاسخ (اندازه‌گیری مجدد ۲۰۲۶-۱۰-۱۱، پاسخ تک‌توکنی):
    Top-Tools-Ai     ~۷۸ ثانیه  ← از سقف ۶۰s فانکشن ورسل رد می‌شود؛ فقط با تنظیم دستی AI_MODEL
    MiniMax-M3       ~۵۲ ثانیه
    Step-5-Preview   ~۲۳ ثانیه
    DeepSeek-V4.1-Flash ~۲۰ ثانیه  ← پیش‌فرض (سریع‌ترین اندازه‌گیری‌شده)
    بنابراین کل بودجه‌ی زمانی محدود شده و مدل پیش‌فرض سریع‌ترین مدل همان کلید است.

    ⚠ سرویس روی هر کلید هم‌زمانی محدودی دارد (خطای 429) و درخواست قطع‌شده را تا انتها
    پردازش می‌کند؛ پس زنجیره‌ی فالبک فقط وقتی جواب می‌دهد که تلاش اول خیلی زود خطا بدهد.

    ⚠ اگر کلید هم‌زمان جای دیگری هم استفاده شود، دروازه‌ی سرویس خطای 503 با متن
    «The request queue is temporarily full» می‌دهد. این خطا موقتی است، پس مثل 429
    یک بار کوتاه صبر می‌کنیم و دوباره می‌زنیم و پیام شفاف‌تری به کاربر می‌دهیم.

همه‌ی کلیدها فقط از متغیرهای محیطی خوانده می‌شوند و هیچ کلیدی در کد نیست:

    AI_API_KEY            (اجباری برای سرویس اصلی)
    AI_BASE_URL           پیش‌فرض: https://top-tools-ai.com/api/v1
    AI_MODEL              پیش‌فرض: DeepSeek-V4.1-Flash
    AI_FALLBACK_MODELS    پیش‌فرض: Step-5-Preview,GLM-5.3-Flash
    AI_MAX_TOKENS         پیش‌فرض: 700
    AI_TOTAL_BUDGET       پیش‌فرض: 55 (ثانیه، باید < maxDuration باشد)
    AI_FIRST_ATTEMPT      پیش‌فرض: 45 (بودجه‌ی تلاش اول)
    GEMINI_API_KEY        اختیاری، فقط به عنوان پشتیبان
"""

from __future__ import annotations

import os
import time

import requests

AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://top-tools-ai.com/api/v1").rstrip("/")
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "DeepSeek-V4.1-Flash").strip()
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "700"))
AI_TOTAL_BUDGET = float(os.environ.get("AI_TOTAL_BUDGET", "55"))
AI_FIRST_ATTEMPT = float(os.environ.get("AI_FIRST_ATTEMPT", "45"))

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-flash-latest"]


def _fallback_models() -> list[str]:
    raw = os.environ.get("AI_FALLBACK_MODELS", "Step-5-Preview,GLM-5.3-Flash")
    models = [m.strip() for m in raw.split(",") if m.strip()]
    chain = [AI_MODEL] + [m for m in models if m != AI_MODEL]
    return chain


SYSTEM = """تو یک دستیار حرفه‌ای و صمیمی در مورد بازار ارز، طلا و رمزارز ایران هستی.
- کوتاه و مفید (۳ تا ۶ جمله)
- از ایموجی استفاده کن
- هرگز تضمین قیمت نکن
- اگر داده‌ی لحظه‌ای در پیام نیست، حدس نزن و بگو که قیمت لحظه‌ای در دسترس نیست
"""


def _lang_instruction(lang: str) -> str:
    return {
        "fa": "به فارسی جواب بده.",
        "en": "Answer in English.",
        "ar": "أجب بالعربية.",
    }.get(lang, "به فارسی جواب بده.")


def _build_messages(message: str, history, lang: str, market_ctx: str) -> list[dict]:
    system = SYSTEM + "\n\n" + _lang_instruction(lang)
    if market_ctx:
        system += "\n\n📊 قیمت‌های لحظه‌ای:\n" + market_ctx

    messages = [{"role": "system", "content": system}]
    for h in (history or [])[-6:]:
        role = "user" if h.get("role") == "user" else "assistant"
        content = (h.get("content") or "")[:400]
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})
    return messages


class _HTTPError(RuntimeError):
    def __init__(self, status: int, text: str):
        super().__init__(f"HTTP {status}: {text[:120]}")
        self.status = status


def _call_openai_compatible(model: str, messages: list[dict], timeout: float) -> str:
    if not AI_API_KEY:
        raise RuntimeError("AI_API_KEY تنظیم نشده است")

    resp = requests.post(
        f"{AI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": AI_MAX_TOKENS,
            "temperature": 0.7,
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise _HTTPError(resp.status_code, resp.text)

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("پاسخ خالی از مدل")
    return (choices[0].get("message") or {}).get("content", "").strip()


def _call_gemini(system: str, messages: list[dict], timeout: float) -> str:
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    errors = []
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_KEY}"
        try:
            resp = requests.post(
                url,
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": contents,
                    "generationConfig": {"temperature": 0.7, "topP": 0.95, "maxOutputTokens": 1024},
                },
                timeout=timeout,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            cands = resp.json().get("candidates") or []
            parts = (cands[0].get("content", {}) or {}).get("parts", []) if cands else []
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text
            raise RuntimeError("خالی")
        except Exception as exc:  # noqa: BLE001 - خطای هر مدل جداگانه جمع می‌شود
            errors.append(f"{model}: {str(exc)[:60]}")
    raise RuntimeError(" | ".join(errors[-2:]) or "gemini failed")


def ai_chat(message: str, history=None, lang: str = "fa", market_ctx: str = "") -> dict:
    """پاسخ کوتاه بازار محور به پیام کاربر.

    خروجی همیشه با قرارداد فرانت‌اند سازگار است:
        {"success": True,  "reply": "...", "ai_powered": True}
        {"success": False, "message": "...", "debug": "..."}
    """
    if not AI_API_KEY and not GEMINI_KEY:
        return {
            "success": True,
            "ai_powered": False,
            "reply": "⚠️ سرویس AI فعال نیست. کلید AI_API_KEY را در متغیرهای محیطی تنظیم کن.",
        }

    messages = _build_messages(message, history, lang, market_ctx)
    system = messages[0]["content"]

    started = time.time()
    errors: list[str] = []
    chain = _fallback_models()

    for index, model in enumerate(chain):
        for attempt in (1, 2):
            remaining = AI_TOTAL_BUDGET - (time.time() - started)
            if remaining < 8 or not AI_API_KEY:
                errors.append(f"{model}: بودجه‌ی زمانی تمام شد")
                break
            budget = min(AI_FIRST_ATTEMPT if index == 0 else remaining, remaining)
            try:
                reply = _call_openai_compatible(model, messages, budget)
                if reply:
                    return {
                        "success": True,
                        "reply": reply,
                        "ai_powered": True,
                        "model": model,
                        "latency_ms": int((time.time() - started) * 1000),
                    }
            except Exception as exc:  # noqa: BLE001 - برای برگرداندن پیام مناسب به کاربر
                errors.append(f"{model}: {str(exc)[:80]}")
                # سرویس سقف هم‌زمانی دارد («Try again shortly»)؛ یک بار کوتاه صبر و دوباره می‌زنیم
                if getattr(exc, "status", 0) in (429, 503) and attempt == 1:
                    pause = min(6.0, max(0.0, AI_TOTAL_BUDGET - (time.time() - started) - 12))
                    if pause >= 2:
                        time.sleep(pause)
                        continue
                break

    # پشتیبان اختیاری: Gemini
    remaining = AI_TOTAL_BUDGET - (time.time() - started)
    if GEMINI_KEY and remaining > 8:
        try:
            reply = _call_gemini(system, messages, remaining)
            if reply:
                return {"success": True, "reply": reply, "ai_powered": True, "model": "gemini-fallback"}
        except Exception as exc:  # noqa: BLE001
            errors.append(f"gemini: {str(exc)[:80]}")

    slow = (time.time() - started) >= AI_TOTAL_BUDGET - 2
    overloaded = any("queue is temporarily full" in err or "503" in err for err in errors)
    if slow:
        message = "⏱ پاسخ مدل طول کشید و نیمه‌کاره ماند. یک بار دیگر بپرس."
    elif overloaded:
        message = "🚦 سرویس هوش مصنوعی همین حالا شلوغ است. چند لحظه بعد دوباره بپرس."
    else:
        message = "❌ سرویس هوش مصنوعی پاسخ نداد."
    return {
        "success": False,
        "message": message,
        "debug": " | ".join(errors[-2:]),
    }
