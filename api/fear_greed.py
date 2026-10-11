from http.server import BaseHTTPRequestHandler
import json
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
            d = (r.json().get("data") or [{}])[0]
            result = {
                "success": True,
                "data": {
                    "value": int(d.get("value", 50)),
                    "classification": d.get("value_classification", "Neutral"),
                },
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}

        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)