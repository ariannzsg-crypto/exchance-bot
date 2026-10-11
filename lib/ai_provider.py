"""کلاینت هوش مصنوعی — چند ارائه‌دهنده با زنجیره‌ی جانشینی.

دلیل وجود این ساختار: سرویس عمومیِ `AI_*` (top-tools-ai) کلیدش با اپ‌های دیگر
هم‌استفاده می‌شود و وقتی ظرفیتش پر شود خطای 503 «طلب در صف پر است» می‌دهد. اگر
تنها راه همین باشد، چتِ کاربر با کلید دیگری می‌خوابد. پس هر ارائه‌دهنده‌ای که کلید
اختصاصی‌اش ست شده باشد، **قبل از** سرویس عمومی امتحان می‌شود:

    ۱. Mistral   → MISTRAL_API_KEY      (پلن Free بدون کارت بانکی، فارسی در فهرست زبان‌ها)
    ۲. Groq      → GROQ_API_KEY         (استنتاج سریع، سازگار با OpenAI)
    ۳. Gemini    → GEMINI_API_KEY       (پلن رایگان AI Studio)
    ۴. سرویس عمومی AI_*                 (آخرین تلاش سازگار با OpenAI + مدل‌های جانشین)

هر ارائه‌دهنده‌ی OpenAI-compatible با MODEL/BASE_URL خودش قابل بازنویسی است
(`MISTRAL_MODEL`, `GROQ_BASE_URL` و …)، پس اگر شناسه‌ی مدل عوض شد فقط یک متغیر
محیطی تغییر می‌کند و نیازی به دست‌زدن به کد نیست.

زمان پاسخ (اندازه‌گیری ۲۰۲۶-۱۰-۱۱ روی سرویس عمومی، پاسخ تک‌توکنی):
    Top-Tools-Ai     ~۷۸ ثانیه  ← از سقف ۶۰s فانکشن ورسل رد می‌شود
    MiniMax-M3       ~۵۲ ثانیه
    Step-5-Preview   ~۲۳ ثانیه
    DeepSeek-V4.1-Flash ~۲۰ ثانیه
بنابراین کل بودجه‌ی زمانی محدود شده (AI_TOTAL_BUDGET) و مدل اول کوتاه‌ترین سهم را دارد.

⚠ خطاهای 429 و 503 موقتی‌اند: یک بار کوتاه صبر می‌کنیم و همان ارائه‌دهنده را دوباره
می‌زنیم، بعد به ارائه‌دهنده‌ی بعدی می‌رویم.

همه‌ی کلیدها فقط از متغیرهای محیطی خوانده می‌شوند و هیچ کلیدی در کد نیست:
    MISTRAL_API_KEY / MISTRAL_BASE_URL / MISTRAL_MODEL
    GROQ_API_KEY    / GROQ_BASE_URL    / GROQ_MODEL
    GEMINI_API_KEY  / GEMINI_MODEL
    AI_API_KEY / AI_BASE_URL / AI_MODEL / AI_FALLBACK_MODELS
    AI_MAX_TOKENS / AI_TOTAL_BUDGET / AI_FIRST_ATTEMPT
"""

from __future__ import annotations

import os
import time

import requests

# ===== سرویس عمومی (سازگار با OpenAI) =====
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://top-tools-ai.com/api/v1").rstrip("/")
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "DeepSeek-V4.1-Flash").strip()
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "700"))
AI_TOTAL_BUDGET = float(os.environ.get("AI_TOTAL_BUDGET", "55"))
AI_FIRST_ATTEMPT = float(os.environ.get("AI_FIRST_ATTEMPT", "45"))

# ===== Gemini (ساختار درخواست متفاوت) =====
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_BASE_URL = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-flash-latest"]

# ===== ارائه‌دهنده‌های اختصاصی (فقط وقتی کلیدشان ست باشد فعال می‌شوند) =====
EXTRA_PROVIDERS = [
    {
        "name": "mistral",
        "key_env": "MISTRAL_API_KEY",
        "base_env": "MISTRAL_BASE_URL",
        "model_env": "MISTRAL_MODEL",
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
    },
    {
        "name": "groq",
        "key_env": "GROQ_API_KEY",
        "base_env": "GROQ_BASE_URL",
        "model_env": "GROQ_MODEL",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
    },
]


def _generic_models() -> list[str]:
    raw = os.environ.get("AI_FALLBACK_MODELS", "Step-5-Preview,GLM-5.3-Flash")
    models = [m.strip() for m in raw.split(",") if m.strip()]
    return [AI_MODEL] + [m for m in models if m != AI_MODEL]


def _gemini_models() -> list[str]:
    explicit = os.environ.get("GEMINI_MODEL", "").strip()
    return [explicit] if explicit else list(GEMINI_FALLBACK_MODELS)


