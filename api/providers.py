import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import AppHandler, INSURER_REGISTRY


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/providers", "/providers"}:
            self.send_error(404)
            return

        payload = {
            "providers": [
                {"key": key, "name": value["name"], "officialUrl": value["official_url"], "type": value["type"]}
                for key, value in INSURER_REGISTRY.items()
            ]
        }
        AppHandler.send_json(self, payload)

