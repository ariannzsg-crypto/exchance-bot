"""تست زنجیره‌ی ارائه‌دهنده‌های هوش مصنوعی.

هیچ تماس شبکه‌ای انجام نمی‌شود: `requests.post` و `time.sleep` جعل می‌شوند تا هم
ترتیب جانشینی و هم تعداد تلاش‌ها دقیقاً قابل اندازه‌گیری باشد.
"""

import importlib
import os

import pytest

import lib.ai_provider as ai

KEY_ENVS = ("MISTRAL_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY", "AI_API_KEY")
ALL_ENVS = KEY_ENVS + ("MISTRAL_MODEL", "MISTRAL_BASE_URL", "GROQ_MODEL", "GROQ_BASE_URL",
                       "GEMINI_MODEL", "AI_MODEL", "AI_FALLBACK_MODELS",
                       "AI_TOTAL_BUDGET", "AI_FIRST_ATTEMPT")


@pytest.fixture
def load():
    """ماژول را با متغیرهای محیطی دلخواه دوباره بارگذاری می‌کند و در پایان پاک می‌کند."""
    original = {k: os.environ.get(k) for k in ALL_ENVS}

    def _load(**env):
        for key in ALL_ENVS:
            os.environ.pop(key, None)
        os.environ.update({k: str(v) for k, v in env.items()})
        return importlib.reload(ai)

    yield _load

    for key in ALL_ENVS:
        os.environ.pop(key, None)
    for key, value in original.items():
        if value is not None:
            os.environ[key] = value
    importlib.reload(ai)


class FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def reply_payload(text="سلام از مدل"):
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture
def calls(monkeypatch):
    """جایگزین requests.post: صف پاسخ‌ها را به ترتیب مصرف می‌کند و درخواست‌ها را ثبت می‌کند."""
    recorded = {"requests": [], "responses": []}

    def fake_post(url, headers=None, json=None, timeout=None):
        recorded["requests"].append({"url": url, "headers": headers, "json": json,
                                     "timeout": timeout})
        if not recorded["responses"]:
            return FakeResp(200, reply_payload())
        nxt = recorded["responses"].pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    monkeypatch.setattr(ai.requests, "post", fake_post)
    monkeypatch.setattr(ai.time, "sleep", lambda seconds: recorded.setdefault("sleeps", []).append(seconds))
    return recorded


# --- زنجیره‌ی ارائه‌دهنده‌ها -------------------------------------------------------


def test_no_keys_means_no_ai_but_still_a_friendly_answer(load):
    module = load()
    assert module.provider_chain() == []
    result = module.ai_chat("سلام")
    assert result["success"] is True
    assert result["ai_powered"] is False
    assert "MISTRAL_API_KEY" in result["reply"]


def test_dedicated_keys_come_before_the_shared_public_service(load):
    module = load(MISTRAL_API_KEY="m-key", GROQ_API_KEY="g-key",
                  GEMINI_API_KEY="gem-key", AI_API_KEY="shared")
    chain = module.provider_chain()
    assert [p["name"] for p in chain] == ["mistral", "groq", "gemini", "gemini", "top-tools",
                                          "top-tools", "top-tools"]
    assert chain[0]["model"] == "mistral-small-latest"
    assert chain[0]["base_url"] == "https://api.mistral.ai/v1"
    assert chain[1]["model"] == "llama-3.3-70b-versatile"
    assert chain[-1]["name"] == "top-tools"


def test_only_providers_with_a_key_are_used(load):
    module = load(GROQ_API_KEY="g-key")
    assert [p["name"] for p in module.provider_chain()] == ["groq"]
    assert module.provider_chain()[0]["model"] == "llama-3.3-70b-versatile"


def test_model_and_base_url_are_overridable_by_env(load):
    module = load(MISTRAL_API_KEY="m-key", MISTRAL_MODEL="mistral-large-latest",
                  MISTRAL_BASE_URL="https://proxy.example/v1/", GROQ_API_KEY="g")
    chain = module.provider_chain()
    assert chain[0]["model"] == "mistral-large-latest"
    assert chain[0]["base_url"] == "https://proxy.example/v1"   # اسلش انتهایی حذف می‌شود