def provider_chain() -> list[dict]:
    """ارائه‌دهنده‌های قابل استفاده، به ترتیب اولویت.

    کلیدهای اختصاصی جلوترند تا یک سرویس شلوغِ مشترک، چت را از کار نیندازد.
    """
    chain: list[dict] = []

    for provider in EXTRA_PROVIDERS:
        key = os.environ.get(provider["key_env"], "").strip()
        if not key:
            continue
        chain.append({
            "name": provider["name"],
            "kind": "openai",
            "api_key": key,
            "base_url": os.environ.get(provider["base_env"], provider["base_url"]).rstrip("/"),
            "model": os.environ.get(provider["model_env"], provider["model"]),
        })

    if GEMINI_KEY:
        for model in _gemini_models():
            chain.append({"name": "gemini", "kind": "gemini",
                          "api_key": GEMINI_KEY, "model": model})

    if AI_API_KEY:
        for model in _generic_models():
            chain.append({"name": "top-tools", "kind": "openai",
                          "api_key": AI_API_KEY, "base_url": AI_BASE_URL, "model": model})

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


def _call_openai_compatible(provider: dict, messages: list[dict], timeout: float) -> str:
    resp = requests.post(
        f"{provider['base_url']}/chat/completions",
        headers={
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json",
        },
        json={
            "model": provider["model"],
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


def _call_gemini(model: str, system: str, messages: list[dict], timeout: float) -> str:
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    resp = requests.post(
        f"{GEMINI_BASE_URL}/models/{model}:generateContent",
        headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "topP": 0.95, "maxOutputTokens": 1024},
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise _HTTPError(resp.status_code, resp.text)

    candidates = resp.json().get("candidates") or []
    parts = (candidates[0].get("content", {}) or {}).get("parts", []) if candidates else []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("پاسخ خالی از مدل")
    return text


def _call(provider: dict, system: str, messages: list[dict], timeout: float) -> str:
    if provider["kind"] == "gemini":
        return _call_gemini(provider["model"], system, messages, timeout)
    return _call_openai_compatible(provider, messages, timeout)


def ai_chat(message: str, history=None, lang: str = "fa", market_ctx: str = "") -> dict:
    """پاسخ کوتاه بازار محور به پیام کاربر.

    خروجی همیشه با قرارداد فرانت‌اند سازگار است:
        {"success": True,  "reply": "...", "ai_powered": True, "provider": "...", "model": "..."}
        {"success": False, "message": "...", "debug": "..."}
    """
    chain = provider_chain()
    if not chain:
        return {
            "success": True,
            "ai_powered": False,
            "reply": "⚠️ سرویس AI فعال نیست. یکی از کلیدها (MISTRAL_API_KEY یا AI_API_KEY) را "
                     "در متغیرهای محیطی تنظیم کن.",
        }

    messages = _build_messages(message, history, lang, market_ctx)
    system = messages[0]["content"]

    started = time.time()
    errors: list[str] = []

    for index, provider in enumerate(chain):
        label = f"{provider['name']}/{provider['model']}"
        for attempt in (1, 2):
            remaining = AI_TOTAL_BUDGET - (time.time() - started)
            if remaining < 8:
                errors.append(f"{label}: بودجه‌ی زمانی تمام شد")
                break
            budget = min(AI_FIRST_ATTEMPT if index == 0 else remaining, remaining)
            try:
                reply = _call(provider, system, messages, budget)
                if reply:
                    return {
                        "success": True,
                        "reply": reply,
                        "ai_powered": True,
                        "provider": provider["name"],
                        "model": provider["model"],
                        "latency_ms": int((time.time() - started) * 1000),
                    }
            except Exception as exc:  # noqa: BLE001 - پیام مناسب باید به کاربر برسد
                errors.append(f"{label}: {str(exc)[:80]}")
                # 429 و 503 موقتی‌اند: یک بار کوتاه صبر و همان ارائه‌دهنده را دوباره می‌زنیم
                if getattr(exc, "status", 0) in (429, 503) and attempt == 1:
                    pause = min(6.0, max(0.0, AI_TOTAL_BUDGET - (time.time() - started) - 12))
                    if pause >= 2:
                        time.sleep(pause)
                        continue
                break

    slow = (time.time() - started) >= AI_TOTAL_BUDGET - 2
    overloaded = any(("queue is temporarily full" in err) or (" 503" in err) for err in errors)
    if slow:
        message_out = "⏱ پاسخ مدل طول کشید و نیمه‌کاره ماند. یک بار دیگر بپرس."
    elif overloaded:
        message_out = "🚦 سرویس هوش مصنوعی همین حالا شلوغ است. چند لحظه بعد دوباره بپرس."
    else:
        message_out = "❌ سرویس هوش مصنوعی پاسخ نداد."
    return {
        "success": False,
        "message": message_out,
        "debug": " | ".join(errors[-2:]),
    }
