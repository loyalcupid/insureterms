import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import AigAdapter, AppHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/download/aig", "/download/aig"}:
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        product_code = params.get("productCode", [""])[0].strip()
        file_id = params.get("fileId", [""])[0].strip() or None
        file_seq = params.get("fileSeq", ["1"])[0].strip() or "1"
        original_name = params.get("name", ["aig.pdf"])[0].strip() or "aig.pdf"
        if not product_code:
            AppHandler.send_json(self, {"error": "productCode is required"}, status=400)
            return

        try:
            body, filename, content_type = AigAdapter.download_document(product_code, file_id, file_seq, original_name)
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