def test_single_gemini_model_env_replaces_the_default_pair(load):
    module = load(GEMINI_API_KEY="k", GEMINI_MODEL="gemini-2.5-pro")
    assert [p["model"] for p in module.provider_chain()] == ["gemini-2.5-pro"]


# --- جانشینی و تلاش دوباره ---------------------------------------------------------


def test_when_the_first_provider_fails_the_next_one_answers(load, calls):
    module = load(MISTRAL_API_KEY="m", GROQ_API_KEY="g")
    calls["responses"] = [FakeResp(500, {}, "boom"), FakeResp(200, reply_payload("از گروک"))]

    result = module.ai_chat("قیمت دلار؟")

    assert result["success"] is True
    assert result["reply"] == "از گروک"
    assert result["provider"] == "groq"
    assert result["model"] == "llama-3.3-70b-versatile"
    urls = [r["url"] for r in calls["requests"]]
    assert urls == ["https://api.mistral.ai/v1/chat/completions",
                    "https://api.groq.com/openai/v1/chat/completions"]


def test_queue_full_is_retried_once_on_the_same_provider(load, calls):
    module = load(MISTRAL_API_KEY="m")
    queue_full = FakeResp(503, {"error": {"message": "The request queue is temporarily full. "
                                                    "Please try again shortly."}},
                          "queue full")
    calls["responses"] = [queue_full, FakeResp(200, reply_payload("بالاخره جواب داد"))]

    result = module.ai_chat("سلام")

    assert result["success"] is True
    assert len(calls["requests"]) == 2          # دو تلاش روی همان ارائه‌دهنده
    assert calls["requests"][0]["url"] == calls["requests"][1]["url"]
    assert calls["sleeps"] == [pytest.approx(6.0)]   # مکث کوتاه بین دو تلاش


def test_rate_limit_is_retried_once_too(load, calls):
    module = load(GROQ_API_KEY="g")
    calls["responses"] = [FakeResp(429, {}, "slow down"), FakeResp(200, reply_payload("ok"))]

    result = module.ai_chat("سلام")

    assert result["success"] is True
    assert len(calls["requests"]) == 2


def test_hard_failures_do_not_waste_a_retry(load, calls):
    module = load(MISTRAL_API_KEY="m", GROQ_API_KEY="g")
    calls["responses"] = [FakeResp(401, {}, "bad key"), FakeResp(200, reply_payload("ok"))]

    result = module.ai_chat("سلام")

    assert result["success"] is True
    assert len(calls["requests"]) == 2                       # 401 بی‌درنگ رد شد
    assert calls["requests"][1]["url"].startswith("https://api.groq.com")
    assert calls.get("sleeps", []) == []                     # بدون مکث بی‌فایده


def test_saturated_service_gets_its_own_user_message(load, calls):
    module = load(AI_API_KEY="shared", AI_MODEL="only-model", AI_FALLBACK_MODELS="")
    calls["responses"] = [FakeResp(503, {}, "queue is temporarily full"),
                          FakeResp(503, {}, "queue is temporarily full")]

    result = module.ai_chat("سلام")

    assert result["success"] is False
    assert "شلوغ" in result["message"]
    assert result["debug"]


def test_other_failures_get_the_generic_message(load, calls):
    module = load(AI_API_KEY="shared", AI_MODEL="only-model", AI_FALLBACK_MODELS="")
    calls["responses"] = [FakeResp(403, {}, "<html>403</html>"), FakeResp(403, {}, "<html>403</html>")]

    result = module.ai_chat("سلام")

    assert result["success"] is False
    assert "شلوغ" not in result["message"]
    assert "پاسخ نداد" in result["message"]


def test_running_out_of_time_is_reported_as_slow(load, calls, monkeypatch):
    module = load(MISTRAL_API_KEY="m", AI_TOTAL_BUDGET=10, AI_FIRST_ATTEMPT=8)
    clock = {"t": 0.0}

    def ticking():
        clock["t"] += 5.0
        return clock["t"]

    monkeypatch.setattr(module.time, "time", ticking)
    calls["responses"] = [FakeResp(500, {}, "boom")]

    result = module.ai_chat("سلام")

    assert result["success"] is False
    assert "طول کشید" in result["message"]


