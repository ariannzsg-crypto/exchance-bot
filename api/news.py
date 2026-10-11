from http.server import BaseHTTPRequestHandler
import json
from lib.news_scraper import get_news

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            data = get_news()
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=300")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print("NEWS ERR:", e)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode())