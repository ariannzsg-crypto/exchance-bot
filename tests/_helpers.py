"""ابزارهای مشترک تست.

اندپوینت‌ها همان کلاس `handler` واقعیِ ورسل هستند و روی لوپ‌بک اجرا می‌شوند،
بنابراین کد مسیر/پاسخ/CORS واقعاً تست می‌شود — بدون هیچ درخواست بیرونی.
"""

import contextlib
import importlib
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@contextlib.contextmanager
def serve(module_name):
    """ماژول اندپوینت را روی یک پورت آزاد لوپ‌بک سرو می‌کند و آدرس پایه را می‌دهد."""
    module = importlib.import_module(module_name)
    server = ThreadingHTTPServer(("127.0.0.1", 0), module.handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    def json(self):
        return json.loads(self.body)


def request(url, method="GET", payload=None, timeout=20):
    """درخواست HTTP واقعی به سرور تست؛ حتی پاسخ ۵۰۰ هم به‌جای استثنا برگردانده می‌شود."""
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return Response(resp.status, dict(resp.headers), resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return Response(exc.code, dict(exc.headers or {}), exc.read().decode("utf-8"))
