from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8123
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"

INSURER_REGISTRY = {
    "kb": {
        "name": "KB손해보험",
        "aliases": ["kb", "케이비", "kb손해보험", "kb손보", "국민"],
        "type": "live",
        "official_url": "https://www.kbinsure.co.kr/CG802030001.ecs",
    },
    "db": {
        "name": "DB손해보험",
        "aliases": ["db", "db손해보험", "db손보", "동부화재"],
        "type": "live",
        "official_url": "https://www.idbins.com/FWMAIV1535.do",
    },
    "lotte": {
        "name": "롯데손해보험",
        "aliases": ["롯데", "롯데손해보험", "롯데손보"],
        "type": "landing",
        "official_url": "https://www.lotteins.co.kr",
    },
    "hyundai": {
        "name": "현대해상",
        "aliases": ["현대해상", "현대", "하이카"],
        "type": "landing",
        "official_url": "https://www.hi.co.kr",
    },
    "samsung": {
        "name": "삼성화재",
        "aliases": ["삼성화재", "삼성"],
        "type": "landing",
        "official_url": "https://www.samsungfire.com",
    },
    "meritz": {
        "name": "메리츠화재",
        "aliases": ["메리츠화재", "메리츠", "메리츠손보"],
        "type": "landing",
        "official_url": "https://www.meritzfire.com",
    },
    "hanwha": {
        "name": "한화생명",
        "aliases": ["한화생명", "한화"],
        "type": "landing",
        "official_url": "https://www.hanwhalife.com",
    },
    "kyobo": {
        "name": "교보생명",
        "aliases": ["교보생명", "교보"],
        "type": "landing",
        "official_url": "https://www.kyobo.com",
    },
}

GENERIC_TERMS = ["보험", "약관", "상품", "요약서", "사업방법서", "다운로드", "찾기", "검색", "공시실"]


def clean_html(value: str) -> str:
    return (
        re.sub(r"<[^>]+>", "", value or "")
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .strip()
    )


def clean_date(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip().replace(".", "")
    if len(text) != 8 or not text.isdigit():
        return None
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}"


def extract_href(fragment: str) -> str | None:
    match = re.search(r'href="([^"]+)"', fragment)
    return match.group(1) if match else None


def normalize_text(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())


def tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"\s+", value.strip()) if token]


def score_text(query: str, *values: str) -> int:
    normalized_query = normalize_text(query)
    score = 0
    for value in values:
        normalized_value = normalize_text(value)
        if not normalized_value:
            continue
        if normalized_query and normalized_query in normalized_value:
            score += 12
        for token in tokenize(query):
            normalized_token = normalize_text(token)
            if normalized_token and normalized_token in normalized_value:
                score += 4
    return score


