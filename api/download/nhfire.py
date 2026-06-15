import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import AppHandler, NhFireLiveAdapter


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/download/nhfire", "/download/nhfire"}:
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        product_code = params.get("pdtCd", [""])[0].strip()
        file_id = params.get("fileId", [""])[0].strip()
        seq = params.get("seq", [""])[0].strip()
        preferred_name = params.get("name", ["nhfire.pdf"])[0].strip() or "nhfire.pdf"
        if not product_code or not seq:
            AppHandler.send_json(self, {"error": "pdtCd and seq are required"}, status=400)
            return

        try:
            body, filename, content_type = NhFireLiveAdapter.download_document(product_code, seq, preferred_name, file_id)
        except Exception as exc:
            AppHandler.send_json(self, {"error": str(exc)}, status=502)
            return

        guessed_type = mimetypes.guess_type(filename)[0] or content_type or "application/pdf"
        self.send_response(200)
        self.send_header("Content-Type", guessed_type)
        self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
