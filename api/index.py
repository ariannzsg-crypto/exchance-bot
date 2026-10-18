"""نقطه‌ی ورود پایتون برای ورسل — entrypoint در «مکان پیش‌فرض».

چرا این فایل وجود دارد؟
    وقتی ورسل پروژه را با preset پایتون می‌سازد، entrypoint را فقط در این
    مکان‌ها جست‌وجو می‌کند:

        app.py, index.py, server.py, main.py, wsgi.py, asgi.py
        در ریشه، یا داخل src/ ، app/ و api/

    و اگر پیدا نکند با خطای PYTHON_ENTRYPOINT_NOT_FOUND می‌میرد، حتی اگر
    همه‌ی api/*.py سالم باشند (دقیقاً همان خطایی که دیدیم).

    api/index.py خودش یکی از همان مکان‌های پیش‌فرض است، پس هر دو مدل ساخت
    ورسل را پوشش می‌دهد:

      • مدل فایلی (هر api/*.py یک فانکشن جدا): اینجا فقط مسیر /api/index را
        سرو می‌کند و بقیه‌ی مسیرها سرِ جای خودشان می‌روند.
      • مدل «پایتون به‌عنوان فریمورک» (کل ترافیک /api به entrypoint می‌رسد):
        درخواست را به همان handler واقعیِ همان اندپوینت می‌سپارد؛ مسیر، کد
        وضعیت، هدرها و قرارداد JSON دقیقاً همان چیزی می‌ماند که خودِ api/*.py
        می‌فرستد.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

# ریشه‌ی پروژه باید روی sys.path باشد تا import شدنِ api.* و lib.* (که خودِ
# اندپوینت‌ها به آن تکیه دارند) در هر دو حالت بالا یکسان جواب بدهد.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from api import chart as chart_api                # noqa: E402
from api import fear_greed as fear_greed_api       # noqa: E402
from api import history as history_api            # noqa: E402
from api import market as market_api              # noqa: E402
from api import news as news_api                  # noqa: E402

# مسیر → کلاس handler واقعیِ همان اندپوینت.
# «fear-greed» هم اینجا است چون rewrite داخل vercel.json در مدل فریمورکی
# اعمال نمی‌شود؛ در مدل فایلی همان rewrite کار خودش را می‌کند.
ROUTES = {
    "/api/market": market_api.handler,
    "/api/history": history_api.handler,
    "/api/news": news_api.handler,
    "/api/chart": chart_api.handler,
    "/api/fear_greed": fear_greed_api.handler,
    "/api/fear-greed": fear_greed_api.handler,
}


class handler(BaseHTTPRequestHandler):
    """ورودی پذیرفته‌شده‌ی ورسل: یک BaseHTTPRequestHandler با نام `handler`."""

    server_version = "ExchanceIndex/1.0"

    def do_GET(self):
        path = urlparse(self.path).path
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        if path in ("/api", "/api/index"):
            self._json(200, {
                "success": True,
                "endpoints": sorted(ROUTES),
            })
            return

        target = ROUTES.get(path)
        if target is None:
            self._json(404, {"success": False, "error": "unknown endpoint"})
            return

        # متد را روی نمونه‌ای از خودِ کلاس اندپوینت اجرا می‌کنیم، نه روی این
        # نمونه: اندپوینت‌ها متدهای کمکی خودشان را دارند (`_json` در history و
        # fear_greed) و اگر self از کلاس دیگری باشد، آن کمکی‌ها پیدا نمی‌شوند
        # و درخواست با AttributeError می‌میرد.
        endpoint = target.__new__(target)
        endpoint.__dict__.update(self.__dict__)
        endpoint.do_GET()
        self.__dict__.update(endpoint.__dict__)   # close_connection و وضعیت اتصال

    def _json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
