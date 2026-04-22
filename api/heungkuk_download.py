import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import AppHandler, HeungkukAdapter


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/heungkuk_download", "/api/heungkuk-download", "/heungkuk_download", "/heungkuk-download"}:
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        seq = params.get("seq", [""])[0].strip()
        doc = params.get("doc", ["terms"])[0].strip() or "terms"
        if not seq:
            AppHandler.send_json(self, {"error": "seq is required"}, status=400)
            return

        try:
            body, filename = HeungkukAdapter.download_document(seq, doc)
        except Exception as exc:
            AppHandler.send_json(self, {"error": str(exc)}, status=502)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
