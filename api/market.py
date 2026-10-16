from http.server import BaseHTTPRequestHandler
import json
from lib.market_data import get_market
from lib.currencies import CURRENCIES

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            market = get_market()
            currencies = []
            for code, info in CURRENCIES.items():
                item = market.get(code)
                if not item:
                    continue
                currencies.append({
                    "code": code, "name": item["name"], "short": item["short"],
                    "flag": item["flag"], "price": item["price"],
                    "change": item.get("change", 0),
                    "unit": item.get("unit", "تومان"),
                    "source": item.get("source"), "type": item.get("type"),
                    "group": item.get("group", item.get("type")),
                    "usd_price": item.get("usd_price"),
                })

            body = json.dumps({
                "success": True, "bot": "EXCHANCE",
                "source": "TGJU + CoinGecko", "currencies": currencies,
            }, ensure_ascii=False).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=10")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print("MARKET ERR:", e)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()