from http.server import BaseHTTPRequestHandler
import json
from lib.ai_provider import ai_chat
from lib.market_data import get_market

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            message = (body.get("message") or "").strip()[:800]

            if not message:
                self.send_response(400)
                self.end_headers()
                return

            # ساخت context قیمت‌ها
            market = get_market()
            priority = ["usd", "eur", "gbp", "gold18", "gold24",
                        "btc", "eth", "ton", "usdt", "sol"]
            ctx = []
            for c in priority:
                it = market.get(c)
                if it and it.get("price"):
                    ctx.append(f"• {it['name']}: {int(it['price']):,} تومان")

            result = ai_chat(
                message=message,
                history=body.get("history") or [],
                lang=body.get("lang") or "fa",
                market_ctx="\n".join(ctx),
            )

            data = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if result.get("success") else 500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            print("AI ERR:", e)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "message": "خطا"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()