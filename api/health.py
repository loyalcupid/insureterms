from http.server import BaseHTTPRequestHandler

from server import AppHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        AppHandler.send_json(self, {"ok": True})

