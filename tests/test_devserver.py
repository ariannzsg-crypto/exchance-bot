"""تست سرور محلی توسعه (`python -m _preview.devserver`).

سرور محلی تنها راهِ دیدن سریع UI است، پس باید همان مسیرهایی را بشناسد که ورسل
می‌شناسد: بازنویسی `fear-greed`، `cleanUrls` و «هیچ فایلی بیرون از web/».
اینجا واقعاً یک سرور روی لوپ‌بک بالا می‌آید و از راه HTTP تست می‌شود؛ فقط
اندپوینت‌هایی که به اینترنت نیاز دارند صدا زده نمی‌شوند.
"""

import os
import socket
import subprocess
import sys
import threading
import time
from http.server import ThreadingHTTPServer

import pytest

from _helpers import ROOT, request

from _preview import devserver


@pytest.fixture(scope="module")
def base_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), devserver.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# --- قرارداد با README ---------------------------------------------------------


def test_readme_command_points_at_a_real_module():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m _preview.devserver" in readme, "README باید همان دستور موجود را بگوید"
    assert (ROOT / "_preview" / "devserver.py").is_file()
    assert (ROOT / "_preview" / "__init__.py").is_file(), "بدون __init__ دستور -m کار نمی‌کند"


# --- مسیریابی ------------------------------------------------------------------


def test_api_paths_map_to_the_real_vercel_handlers():
    for name, module in devserver.API_MODULES.items():
        assert devserver.api_module_for("/api/" + name) == module
        assert devserver.api_module_for("/api/" + name + "?x=1") == module
    # همان rewriteی که در vercel.json هست
    assert devserver.api_module_for("/api/fear-greed") == "api.fear_greed"
    for path in ("/api", "/api/", "/api/nope", "/app.js", "/"):
        assert devserver.api_module_for(path) is None


def test_static_lookup_stays_inside_web_and_understands_clean_urls():
    assert devserver.static_file_for("/").name == "index.html"
    assert devserver.static_file_for("/app.js").name == "app.js"
    assert devserver.static_file_for("/index").name == "index.html"
    assert devserver.static_file_for("/manifest.json").name == "manifest.json"
    # خروج از web/ ممنوع است — هم ساده و هم کدشده
    for escape in ("/../lib/currencies.py", "/%2e%2e/lib/currencies.py", "/..%2flib%2fcurrencies.py"):
        assert devserver.static_file_for(escape) is None, escape
    # فایلی که در ریپو هست ولی در web/ نیست
    assert devserver.static_file_for("/lib/currencies.py") is None


# --- HTTP واقعی -----------------------------------------------------------------


def test_server_serves_the_frontend_over_http(base_url):
    page = request(base_url + "/")
    assert page.status == 200
    assert "text/html" in page.headers.get("Content-Type", "")
    assert 'id="splash"' in page.body

    script = request(base_url + "/app.js")
    assert script.status == 200
    assert "javascript" in script.headers.get("Content-Type", "")
    assert script.body == (ROOT / "web" / "app.js").read_text(encoding="utf-8")


def test_unknown_paths_and_escapes_are_404_not_leaks(base_url):
    for path in ("/nope", "/api/nope", "/../lib/currencies.py", "/lib/currencies.py"):
        resp = request(base_url + path)
        assert resp.status == 404, path
        assert "CURRENCIES" not in resp.body, path


def test_head_requests_do_not_send_a_body(base_url):
    resp = request(base_url + "/app.js", method="HEAD")
    assert resp.status == 200
    assert resp.body == ""


def test_documented_command_actually_starts_on_a_legacy_windows_console():
    """همان دستوری که README می‌گوید، با کنسول cp1252 ویندوز بالا بیاید.

    رگرسیون واقعی: چاپ پرچم/فارسی روی cp1252 باعث UnicodeEncodeError و مرگ
    سرور می‌شد.
    """
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    env = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "_preview.devserver", "--port", str(port)],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    try:
        for _ in range(120):
            if proc.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    break
            except OSError:
                time.sleep(0.25)
        assert proc.poll() is None, "سرور با کنسول cp1252 بالا نیامد:\n" + (proc.stdout.read() or "")
        assert request(f"http://127.0.0.1:{port}/").status == 200
    finally:
        proc.terminate()
        try:
            out = proc.communicate(timeout=10)[0]
        except subprocess.TimeoutExpired:
            proc.kill()
            out = proc.communicate(timeout=10)[0]
    assert "UnicodeEncodeError" not in (out or "")
