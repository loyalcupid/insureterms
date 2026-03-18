import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import AppHandler, search_all


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/search", "/search"}:
            self.send_error(404)
            return

        query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
        if not query:
            AppHandler.send_json(self, {"error": "query is required"}, status=400)
            return

        AppHandler.send_json(self, search_all(query))

