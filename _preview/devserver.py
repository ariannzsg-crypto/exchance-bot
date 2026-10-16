"""سرور محلی توسعه: همان چیزی که ورسل اجرا می‌کند، روی لوپ‌بک.

چرا این فایل وجود دارد؟ چون `api/*.py` عمداً هیچ منطقی خارج از کلاس `handler`
ندارند (ورسل همین را صدا می‌زند). اینجا همان کلاس‌های واقعی صدا زده می‌شوند —
هیچ کدی تکرار نمی‌شود — و فایل‌های `web/` هم کنارشان سرو می‌شوند. یعنی:

    python -m _preview.devserver

بعد مرورگر را روی http://127.0.0.1:8811 باز کن. تفاوتش با `vercel dev` این است
که به CLI و لاگین ورسل نیازی ندارد و فقط برای دیدن سریع UI محلی است.

نکته: بازنویسی `/api/fear-greed` → `/api/fear_greed` که در `vercel.json` است
اینجا هم اعمال می‌شود تا آدرس‌ها دقیقاً مثل پروداکشن کار کنند.
"""

from __future__ import annotations

import argparse
import importlib
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# نامی که در آدرس می‌آید → ماژول واقعیِ ورسل
API_MODULES = {
    "market": "api.market",
    "news": "api.news",
    "history": "api.history",
    "chart": "api.chart",
    "fear_greed": "api.fear_greed",
}

# همان rewriteهای vercel.json
API_ALIASES = {"fear-greed": "fear_greed"}

DEFAULT_PORT = 8811


def api_module_for(path: str) -> str | None:
    """`/api/history?days=7` → «api.history»؛ اگر مسیر اندپوینت نباشد None.

    تابع خالص است تا بدون باز کردن سوکت هم قابل تست باشد.
    """
    parts = [p for p in urlparse(path).path.strip("/").split("/") if p]
    if len(parts) < 2 or parts[0] != "api":
        return None
    name = API_ALIASES.get(parts[1], parts[1])
    return API_MODULES.get(name)


def static_file_for(path: str) -> Path | None:
    """مسیر URL → فایل داخل web/ (یا None اگر بیرون از web/ باشد).

    مثل `cleanUrls` ورسل، `/charts` را هم به `charts.html` وصل می‌کند.
    """
    rel = unquote(urlparse(path).path).lstrip("/")
    candidate = (WEB / rel).resolve()
    if WEB.resolve() not in candidate.parents and candidate != WEB.resolve():
        return None
    if candidate.is_dir():
        candidate = candidate / "index.html"
    if candidate.is_file():
        return candidate
    if not candidate.suffix:
        html = candidate.with_suffix(".html")
        if html.is_file():
            return html
    return None


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.0 عمدی است: هندلرهای ورسل همه‌جا Content-Length نمی‌گذارند و روی
    # keep-alive مرورگر منتظر ادامه‌ی پاسخ می‌ماند. با بستن اتصال، مرورگر پاسخ را
    # بر اساس EOF می‌بندد — همان کاری که ورسل هم پشت صحنه می‌کند.
    protocol_version = "HTTP/1.0"
    server_version = "exchance-devserver"

    def log_message(self, fmt, *args):  # لاگ تمیزتر از پیش‌فرض
        sys.stderr.write("  %s %s\n" % (self.command, self.path))

    # --- API: دقیقاً همان کلاس‌های ورسل -------------------------------------
    def _delegate_api(self, module_name: str, method: str) -> bool:
        module = importlib.import_module(module_name)
        target = getattr(module.handler, method, None)
        if target is None:
            return False
        target(self)          # self همان هندلر است؛ فقط منطق از ماژول می‌آید
        return True

    # --- استاتیک ------------------------------------------------------------
    def _send_static(self, path: str, head_only: bool = False):
        target = static_file_for(path)
        if target is None:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            return

        body = target.read_bytes()
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # در توسعه هیچ‌چیز کش نشود تا ویرایش‌ها فوری دیده شوند
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def do_GET(self):
        module_name = api_module_for(self.path)
        if module_name:
            if self._delegate_api(module_name, "do_GET"):
                return
        self._send_static(self.path)

    def do_HEAD(self):
        self._send_static(self.path, head_only=True)

    def do_OPTIONS(self):
        module_name = api_module_for(self.path)
        if module_name:
            module = importlib.import_module(module_name)
            if getattr(module.handler, "do_OPTIONS", None) is not None:
                self._delegate_api(module_name, "do_OPTIONS")
                return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        module_name = api_module_for(self.path)
        if module_name and self._delegate_api(module_name, "do_POST"):
            return
        self.send_response(405)
        self.send_header("Content-Length", "0")
        self.end_headers()


def _force_utf8_console():
    """کنسول ویندوز اغلب cp1252 است؛ لاگ‌های فارسی و پرچم‌ها آنجا خطا می‌دهند.

    بدون این کار، همین دستور مستندشده (`python -m _preview.devserver`) روی
    ویندوز با UnicodeEncodeError می‌میرد — و پیام‌های خودِ اندپوینت‌ها هم می‌توانند
    برنامه را زمین بزنند.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):   # جریان گرفته‌شده یا غیرقابل تنظیم
            pass


def main(argv=None) -> int:
    _force_utf8_console()
    parser = argparse.ArgumentParser(description="EXCHANCE — local dev server")
    parser.add_argument("-p", "--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    # flush=True واجب است: وقتی خروجی به فایل لاگ می‌رود، چاپ بافر می‌شود و
    # «آدرس را باز کن» تا پایان پروسه دیده نمی‌شود.
    print(f"EXCHANCE devserver -> http://{args.host}:{server.server_address[1]}/", flush=True)
    print("  endpoints: " + ", ".join("/api/" + k for k in API_MODULES), flush=True)
    print("  static:    " + str(WEB), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