def test_empty_model_reply_moves_to_the_next_provider(load, calls):
    module = load(MISTRAL_API_KEY="m", GROQ_API_KEY="g")
    calls["responses"] = [FakeResp(200, {"choices": []}), FakeResp(200, reply_payload("دومی"))]

    result = module.ai_chat("سلام")

    assert result["reply"] == "دومی"
    assert result["provider"] == "groq"
    assert len(calls["requests"]) == 2


def test_empty_reply_from_the_only_provider_is_reported_clearly(load, calls):
    module = load(MISTRAL_API_KEY="m")
    calls["responses"] = [FakeResp(200, {"choices": []})]

    result = module.ai_chat("سلام")

    assert result["success"] is False
    assert "پاسخ نداد" in result["message"]
    assert "پاسخ خالی" in result["debug"]
    assert len(calls["requests"]) == 1          # پاسخ خالی، تلاش دوباره‌ی گران‌قیمت نمی‌ارزد


# --- شکل درخواست ------------------------------------------------------------------


def test_openai_compatible_request_shape(load, calls):
    module = load(MISTRAL_API_KEY="m-key", AI_MAX_TOKENS=123)
    calls["responses"] = [FakeResp(200, reply_payload())]

    module.ai_chat("قیمت دلار؟", history=[{"role": "user", "content": "سلام"}],
                   lang="fa", market_ctx="دلار آمریکا: 264,305 تومان")

    sent = calls["requests"][0]
    assert sent["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer m-key"
    assert sent["json"]["model"] == "mistral-small-latest"
    assert sent["json"]["stream"] is False
    assert sent["json"]["max_tokens"] == 123
    roles = [m["role"] for m in sent["json"]["messages"]]
    assert roles == ["system", "user", "user"]
    assert "264,305 تومان" in sent["json"]["messages"][0]["content"]


def test_gemini_request_shape(load, calls):
    module = load(GEMINI_API_KEY="gem-key", GEMINI_MODEL="gemini-2.5-flash")
    calls["responses"] = [FakeResp(200, {"candidates": [{"content": {"parts": [{"text": "جواب"}]}}]})]

    result = module.ai_chat("سلام", lang="en")

    sent = calls["requests"][0]
    assert sent["url"] == ("https://generativelanguage.googleapis.com/v1beta/models/"
                           "gemini-2.5-flash:generateContent")
    assert sent["headers"]["x-goog-api-key"] == "gem-key"
    assert sent["json"]["system_instruction"]["parts"][0]["text"].startswith("تو یک دستیار")
    assert "Answer in English" in sent["json"]["system_instruction"]["parts"][0]["text"]
    assert sent["json"]["contents"][0]["role"] == "user"
    assert result["provider"] == "gemini"


def test_gemini_rate_limit_is_also_retried(load, calls):
    module = load(GEMINI_API_KEY="k", GEMINI_MODEL="gemini-2.5-flash")
    calls["responses"] = [FakeResp(429, {}, "quota"),
                          FakeResp(200, {"candidates": [{"content": {"parts": [{"text": "دوم"}]}}]})]

    result = module.ai_chat("سلام")

    assert result["reply"] == "دوم"
    assert len(calls["requests"]) == 2


def test_history_is_trimmed_and_clipped(load, calls):
    module = load(MISTRAL_API_KEY="m")
    history = [{"role": "user", "content": f"پیام {i}"} for i in range(10)]
    history.append({"role": "user", "content": "x" * 900})
    calls["responses"] = [FakeResp(200, reply_payload())]

    module.ai_chat("آخرین", history=history)

    sent_messages = calls["requests"][0]["json"]["messages"]
    assert len(sent_messages) == 1 + 7            # system + ۶ پیام تاریخی + پیام کاربر
    assert len(sent_messages[-2]["content"]) == 400   # متن بلند بریده می‌شود
