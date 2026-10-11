from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlencode, urlparse, parse_qs
from lib.market_data import get_market

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("code", [""])[0]).lower()
            theme = q.get("theme", ["light"])[0]

            market = get_market()
            item = market.get(code)
            if not item:
                self.send_response(404)
                self.end_headers()
                return

            change = float(item.get("change", 0) or 0)
            color = "16a86a" if change >= 0 else "e0455a"

            config = {
                "type": "line",
                "data": {
                    "labels": list(range(20)),
                    "datasets": [{
                        "data": [50 + (i * change / 10) + (i % 3) for i in range(20)],
                        "borderColor": "#" + color,
                        "backgroundColor": "#" + color + "40",
                        "borderWidth": 3, "fill": True,
                        "pointRadius": 0, "tension": 0.4,
                    }],
                },
                "options": {
                    "plugins": {"legend": {"display": False}},
                    "scales": {"x": {"display": False}, "y": {"display": False}},
                },
            }

            url = "https://quickchart.io/chart?" + urlencode({
                "c": json.dumps(config),
                "w": "600", "h": "350",
                "bkg": "0e0a1e" if theme == "dark" else "f8f5ff",
            })

            body = json.dumps({"success": True, "chart_url": url}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()