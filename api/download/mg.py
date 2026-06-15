import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler

from server import AppHandler, MgAdapter


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path not in {"/api/download/mg", "/download/mg"}:
            self.send_error(404)
            return

        params = urllib.parse.parse_qs(parsed.query)
        data_id = params.get("dataIdno", [""])[0].strip()
        doc_cfcd = params.get("docCfcd", [""])[0].strip()
        sale_flag = params.get("saleYn", ["0"])[0].strip() or "0"
        original_name = params.get("name", ["mg.pdf"])[0].strip() or "mg.pdf"
        if not data_id or not doc_cfcd:
            AppHandler.send_json(self, {"error": "dataIdno and docCfcd are required"}, status=400)
            return

        try:
            body, filename, content_type = MgAdapter.download_document(data_id, doc_cfcd, sale_flag, original_name)
        except Exception as exc:
            AppHandler.send_json(self, {"error": str(exc)}, status=502)
            return

        guessed_type = mimetypes.guess_type(filename)[0] or content_type or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", guessed_type)
        self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