def unique_by(items: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    output: list[dict[str, Any]] = []
    for item in items:
        signature = tuple(item.get(key) for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        output.append(item)
    return output


def build_query_variants(query: str) -> list[str]:
    base = query.strip()
    if not base:
        return []
    compact = base.replace(" ", "")
    variants = [base, compact]
    variants.extend(tokenize(base))
    if len(compact) >= 2:
        variants.append(compact[:2])
    if len(compact) >= 3:
        variants.append(compact[:3])
    if len(compact) >= 4:
        variants.append(compact[:4])

    ordered: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        cleaned = variant.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def fetch_url(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def fetch_text(
    url: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    encoding: str = "utf-8",
) -> str:
    return fetch_url(url, method=method, data=data, headers=headers).decode(encoding, errors="ignore")


@dataclass
class SearchContext:
    raw_query: str
    insurer_key: str | None
    insurer_name: str | None
    product_query: str


def parse_query(raw_query: str) -> SearchContext:
    lowered = raw_query.lower()
    insurer_key = None
    insurer_name = None
    cleaned = raw_query
    for key, config in INSURER_REGISTRY.items():
        aliases = sorted(config["aliases"], key=len, reverse=True)
        for alias in aliases:
            if alias.lower() in lowered:
                insurer_key = key
                insurer_name = config["name"]
                cleaned = re.sub(re.escape(alias), " ", cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(re.escape(config["name"]), " ", cleaned, flags=re.IGNORECASE)
                break
        if insurer_key:
            break
    product_query = cleaned
    for term in GENERIC_TERMS:
        product_query = product_query.replace(term, " ")
    product_query = re.sub(r"\s+", " ", product_query).strip() or raw_query.strip()
    return SearchContext(raw_query.strip(), insurer_key, insurer_name, product_query)


class KbAdapter:
    base = "https://www.kbinsure.co.kr"
    search_url = f"{base}/CG802030001.ecs"
    detail_url = f"{base}/CG802030002.ec"

    @classmethod
    def search(cls, query: str, limit: int = 5) -> list[dict[str, Any]]:
        aggregated: list[dict[str, Any]] = []
        for variant in build_query_variants(query):
            aggregated.extend(cls.search_once(variant))
            if len(aggregated) >= limit * 4:
                break

        ranked = sorted(
            unique_by(aggregated, "productCode", "productName"),
            key=lambda item: (-score_text(query, item["productName"], item["insuranceType"], item["productCode"]), item["productName"]),
        )

        enriched = []
        for item in ranked[:limit]:
            docs = cls.fetch_detail(item["detailParams"])
            item["documents"] = docs
            item["saleStartDate"] = docs[0]["saleStartDate"] if docs else None
            item["saleEndDate"] = docs[-1]["saleEndDate"] if docs else None
            item["updatedAt"] = docs[-1]["saleStartDate"] if docs else None
            item["officialSource"] = "KB손해보험 상품목록(약관)"
            item["score"] = score_text(query, item["productName"], item["insuranceType"], item["productCode"])
            enriched.append(item)
        return enriched

    @classmethod
    def search_once(cls, query: str) -> list[dict[str, Any]]:
        params = {
            "devonTargetRow": "1",
            "devonOrderBy": "",
            "gubun": "",
            "goodsNm": query,
            "onsaleYn": "",
            "bojongNo": "",
            "bojongSeq": "",
            "search_onsale_yn": "",
            "search_bojong_no": "",
            "search_gubun": "",
            "search_goods_nm": query,
        }
        body = urllib.parse.urlencode(params, encoding="euc-kr").encode("ascii")
        html = fetch_text(
            cls.search_url,
            method="POST",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            encoding="euc-kr",
        )
        rows = re.findall(
            r"<tr>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td class=\"tx_lt thnone\"><a href=\"javascript:detail\('([^']+)','([^']+)','([^']+)'\);\">(.*?)</a>",
            html,
            re.S,
        )
        results = []
        for sale_text, insurance_type, product_code, bojong_no, gubun, bojong_seq, product_name in rows:
            results.append(
                {
                    "provider": "kb",
                    "insurerName": "KB손해보험",
                    "productName": clean_html(product_name),
                    "productCode": product_code.strip(),
                    "insuranceType": clean_html(insurance_type),
                    "status": "판매중" if "판매중지" not in sale_text else "판매중지",
                    "sourceUrl": cls.search_url,
                    "detailParams": {"bojongNo": bojong_no, "gubun": gubun, "bojongSeq": bojong_seq},
                    "score": score_text(query, product_name, insurance_type, product_code),
                }
            )
        return results

    @classmethod
    def fetch_detail(cls, detail_params: dict[str, str]) -> list[dict[str, Any]]:
        body = urllib.parse.urlencode(detail_params, encoding="euc-kr").encode("ascii")
        html = fetch_text(
            cls.detail_url,
            method="POST",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            encoding="euc-kr",
        )
        pattern = re.compile(
            r"<tr>\s*<td class=\"vfont_s02\">(.*?)</td>\s*<td class=\"vfont_s02\">(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>\s*<td>(.*?)</td>",
            re.S,
        )
        docs = []
        for sale_start, sale_end, terms_html, biz_html, summary_html in pattern.findall(html):
            for doc_type, href in [
                ("보험약관", extract_href(terms_html)),
                ("사업방법서", extract_href(biz_html)),
                ("상품요약서", extract_href(summary_html)),
            ]:
                if not href:
                    continue
                docs.append(
                    {
                        "type": doc_type,
                        "title": doc_type,
                        "url": urllib.parse.urljoin(cls.base, href),
                        "revisionDate": clean_date(sale_start),
                        "saleStartDate": clean_date(sale_start),
                        "saleEndDate": clean_date(sale_end),
                        "format": "PDF",
                    }
                )
        return docs


class DbAdapter:
    base = "https://www.idbins.com"
    search_url = f"{base}/insuPcPbanFindProductStep5_AX.do"

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        aggregated: list[dict[str, Any]] = []
        for variant in build_query_variants(query):
            aggregated.extend(cls.search_once(variant))
            if len(aggregated) >= limit * 6:
                break

        ranked = sorted(
            unique_by(aggregated, "productCode", "productName"),
            key=lambda item: (-score_text(query, item["productName"], item["insuranceType"]), item["productName"]),
        )
        for item in ranked:
            item["score"] = score_text(query, item["productName"], item["insuranceType"])
        return ranked[:limit]

    @classmethod
    def search_once(cls, query: str) -> list[dict[str, Any]]:
        payload = json.dumps(
            {"searchCheck": "0", "keyword": query, "beginDate": "", "endDate": ""},
            ensure_ascii=False,
        ).encode("utf-8")
        raw = fetch_text(
            cls.search_url,
            method="POST",
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest"},
            encoding="utf-8",
        )
        parsed = json.loads(raw)
        results = []
        for item in parsed.get("result", []):
            product_name = item.get("PDC_NM", "").strip()
            if not product_name:
                continue
            documents = []
            for key, doc_type in [
                ("INPL_FINM", "보험약관"),
                ("BIZ_MDDC_FINM", "사업방법서"),
                ("CNSL_SMAR_FINM", "상품요약서"),
                ("PDC_EXPP_FINM", "상품설명서"),
            ]:
                filename = item.get(key)
                if not filename:
                    continue
                documents.append(
                    {
                        "type": doc_type,
                        "title": doc_type,
                        "url": f"{cls.base}/cYakgwanDown.do?FilePath=InsProduct/{urllib.parse.quote(filename)}",
                        "revisionDate": item.get("SALE_BEGIN_DAY"),
                        "saleStartDate": item.get("SALE_BEGIN_DAY"),
                        "saleEndDate": item.get("SALE_END_DAY"),
                        "format": "PDF",
                    }
                )
            results.append(
                {
                    "provider": "db",
                    "insurerName": "DB손해보험",
                    "productName": product_name,
                    "productCode": str(item.get("SQNO", "")),
                    "insuranceType": item.get("ARC_KND_LGCG_NM", ""),
                    "status": "판매중" if item.get("ARC_PDC_SL_YN") == "1" else "판매중지",
                    "sourceUrl": "https://www.idbins.com/FWMAIV1535.do",
                    "documents": documents,
                    "saleStartDate": item.get("SALE_BEGIN_DAY"),
                    "saleEndDate": item.get("SALE_END_DAY"),
                    "updatedAt": item.get("SALE_BEGIN_DAY"),
                    "officialSource": "DB손해보험 상품목록 및 기초서류(보험약관)",
                    "score": score_text(query, product_name, item.get("ARC_KND_LGCG_NM", "")),
                }
            )
        return results


def landing_result(provider_key: str, query: str) -> list[dict[str, Any]]:
    config = INSURER_REGISTRY[provider_key]
    return [
        {
            "provider": provider_key,
            "insurerName": config["name"],
            "productName": query,
            "productCode": "",
            "insuranceType": "",
            "status": "공식 공시실 이동",
            "sourceUrl": config["official_url"],
            "documents": [],
            "saleStartDate": None,
            "saleEndDate": None,
            "updatedAt": None,
            "officialSource": f"{config['name']} 공식 사이트",
            "score": 1,
            "notice": "이 보험사는 현재 공식 공시실 랜딩 연결만 구성되어 있습니다. 전용 크롤러 어댑터를 추가하면 약관 직접 수집이 가능합니다.",
        }
    ]


def search_all(raw_query: str) -> dict[str, Any]:
    context = parse_query(raw_query)
    provider_keys = [context.insurer_key] if context.insurer_key else ["kb", "db"]
    results = []
    errors = []
    for provider_key in provider_keys:
        try:
            if provider_key == "kb":
                results.extend(KbAdapter.search(context.product_query))
            elif provider_key == "db":
                results.extend(DbAdapter.search(context.product_query))
            else:
                results.extend(landing_result(provider_key, context.product_query))
        except Exception as exc:
            errors.append({"provider": INSURER_REGISTRY[provider_key]["name"], "message": str(exc)})

    ranked = sorted(
        results,
        key=lambda item: (-item.get("score", 0), 0 if item.get("status") == "판매중" else 1, item.get("productName", "")),
    )
    return {
        "query": raw_query,
        "parsedInsurer": context.insurer_name,
        "parsedProduct": context.product_query,
        "resultCount": len(ranked),
        "results": ranked[:20],
        "errors": errors,
        "generatedAt": int(time.time()),
    }


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "time": int(time.time())})
            return
        if parsed.path == "/api/providers":
            self.send_json(
                {
                    "providers": [
                        {"key": key, "name": value["name"], "officialUrl": value["official_url"], "type": value["type"]}
                        for key, value in INSURER_REGISTRY.items()
                    ]
                }
            )
            return
        if parsed.path == "/api/search":
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip()
            if not query:
                self.send_json({"error": "query is required"}, status=400)
                return
            self.send_json(search_all(query))
            return
        self.serve_static(parsed.path)

    def serve_static(self, path: str) -> None:
        target = "index.html" if path in {"/", ""} else path.lstrip("/")
        file_path = (BASE_DIR / target).resolve()
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(file_path.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def run() -> None:
    port = int(os.environ.get("PORT", PORT))
    server = ThreadingHTTPServer((HOST, port), AppHandler)
    print(f"Serving on http://{HOST}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
