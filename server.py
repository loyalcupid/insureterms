from __future__ import annotations

import json
import os
import re
import time
import http.cookiejar
import mimetypes
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
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
        "type": "live",
        "official_url": "https://www.lotteins.co.kr/web/C/D/H/cdh190.jsp",
    },
    "hyundai": {
        "name": "현대해상",
        "aliases": ["현대해상", "현대", "하이카"],
        "type": "live",
        "official_url": "https://children.hi.co.kr/bin/CI/ON/CION3200G.jsp",
    },
    "samsung": {
        "name": "삼성화재",
        "aliases": ["삼성화재", "삼성"],
        "type": "live",
        "official_url": "https://www.samsungfire.com/vh/page/VH.REIF0011.do",
    },
    "meritz": {
        "name": "메리츠화재",
        "aliases": ["메리츠화재", "메리츠", "메리츠손보"],
        "type": "live",
        "official_url": "https://store.meritzfire.com/disclosure/product.do",
    },
    "hanwhafire": {
        "name": "한화손해보험",
        "aliases": ["한화손해보험", "한화손보", "한화화재"],
        "type": "live",
        "official_url": "https://m.hwgeneralins.com/product/catalog/product-info.do",
    },
    "heungkuk": {
        "name": "흥국화재",
        "aliases": ["흥국화재", "흥국"],
        "type": "live",
        "official_url": "https://m.heungkukfire.co.kr/product/insr/CPDIS0001_M00/CPDIS0001_M00.do",
    },
    "nhfire": {
        "name": "NH농협손해보험",
        "aliases": ["nh농협손해보험", "nh농협", "농협손해보험", "농협손보", "nh손해보험", "nh손보"],
        "type": "live",
        "official_url": "https://www.nhfire.co.kr/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire",
    },
    "mg": {
        "name": "MG손해보험(예별손해보험)",
        "aliases": [
            "mg손해보험",
            "mg손보",
            "mg",
            "예별손해보험",
            "예별손보",
            "yebyeol",
            "mggeneral",
        ],
        "type": "live",
        "official_url": "https://www.yebyeol.co.kr/PB031210DM.scp?menuId=MN0803006",
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
    return re.sub(r"[^0-9a-z가-힣]", "", str(value or "").lower())


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


def filter_term_documents(item: dict[str, Any]) -> dict[str, Any] | None:
    documents = [doc for doc in (item.get("documents") or []) if doc.get("type") == "보험약관"]
    if not documents:
        return None
    filtered = dict(item)
    filtered["documents"] = documents
    return filtered


def product_name_matches_query(item: dict[str, Any], query: str) -> bool:
    normalized_query = normalize_text(query)
    product_name = normalize_text(item.get("productName", ""))
    if not normalized_query or not product_name:
        return False
    if normalized_query in product_name:
        return True
    query_tokens = [normalize_text(token) for token in tokenize(query) if normalize_text(token)]
    return bool(query_tokens) and all(token in product_name for token in query_tokens)


def name_recency_value(text: str | None) -> int:
    value = str(text or "")
    match = re.search(r"\((20\d{2})[.\-/](\d{2})\)", value)
    if match:
        return int(f"{match.group(1)}{match.group(2)}01")
    match = re.search(r"\((\d{2})[.\-/](\d{2})\)", value)
    if match:
        return int(f"20{match.group(1)}{match.group(2)}01")
    return 0


def recency_value(item: dict[str, Any]) -> int:
    candidates = [item.get("updatedAt"), item.get("saleStartDate")]
    candidates.extend(doc.get("revisionDate") or doc.get("saleStartDate") for doc in item.get("documents", []))
    for value in candidates:
        if not value:
            continue
        digits = re.sub(r"\D", "", str(value))[:8]
        if digits:
            return int(digits)
    fallback = name_recency_value(item.get("productName", ""))
    if fallback:
        return fallback
    return 0


def result_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        -recency_value(item),
        -item.get("score", 0),
        0 if item.get("status") == "판매중" else 1,
        item.get("productName", ""),
    )


def expanded_limit(limit: int, minimum: int = 20, maximum: int = 40) -> int:
    return min(max(limit, minimum), maximum)


def finalize_results(results: list[dict[str, Any]], query: str, limit: int = 20) -> list[dict[str, Any]]:
    ranked = sorted(results, key=result_sort_key)

    filtered: list[dict[str, Any]] = []
    for item in ranked:
        filtered_item = filter_term_documents(item)
        if not filtered_item:
            continue
        if not product_name_matches_query(filtered_item, query):
            continue
        filtered.append(filtered_item)

    return unique_by(filtered, "provider", "productCode", "productName")[:limit]


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


def strip_insurer_terms(query: str, insurer_key: str | None) -> str:
    if not insurer_key or insurer_key not in INSURER_REGISTRY:
        return query
    cleaned = query
    config = INSURER_REGISTRY[insurer_key]
    for alias in sorted([config["name"], *config["aliases"]], key=len, reverse=True):
        cleaned = re.sub(re.escape(alias), " ", cleaned, flags=re.IGNORECASE)
    return cleaned


def parse_query(raw_query: str, forced_insurer_key: str | None = None) -> SearchContext:
    insurer_key = forced_insurer_key if forced_insurer_key in INSURER_REGISTRY else None
    insurer_name = INSURER_REGISTRY[insurer_key]["name"] if insurer_key else None
    cleaned = strip_insurer_terms(raw_query, insurer_key)

    if not insurer_key:
        lowered = raw_query.lower()
        for key, config in INSURER_REGISTRY.items():
            aliases = sorted(config["aliases"], key=len, reverse=True)
            for alias in aliases:
                if alias.lower() in lowered:
                    insurer_key = key
                    insurer_name = config["name"]
                    cleaned = strip_insurer_terms(raw_query, insurer_key)
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
    page_size = 10

    @classmethod
    def search(cls, query: str, limit: int = 20) -> list[dict[str, Any]]:
        aggregated: list[dict[str, Any]] = []
        for variant in build_query_variants(query):
            target_row = 1
            while True:
                page_results = cls.search_once(variant, target_row=target_row)
                if not page_results:
                    break
                aggregated.extend(page_results)
                if len(page_results) < cls.page_size:
                    break
                if len(aggregated) >= limit * 8:
                    break
                target_row += cls.page_size
            if len(aggregated) >= limit * 8:
                break

        ranked = sorted(
            unique_by(aggregated, "productCode", "productName"),
            key=lambda item: result_sort_key(
                {
                    **item,
                    "score": score_text(query, item["productName"], item["insuranceType"], item["productCode"]),
                }
            ),
        )

        enriched = []
        for item in ranked[: expanded_limit(limit)]:
            docs = cls.fetch_detail(item["detailParams"])
            item["documents"] = docs
            item["saleStartDate"] = docs[0]["saleStartDate"] if docs else None
            item["saleEndDate"] = docs[-1]["saleEndDate"] if docs else None
            item["updatedAt"] = docs[-1]["saleStartDate"] if docs else None
            item["officialSource"] = "KB손해보험 상품목록(약관)"
            item["score"] = score_text(query, item["productName"], item["insuranceType"], item["productCode"])
            enriched.append(item)
        return sorted(enriched, key=result_sort_key)[:limit]

    @classmethod
    def search_once(cls, query: str, target_row: int = 1) -> list[dict[str, Any]]:
        params = {
            "devonTargetRow": str(target_row),
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


class HyundaiAdapter:
    base = "https://children.hi.co.kr"
    page_url = f"{base}/bin/CI/ON/CION3200G.jsp"
    ajax_url = f"{base}/ajax.xhi"

    DOC_TYPES = [
        ("clauApnflId", "보험약관"),
        ("userMthdApnflId", "사업방법서"),
        ("prodSmryApnflId", "상품요약서"),
        ("prodNoteApnflId", "상품설명서"),
    ]

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        aggregated = []
        for item in cls.fetch_catalog():
            item["score"] = score_text(query, item["productName"], item["insuranceType"], item["productCode"])
            if item["score"] > 0:
                aggregated.append(item)

        ranked = sorted(aggregated, key=result_sort_key)

        enriched: list[dict[str, Any]] = []
        for item in ranked[: expanded_limit(limit)]:
            documents = cls.fetch_documents(item["rawItem"], item["saleStartDate"], item["saleEndDate"])
            item["documents"] = documents
            enriched.append(item)
        return sorted(enriched, key=result_sort_key)[:limit]

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        payload = cls.make_request("HHCA0310M38S", {})
        response = cls.fetch_json(payload)
        results: list[dict[str, Any]] = []
        for sale_key in ["slYProdList", "slNProdList"]:
            for item in response.get("data", {}).get(sale_key, []):
                product_name = (item.get("prodNm") or "").strip()
                if not product_name:
                    continue
                sale_start = clean_hi_date(item.get("slStDt"))
                sale_end = clean_hi_date(item.get("slEdDt"))
                results.append(
                    {
                        "provider": "hyundai",
                        "insurerName": "현대해상",
                        "productName": product_name,
                        "productCode": str(item.get("repInsCd") or item.get("seqno") or ""),
                        "insuranceType": hi_product_category(item.get("prodCatCd")),
                        "status": "판매중" if item.get("slYn") == "Y" else "판매중지",
                        "sourceUrl": cls.page_url,
                        "documents": [],
                        "saleStartDate": sale_start,
                        "saleEndDate": sale_end,
                        "updatedAt": item.get("regDtm"),
                        "officialSource": "현대해상 보험상품공시",
                        "rawItem": item,
                    }
                )
        return results

    @classmethod
    def fetch_documents(cls, item: dict[str, Any], sale_start: str | None, sale_end: str | None) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for field_name, doc_type in cls.DOC_TYPES:
            apnfl_id = item.get(field_name)
            if not apnfl_id:
                continue
            file_info = cls.fetch_file_info(apnfl_id)
            file_ext = file_info.get("flExts") or "pdf"
            file_path = f"{file_info.get('savPath', '')}/{file_info.get('savFileNm', '')}.{file_ext}".replace("//", "/")
            documents.append(
                {
                    "type": doc_type,
                    "title": file_info.get("originalFileNm") or doc_type,
                    "url": f"{cls.base}/FileActionServlet/download/0{file_path}",
                    "previewUrl": f"{cls.base}/FileActionServlet/preview/0{file_path}",
                    "revisionDate": sale_start,
                    "saleStartDate": sale_start,
                    "saleEndDate": sale_end,
                    "format": (file_info.get("flExts") or "PDF").upper(),
                }
            )
        return documents

    @classmethod
    def fetch_file_info(cls, apnfl_id: str) -> dict[str, Any]:
        payload = cls.make_request("HHCA0310M26S", {"apnflId": apnfl_id})
        response = cls.fetch_json(payload)
        return response.get("data", {})

    @classmethod
    def fetch_json(cls, payload: dict[str, Any]) -> dict[str, Any]:
        raw = fetch_text(
            cls.ajax_url,
            method="POST",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Referer": cls.page_url,
            },
            encoding="utf-8",
        )
        return json.loads(raw)

    @classmethod
    def make_request(cls, tran_id: str, request_data: dict[str, Any]) -> dict[str, Any]:
        gid = f"codex{int(time.time() * 1000)}"
        return {
            "header": {
                "gId": gid,
                "tranId": tran_id,
                "channelId": "HI-HOME",
                "clientIp": "127.0.0.1",
                "menuId": "100221",
                "loginId": None,
            },
            "request": request_data,
        }


def hi_product_category(value: str | None) -> str:
    if not value:
        return ""
    prefix = value[:2]
    return {
        "01": "일반보험",
        "02": "자동차보험",
        "03": "장기보험",
        "04": "퇴직보험",
        "05": "퇴직연금",
    }.get(prefix, "기타")


def clean_hi_date(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^0-9]", "", value)
    if len(compact) < 8:
        return None
    return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"


class MeritzAdapter:
    base = "https://store.meritzfire.com"
    menu_url = f"{base}/menuList.do"
    json_url = f"{base}/json.smart"
    source_url = f"{base}/disclosure/product.do"

    DOC_TYPE_BY_CODE = {
        "6102": "보험약관",
        "6103": "상품요약서",
        "6104": "사업방법서",
    }

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        candidates = []
        for item in cls.fetch_products():
            score = score_text(query, item["productName"], item["productCode"], item.get("insuranceType", ""))
            if score <= 0:
                continue
            item["score"] = score
            candidates.append(item)

        ranked = sorted(candidates, key=result_sort_key)
        enriched = []
        for item in ranked[: expanded_limit(limit)]:
            item["documents"] = cls.fetch_documents(item["documentProductCode"])
            enriched.append(item)
        return sorted(enriched, key=result_sort_key)[:limit]

    @classmethod
    def fetch_products(cls) -> list[dict[str, Any]]:
        payload = cls.make_request("f.cg.de.cm.ce.o.bc.CnsTmBc.retrieveCnsTmInfo", {"tempCdObj": ["2", "4", "6", "5"]})
        response = cls.fetch_json(cls.json_url, payload)
        direct_products = response.get("body", {}).get("directPdMngList", [])
        menu_products = cls.fetch_menu_products()
        menu_by_code = {item.get("cmCommPdCd"): item for item in menu_products if item.get("cmCommPdCd")}

        results = []
        for item in direct_products:
            product_name = item.get("pdNm") or item.get("pdNmSt") or item.get("expoMenuNm")
            document_product_code = item.get("counselPdCd") or item.get("untPdCd")
            if not product_name or not document_product_code:
                continue
            menu_info = menu_by_code.get(item.get("mktCd")) or menu_by_code.get(item.get("counselPdCd")) or {}
            results.append(
                {
                    "provider": "meritz",
                    "insurerName": "메리츠화재",
                    "productName": product_name.strip(),
                    "productCode": str(item.get("pdCd") or item.get("mktCd") or ""),
                    "documentProductCode": str(document_product_code),
                    "insuranceType": item.get("pdNmSt") or "",
                    "status": "판매중",
                    "sourceUrl": urllib.parse.urljoin(cls.base, menu_info.get("linkUrl") or "/disclosure/product.do"),
                    "documents": [],
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "updatedAt": None,
                    "officialSource": "메리츠화재 상품/약관 공시",
                }
            )
        return unique_by(results, "documentProductCode", "productName")

    @classmethod
    def fetch_menu_products(cls) -> list[dict[str, Any]]:
        raw = fetch_text(cls.menu_url, method="POST", data=b"", headers={"Content-Type": "application/x-www-form-urlencoded"})
        return json.loads(raw).get("list", [])

    @classmethod
    def fetch_documents(cls, product_code: str) -> list[dict[str, Any]]:
        payload = cls.make_request("f.cg.he.ct.tm.o.bc.CtrCnfBc.retrievePdfFileLst", {"pdCd": product_code})
        response = cls.fetch_json(cls.json_url, payload)
        documents = []
        for item in response.get("body", {}).get("pdfList", []):
            doc_type = cls.DOC_TYPE_BY_CODE.get(item.get("cmAtcFileCtgCd"), "문서")
            encrypted_path = item.get("atcFilePthNm#[E]") or item.get("atcFilePthNm")
            original_name = item.get("ortxtFileNm") or item.get("atcFileNm") or f"{doc_type}.pdf"
            if not encrypted_path:
                continue
            params = urllib.parse.urlencode({"productCode": product_code, "name": original_name})
            documents.append(
                {
                    "type": doc_type,
                    "title": original_name,
                    "url": f"/api/download/meritz?{params}",
                    "revisionDate": None,
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "format": "PDF",
                }
            )
        return documents

    @classmethod
    def download_document(cls, product_code: str, original_name: str) -> tuple[bytes, str, str]:
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        headers = {"User-Agent": USER_AGENT}

        opener.open(urllib.request.Request(cls.source_url, headers=headers), timeout=30).read(128)
        payload = cls.make_request("f.cg.he.ct.tm.o.bc.CtrCnfBc.retrievePdfFileLst", {"pdCd": product_code})
        preflight_request = urllib.request.Request(
            cls.json_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                **headers,
                "Content-Type": "application/json; charset=UTF-8",
                "Referer": cls.source_url,
            },
        )
        preflight_response = json.loads(opener.open(preflight_request, timeout=30).read().decode("utf-8", errors="ignore"))
        pdf_items = preflight_response.get("body", {}).get("pdfList", [])
        encrypted_path = ""
        for item in pdf_items:
            candidate_name = item.get("ortxtFileNm") or item.get("atcFileNm")
            if candidate_name == original_name:
                encrypted_path = item.get("atcFilePthNm#[E]") or item.get("atcFilePthNm") or ""
                break

        if not encrypted_path:
            raise ValueError("Meritz document token could not be refreshed")

        params = urllib.parse.urlencode(
            {
                "path": encrypted_path,
                "id": encrypted_path,
                "orgFileName": original_name,
                "pdfView": "Y",
            }
        )
        download_url = f"{cls.base}/hp/fileDownload.do?{params}"
        request = urllib.request.Request(download_url, headers={**headers, "Referer": cls.source_url})
        with opener.open(request, timeout=30) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type", "application/pdf")

        if not body.startswith(b"%PDF"):
            raise ValueError("Meritz document download did not return a PDF")

        return body, original_name, content_type

    @classmethod
    def fetch_json(cls, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        raw = fetch_text(
            url,
            method="POST",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "Referer": cls.source_url,
            },
            encoding="utf-8",
        )
        return json.loads(raw)

    @classmethod
    def make_request(cls, service_id: str, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "header": {
                "encryDivCd": "0",
                "globId": "",
                "rcvmsgSrvId": service_id,
                "resultRcvmsgSrvId": "",
                "esbIntfId": "",
                "exsIntfId": "",
                "ipv6Addr1": "",
                "ipv6Addr2": "",
                "teleMsgMacAdr": "",
                "envirInfoDivCd": "",
                "firstTranssLcatgBizafairCd": "",
                "transsLcatgBizafairCd": "",
                "reqRespnsDivCd": "Q",
                "syncDivCd": "S",
                "teleMsgReqDttm": time.strftime("%Y%m%d%H%M%S") + "000",
                "prcesResultDivCd": "",
                "teleMsgRespnsDttm": "",
                "clienTrespnsDttm": "",
                "handcapLcatgBizafairCd": "",
                "teleMsgVerDivCd": "",
                "langDivCd": "KR",
                "belongGrpCd": "",
                "empNo": "",
                "empId": "",
                "dptCd": "",
                "hgrkDptCd": "",
                "nxupDptCd": "",
                "transGrpCd": "F",
                "screenId": "",
                "lowrnkScreenId": "",
                "resveLet": "",
            },
            "body": body,
        }


class LotteAdapter:
    base = "https://www.lotteins.co.kr"
    source_url = f"{base}/web/C/D/H/cdh190.jsp"
    channel_url = f"{base}/CChannelSvl"
    ops_tc = "dfi.c.d.g.cmd.Cdg079Cmd"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None
    _detail_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _detail_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _detail_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    CATEGORY_LABELS = {
        ("01", "01"): "\uac1c\uc778\uc6a9",
        ("01", "02"): "\uc5c5\ubb34\uc6a9",
        ("01", "03"): "\uc601\uc5c5\uc6a9",
        ("01", "04"): "\uc774\ub95c\ucc28",
        ("01", "05"): "\uc6b4\uc804\uc790",
        ("01", "06"): "\uc678\ud654\ud45c\uc2dc",
        ("01", "07"): "\ub18d\uae30\uacc4",
        ("01", "08"): "\uae30\ud0c0",
        ("01", "09"): "\uc6b4\uc804\uba74\ud5c8\uad50\uc2b5\uc0dd",
        ("01", "10"): "\ubaa8\ud130\ubc14\uc774\ud06c",
        ("01", "11"): "\uacf5\ub3d9\uc778\uc218",
        ("02", "01"): "\uc77c\ubc18\ubcf4\ud5d8",
        ("03", "01"): "\uc0c1\ud574,\uc9c8\ubcd1",
        ("03", "02"): "\uc800\ucd95",
        ("03", "03"): "\uc6b4\uc804\uc790",
        ("03", "04"): "\uc7ac\ubb3c\ubcf4\ud5d8",
        ("03", "05"): "\uc5f0\uae08\ubcf4\ud5d8",
        ("03", "06"): "\uc81c\ub3c4\uc131\ud2b9\uc57d",
        ("04", "01"): "\uacf5\ud1b5",
    }

    DOC_TYPE_LABELS = {
        "\uc0ac\uc5c5\ubc29\ubc95\uc11c": "\uc0ac\uc5c5\ubc29\ubc95\uc11c",
        "\uc0c1\ud488\uc694\uc57d\uc11c": "\uc0c1\ud488\uc694\uc57d\uc11c",
        "\ubcf4\ud5d8\uc57d\uad00": "\ubcf4\ud5d8\uc57d\uad00",
    }

    @classmethod
    def normalize_doc_type(cls, raw_type: str) -> str:
        label = clean_html(raw_type)
        if label in cls.DOC_TYPE_LABELS:
            return cls.DOC_TYPE_LABELS[label]
        if "\uc57d\uad00" in label:
            return "\ubcf4\ud5d8\uc57d\uad00"
        if "\uc694\uc57d" in label:
            return "\uc0c1\ud488\uc694\uc57d\uc11c"
        if "\uc0ac\uc5c5\ubc29\ubc95" in label:
            return "\uc0ac\uc5c5\ubc29\ubc95\uc11c"
        return label

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        categories = cls.parse_categories(fetch_text(cls.source_url, encoding="cp949"))
        keyword_matches: list[dict[str, Any]] = []
        for is_sale in [True, False]:
            for category in categories:
                keyword_matches.extend(cls.fetch_products(category["lcode"], category["mcode"], is_sale=is_sale, query=query))

        source_items = unique_by(keyword_matches, "status", "productCode", "productName") if keyword_matches else cls.fetch_catalog()
        for item in source_items:
            score = score_text(query, item["productName"], item.get("insuranceType", ""), item.get("productCode", ""))
            if score <= 0:
                continue
            ranked_item = dict(item)
            ranked_item["score"] = score
            candidates.append(ranked_item)

        ranked = sorted(
            unique_by(candidates, "status", "productCode", "productName"),
            key=lambda item: (-item["score"], 0 if item.get("status") == "\ud310\ub9e4\uc911" else 1, item["productName"]),
        )

        results: list[dict[str, Any]] = []
        for item in ranked:
            period_results = cls.fetch_period_results(item)
            if period_results:
                best_period = sorted(
                    period_results,
                    key=lambda period: (
                        0 if period.get("saleEndDate") is None else 1,
                        -(int((period.get("saleStartDate") or "0").replace("-", ""))),
                    ),
                )[0]
                best_period["score"] = item["score"]
                results.append(best_period)
            else:
                results.append(item)
            if len(results) >= expanded_limit(limit):
                break

        ranked_candidates = sorted(
            results,
            key=lambda item: (-item.get("score", 0), 0 if item.get("status") == "\ud310\ub9e4\uc911" else 1, item.get("productName", "")),
        )
        return ranked_candidates[:limit]
        return ranked_candidates[:limit]

        enriched_results = []
        for item in ranked_candidates[: expanded_limit(limit)]:
            detail = cls.get_product_detail(item["productCode"])
            enriched = dict(item)
            enriched.update(detail)
            enriched["score"] = score_text(
                query,
                enriched["productName"],
                enriched.get("insuranceType", ""),
                enriched.get("keywords", ""),
                " ".join(doc.get("type", "") for doc in enriched.get("documents", [])),
                enriched.get("productCode", ""),
            )
            enriched_results.append(enriched)

        ranked_candidates = sorted(
            unique_by(enriched_results, "productCode", "productName"),
            key=lambda item: (-item["score"], item["productName"]),
        )

        enriched_results = []
        for item in ranked_candidates[: expanded_limit(limit)]:
            detail = cls.get_product_detail(item["productCode"])
            enriched = dict(item)
            enriched.update(detail)
            enriched["score"] = score_text(
                query,
                enriched["productName"],
                enriched.get("insuranceType", ""),
                enriched.get("keywords", ""),
                " ".join(doc.get("type", "") for doc in enriched.get("documents", [])),
                enriched.get("productCode", ""),
            )
            enriched_results.append(enriched)

        return sorted(
            unique_by(enriched_results, "productCode", "productName"),
            key=lambda item: (-item["score"], item["productName"]),
        )[:limit]

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        cached = cls._catalog_cache
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        page_html = fetch_text(cls.source_url, encoding="cp949")
        categories = unique_by(cls.parse_categories(page_html), "lcode", "mcode")
        catalog: list[dict[str, Any]] = []
        for is_sale in [True, False]:
            for category in categories:
                catalog.extend(cls.fetch_products(category["lcode"], category["mcode"], is_sale=is_sale))

        deduped = unique_by(catalog, "status", "productCode", "productName")
        cls._catalog_cache = (now, deduped)
        return [dict(item) for item in deduped]

    @classmethod
    def parse_categories(cls, html: str) -> list[dict[str, str]]:
        categories = []
        for lcode, mcode in re.findall(r"step2\('([^']+)','([^']+)'(?:,\s*\d+,\s*\d+)?\);", html):
            categories.append({"lcode": lcode, "mcode": mcode})
        if categories:
            return unique_by(categories, "lcode", "mcode")
        return [{"lcode": lcode, "mcode": mcode} for lcode, mcode in cls.CATEGORY_LABELS.keys()]

    @classmethod
    def fetch_products(cls, lcode: str, mcode: str, *, is_sale: bool, query: str = "") -> list[dict[str, Any]]:
        task = "gostep2issale" if is_sale else "gostep2isnotsale"
        html = cls.post_form(
            {
                "ops_tc": cls.ops_tc,
                "task": task,
                "rtnUri": "/web/C/D/H/cdh190_result.jsp",
                "lcode": lcode,
                "mcode": mcode,
                "scode": "",
                "startdate": "",
                "issale": "Y" if is_sale else "N",
                "srcPrdNm": query,
            }
        )
        products: list[dict[str, Any]] = []
        for product_lcode, product_mcode, scode, product_name in re.findall(
            r"step3\('([^']+)','([^']+)','([^']+)'\)[^<]*<span>(.*?)</span>",
            html,
        ):
            name = clean_html(product_name)
            if not name:
                continue
            products.append(
                {
                    "provider": "lotte",
                    "insurerName": "\ub86f\ub370\uc190\ud574\ubcf4\ud5d8",
                    "productName": name,
                    "productCode": scode,
                    "insuranceType": cls.CATEGORY_LABELS.get((product_lcode, product_mcode), ""),
                    "status": "\ud310\ub9e4\uc911" if is_sale else "\ud310\ub9e4\uc911\uc9c0",
                    "sourceUrl": cls.source_url,
                    "documents": [],
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "updatedAt": None,
                    "officialSource": "\ub86f\ub370\uc190\ud574\ubcf4\ud5d8 \uc0c1\ud488\ubaa9\ub85d/\ubcf4\ud5d8\uc57d\uad00",
                    "lcode": product_lcode,
                    "mcode": product_mcode,
                    "scode": scode,
                    "isSale": is_sale,
                }
            )
        return products

    @classmethod
    def fetch_period_results(cls, product: dict[str, Any]) -> list[dict[str, Any]]:
        task = "gostep3issale" if product.get("isSale") else "gostep3isnotsale"
        html = cls.post_form(
            {
                "ops_tc": cls.ops_tc,
                "task": task,
                "rtnUri": "/web/C/D/H/cdh190_result.jsp",
                "lcode": product["lcode"],
                "mcode": product["mcode"],
                "scode": product["scode"],
                "startdate": "",
                "issale": "Y" if product.get("isSale") else "N",
                "srcPrdNm": "",
            }
        )
        periods = re.findall(
            r"step4\('([^']+)','([^']+)','([^']+)','([^']+)'\)[^<]*<span>(.*?)</span>",
            html,
        )
        results = []
        for lcode, mcode, scode, startdate, sale_period in periods:
            details = cls.fetch_documents(lcode, mcode, scode, startdate, product.get("isSale", False))
            if not details:
                continue
            period_result = dict(product)
            period_result.update(details)
            sale_start, sale_end = cls.parse_sale_period(sale_period)
            period_result["saleStartDate"] = sale_start or details.get("saleStartDate")
            period_result["saleEndDate"] = sale_end or details.get("saleEndDate")
            period_result["updatedAt"] = sale_start or details.get("saleStartDate")
            results.append(period_result)
        return results

    @classmethod
    def fetch_documents(cls, lcode: str, mcode: str, scode: str, startdate: str, is_sale: bool) -> dict[str, Any] | None:
        task = "gostep4issale" if is_sale else "gostep4isnotsale"
        html = cls.post_form(
            {
                "ops_tc": cls.ops_tc,
                "task": task,
                "rtnUri": "/web/C/D/H/cdh190_result.jsp",
                "lcode": lcode,
                "mcode": mcode,
                "scode": scode,
                "startdate": startdate,
                "issale": "Y" if is_sale else "N",
                "srcPrdNm": "",
            }
        )
        name_match = re.search(r"<dt[^>]*>[^<]*</dt>\s*<dd>\s*<span>(.*?)</span></dd>", html, re.S)
        sale_match = re.search(r"<dt[^>]*class=['\"]pt20['\"][^>]*>[^<]*</dt>\s*<dd>\s*<span>(.*?)</span></dd>", html, re.S)
        links = re.findall(r"<a\s+href=([^ >]+)[^>]*title='[^']*?_(.*?)\s*PDF[^']*'[^>]*>", html, re.S)
        if not name_match and not links:
            return None

        sale_start, sale_end = cls.parse_sale_period(sale_match.group(1) if sale_match else "")
        documents = []
        for href, raw_type in links:
            doc_type = cls.normalize_doc_type(raw_type)
            documents.append(
                {
                    "type": doc_type,
                    "title": doc_type,
                    "url": urllib.parse.urljoin(cls.base, href),
                    "revisionDate": sale_start,
                    "saleStartDate": sale_start,
                    "saleEndDate": sale_end,
                    "format": "PDF",
                }
            )

        return {
            "productName": clean_html(name_match.group(1)) if name_match else "",
            "documents": documents,
            "saleStartDate": sale_start,
            "saleEndDate": sale_end,
        }

    @classmethod
    def parse_sale_period(cls, value: str) -> tuple[str | None, str | None]:
        text = clean_html(value).replace(" ", "")
        match = re.match(r"(\d{4}\.\d{2}\.\d{2})~(.+)", text)
        if not match:
            return None, None
        start_raw, end_raw = match.groups()
        sale_start = clean_date(start_raw)
        sale_end = clean_date(end_raw)
        return sale_start, sale_end

    @classmethod
    def post_form(cls, payload: dict[str, str]) -> str:
        body = urllib.parse.urlencode(payload, encoding="euc-kr").encode("ascii")
        return fetch_text(
            cls.channel_url,
            method="POST",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": cls.source_url,
                "Origin": cls.base,
            },
            encoding="cp949",
        )


class SamsungAdapter:
    base = "https://www.samsungfire.com"
    source_url = f"{base}/vh/page/VH.REIF0011.do"
    api_url = f"{base}/vh/data/VH.HDIF0103.do"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None

    DOC_FIELDS = [
        ("prdfilename2", "\uc0ac\uc5c5\ubc29\ubc95\uc11c"),
        ("prdfilename3", "\uc0c1\ud488\uc694\uc57d\uc11c"),
        ("prdfilename1", "\ubcf4\ud5d8\uc57d\uad00"),
        ("prdfilename4", "\uc0c1\ud488\uc124\uba85\uc11c"),
    ]

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        results = []
        for item in cls.fetch_catalog():
            score = score_text(
                query,
                item["productName"],
                item.get("insuranceType", ""),
                item.get("insuranceCategory", ""),
                item.get("channel", ""),
                item.get("productCode", ""),
            )
            if score <= 0:
                continue
            ranked = dict(item)
            ranked["score"] = score
            results.append(ranked)

        return sorted(
            unique_by(results, "status", "productCode", "productName", "saleStartDate"),
            key=lambda item: (-item.get("score", 0), 0 if item.get("status") == "\ud310\ub9e4\uc911" else 1, item.get("productName", "")),
        )[:limit]

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        cached = cls._catalog_cache
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        response = cls.fetch_json("VH.HDIF0103", {})
        catalog: list[dict[str, Any]] = []
        for item in response.get("responseMessage", {}).get("body", {}).get("data", {}).get("list", []):
            product_name = (item.get("prdName") or "").strip()
            if not product_name:
                continue

            sale_end_raw = (item.get("saleEnDt") or "").strip()
            display_gb = (item.get("displayGb") or "").strip()
            is_active = display_gb == "1" or (display_gb != "2" and sale_end_raw == "99991231")
            sale_start = clean_date(item.get("saleStDt"))
            sale_end = None if sale_end_raw == "99991231" else clean_date(sale_end_raw)
            documents = []
            for field_name, doc_type in cls.DOC_FIELDS:
                path = (item.get(field_name) or "").strip()
                if not path:
                    continue
                title = path.split("/")[-1] or doc_type
                ext = title.rsplit(".", 1)[-1].upper() if "." in title else "PDF"
                documents.append(
                    {
                        "type": doc_type,
                        "title": title,
                        "url": urllib.parse.urljoin(cls.base, path),
                        "revisionDate": sale_start,
                        "saleStartDate": sale_start,
                        "saleEndDate": sale_end,
                        "format": ext,
                    }
                )

            catalog.append(
                {
                    "provider": "samsung",
                    "insurerName": "\uc0bc\uc131\ud654\uc7ac",
                    "productName": product_name,
                    "productCode": str(item.get("prdCode") or ""),
                    "insuranceType": (item.get("prdGb") or "").strip(),
                    "insuranceCategory": (item.get("prdGun") or "").strip(),
                    "channel": (item.get("saleChannel") or "").strip(),
                    "status": "\ud310\ub9e4\uc911" if is_active else "\ud310\ub9e4\uc911\uc9c0",
                    "sourceUrl": cls.source_url,
                    "documents": documents,
                    "saleStartDate": sale_start,
                    "saleEndDate": sale_end,
                    "updatedAt": sale_start,
                    "officialSource": "\uc0bc\uc131\ud654\uc7ac \ubcf4\ud5d8\uc0c1\ud488\uacf5\uc2dc",
                }
            )

        deduped = unique_by(catalog, "status", "productCode", "productName", "saleStartDate")
        cls._catalog_cache = (now, deduped)
        return [dict(item) for item in deduped]

    @classmethod
    def fetch_json(cls, tran_id: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = urllib.parse.urlencode(
            {
                "header": json.dumps({"tranId": tran_id}, ensure_ascii=False),
                "body": json.dumps(body, ensure_ascii=False),
            }
        ).encode("utf-8")
        raw = fetch_text(
            cls.api_url,
            method="POST",
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Referer": cls.source_url,
            },
            encoding="utf-8",
        )
        return json.loads(raw)


class NhFireAdapter:
    base = "https://www.nhfire.co.kr"
    source_url = f"{base}/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire"
    disclosure_ajax_url = f"{base}/front/announce/retrievePdtInfo.ajax"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return NhFireLiveAdapter.search(query, limit)

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        cached = cls._catalog_cache
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        html = fetch_text(cls.source_url, encoding="utf-8")
        category_positions = [
            {
                "start": match.start(),
                "category": clean_html(match.group(2) or match.group(1) or ""),
            }
            for match in re.finditer(
                r'<a href="javascript:void\(0\);" onclick="fnRetrieveProductInfo\(\'[A-Z0-9]+\'\)(?:;return false;)?"\s+title="([^"]*)">([^<]+)</a>',
                html,
                re.S,
            )
        ]

        products: list[dict[str, Any]] = []
        for match in re.finditer(
            r'<a href="/product/retrieveProduct\.nhfire\?pdtCd=([A-Z0-9]+)"\s+title="([^"]+)"[^>]*>(.*?)</a>',
            html,
            re.S,
        ):
            product_code = match.group(1)
            product_name = clean_html(match.group(3) or match.group(2))
            if not product_name:
                continue
            category = cls.category_for_position(category_positions, match.start())
            products.append(
                {
                    "provider": "nhfire",
                    "insurerName": "NH농협손해보험",
                    "productName": product_name,
                    "productCode": product_code,
                    "insuranceType": category,
                    "status": "판매중",
                    "sourceUrl": cls.detail_page_url(product_code),
                    "documents": [],
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "updatedAt": None,
                    "officialSource": "NH농협손해보험 상품공시",
                    "keywords": "",
                }
            )

        catalog = unique_by(products, "productCode", "productName")
        for item in []:
            detail = cls.fetch_product_detail(item["productCode"])
            merged = dict(item)
            merged.update(detail)
            merged["sourceUrl"] = cls.detail_page_url(item["productCode"])
            merged["officialSource"] = "NH농협손해보험 상품공시"
            catalog.append(merged)

        cls._catalog_cache = (now, catalog)
        return [dict(item) for item in catalog]

    @classmethod
    def get_product_detail(cls, product_code: str) -> dict[str, Any]:
        cached = cls._detail_cache.get(product_code)
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return dict(cached[1])
        detail = cls.fetch_product_detail(product_code)
        cls._detail_cache[product_code] = (now, detail)
        return dict(detail)

    @staticmethod
    def category_for_position(categories: list[dict[str, Any]], position: int) -> str:
        current = ""
        for item in categories:
            if item["start"] > position:
                break
            current = item["category"]
        return current

    @classmethod
    def fetch_product_detail(cls, product_code: str) -> dict[str, Any]:
        html = fetch_text(cls.detail_page_url(product_code), encoding="utf-8")
        disclosure = cls.fetch_disclosure(product_code)
        documents = disclosure["documents"] or cls.parse_documents(product_code, html)
        keywords_match = re.search(r'<ul class="bar_area">\s*<li>\s*(.*?)\s*</li>', html, re.S)
        keywords = clean_html(keywords_match.group(1)) if keywords_match else ""
        revision_date = disclosure["updatedAt"] or (documents[0]["revisionDate"] if documents else None)
        return {
            "documents": documents,
            "saleStartDate": disclosure["saleStartDate"],
            "saleEndDate": disclosure["saleEndDate"],
            "updatedAt": revision_date,
            "keywords": keywords,
        }

    @classmethod
    def fetch_disclosure(cls, product_code: str) -> dict[str, Any]:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.open(urllib.request.Request(cls.source_url, headers={"User-Agent": USER_AGENT}), timeout=30).read()
        query = urllib.parse.urlencode({"type": "ajax", "fileType": "05", "pdtCd": product_code})
        request = urllib.request.Request(
            f"{cls.disclosure_ajax_url}?{query}",
            headers={
                "User-Agent": USER_AGENT,
                "Referer": cls.source_url,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        xml_text = opener.open(request, timeout=30).read().decode("utf-8", errors="ignore")
        rows = cls.parse_disclosure_rows(xml_text)
        current = cls.pick_current_disclosure(rows)
        if not current:
            return {"documents": [], "saleStartDate": None, "saleEndDate": None, "updatedAt": None}
        documents = cls.documents_from_disclosure(product_code, current)
        return {
            "documents": documents,
            "saleStartDate": clean_date(current.get("pdtSelStDt")),
            "saleEndDate": clean_date(current.get("pdtSelEdDt")),
            "updatedAt": clean_date(current.get("pdtSelStDt")),
        }

    @staticmethod
    def parse_disclosure_rows(xml_text: str) -> list[dict[str, str]]:
        root = ET.fromstring(xml_text)
        multi = root.find(".//LMultiData")
        if multi is None:
            return []

        grouped: dict[str, list[str]] = {}
        for child in multi:
            grouped.setdefault(child.tag, []).append((child.text or "").strip())

        row_count = max((len(values) for values in grouped.values()), default=0)
        rows: list[dict[str, str]] = []
        for index in range(row_count):
            row = {key: values[index] if index < len(values) else "" for key, values in grouped.items()}
            rows.append(row)
        return rows

    @staticmethod
    def pick_current_disclosure(rows: list[dict[str, str]]) -> dict[str, str] | None:
        if not rows:
            return None

        def sort_key(row: dict[str, str]) -> tuple[int, str]:
            end_date = row.get("pdtSelEdDt") or ""
            is_current = 0 if end_date in {"99991231", "29991231", ""} else 1
            return (is_current, row.get("pdtSelStDt") or "")

        return sorted(rows, key=sort_key, reverse=False)[0]

    @classmethod
    def documents_from_disclosure(cls, product_code: str, row: dict[str, str]) -> list[dict[str, Any]]:
        documents = []
        mappings = [
            ("plcndAfileSeqn", "plcndAfileNm", "보험약관"),
            ("bzMtdAfileSeqn", "bzMtdAfileNm", "사업방법서"),
            ("smmrAfileSeqn", "smmrAfileNm", "상품요약서"),
        ]
        file_id = row.get("fileId", "")
        revision_date = clean_date(row.get("pdtSelStDt"))
        for seq_key, name_key, doc_type in mappings:
            seq = (row.get(seq_key) or "").strip()
            file_name = (row.get(name_key) or "").strip()
            if not file_id or not seq or not file_name:
                continue
            documents.append(
                {
                    "type": doc_type,
                    "title": doc_type,
                    "displayTitle": doc_type,
                    "url": (
                        f"/api/download/nhfire?pdtCd={urllib.parse.quote(product_code)}"
                        f"&fileId={urllib.parse.quote(file_id)}&seq={urllib.parse.quote(seq)}&name={urllib.parse.quote(file_name)}"
                    ),
                    "revisionDate": revision_date or cls.extract_revision(file_name),
                    "saleStartDate": clean_date(row.get("pdtSelStDt")),
                    "saleEndDate": clean_date(row.get("pdtSelEdDt")),
                    "format": "PDF",
                }
            )
        return documents

    @classmethod
    def parse_documents(cls, product_code: str, html: str) -> list[dict[str, Any]]:
        documents = []
        seen: set[tuple[str, str]] = set()
        for file_id, seq, filename in re.findall(
            r"fnPdtFileDownload\('([^']+)',\s*'([^']+)',\s*'([^']*)'\)",
            html,
        ):
            file_name = filename.strip()
            if not file_name:
                continue
            signature = (file_id, seq)
            if signature in seen:
                continue
            seen.add(signature)
            documents.append(
                {
                    "type": cls.document_type(file_name),
                    "title": cls.document_type(file_name),
                    "displayTitle": cls.document_type(file_name),
                    "url": f"/api/download/nhfire?pdtCd={urllib.parse.quote(product_code)}&seq={urllib.parse.quote(seq)}&name={urllib.parse.quote(file_name)}",
                    "revisionDate": cls.extract_revision(file_name),
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "format": "PDF",
                }
            )
        return documents

    @staticmethod
    def document_type(filename: str) -> str:
        lowered = filename.lower()
        if "안내장" in filename:
            return "상품설명서"
        if "요약" in filename:
            return "상품요약서"
        if "사업방법" in filename:
            return "사업방법서"
        if "설명" in filename:
            return "상품설명서"
        if "약관" in filename or lowered.endswith(".pdf"):
            return "보험약관"
        return "공식문서"

    @classmethod
    def download_document(cls, product_code: str, seq: str, preferred_name: str = "", file_id: str = "") -> tuple[bytes, str, str]:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        referer_url = cls.source_url
        html = opener.open(urllib.request.Request(referer_url, headers={"User-Agent": USER_AGENT}), timeout=30).read().decode("utf-8", errors="ignore")
        action_match = re.search(r'"(/imageView/downloadFile\.ajax;jsessionid=[^"]+)"', html)
        if not action_match:
            raise ValueError("NH농협손해보험 다운로드 경로를 찾지 못했습니다.")

        resolved_file_id = file_id.strip()
        resolved_name = preferred_name.strip()
        if not resolved_file_id:
            disclosure = cls.fetch_disclosure(product_code)
            for document in disclosure["documents"]:
                parsed = urllib.parse.urlparse(document["url"])
                params = urllib.parse.parse_qs(parsed.query)
                if params.get("seq", [""])[0] == seq:
                    resolved_file_id = params.get("fileId", [""])[0]
                    resolved_name = urllib.parse.unquote(params.get("name", [""])[0]) or resolved_name
                    break

        if not resolved_file_id:
            raise ValueError("NH농협손해보험 문서 정보를 찾지 못했습니다.")

        body = urllib.parse.urlencode({"fileId": resolved_file_id, "afileSeqn": seq}).encode("utf-8")
        request = urllib.request.Request(
            urllib.parse.urljoin(cls.base, action_match.group(1)),
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": referer_url,
                "Origin": cls.base,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with opener.open(request, timeout=30) as response:
            payload = response.read()
            content_type = response.getheader("Content-Type") or "application/octet-stream"

        if not payload.startswith(b"%PDF"):
            raise ValueError("NH농협손해보험 PDF 다운로드에 실패했습니다.")

        filename = resolved_name or preferred_name or f"nhfire-{product_code}-{seq}.pdf"
        return payload, filename, content_type

    @classmethod
    def detail_page_url(cls, product_code: str) -> str:
        return f"{cls.base}/product/retrieveProduct.nhfire?pdtCd={urllib.parse.quote(product_code)}"

    @staticmethod
    def extract_revision(value: str | None) -> str | None:
        if not value:
            return None
        compact = re.sub(r"[^0-9]", "", value)
        if len(compact) >= 8:
            return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"
        match = re.search(r"(?<!\d)(\d{2})(0[1-9]|1[0-2])(?!\d)", compact)
        if match:
            return f"20{match.group(1)}-{match.group(2)}-01"
        dotted = re.search(r"(?<!\d)(\d{2})\.(\d{1,2})(?!\d)", value)
        if dotted:
            return f"20{dotted.group(1)}-{int(dotted.group(2)):02d}-01"
        return None


class NhFireLiveAdapter:
    base = "https://www.nhfire.co.kr"
    source_url = f"{base}/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire"
    search_url = f"{base}/announce/productAnnounce/retrieveInsuranceProductsAnnounceSearch.nhfire"
    disclosure_ajax_url = f"{base}/front/announce/retrievePdtInfo.ajax"
    detail_url = f"{base}/product/retrieveProduct.nhfire"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None
    _detail_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        ranked = []
        catalog = cls.search_catalog(query) if query.strip() else cls.fetch_catalog()
        for item in catalog:
            score = score_text(query, item["productName"], item.get("insuranceType", ""), item.get("productCode", ""))
            if score <= 0:
                continue
            ranked.append({**item, "score": score})

        candidates = sorted(
            unique_by(ranked, "productCode", "productName"),
            key=lambda item: (-item["score"], item["productName"]),
        )

        enriched = []
        for item in candidates[: expanded_limit(limit)]:
            detail = cls.fetch_detail(item["productCode"])
            merged = {**item, **detail}
            merged["score"] = score_text(
                query,
                merged["productName"],
                merged.get("insuranceType", ""),
                merged.get("keywords", ""),
                " ".join(doc.get("type", "") for doc in merged.get("documents", [])),
                merged.get("productCode", ""),
            )
            enriched.append(merged)

        return sorted(
            unique_by(enriched, "productCode", "productName"),
            key=lambda item: (-item["score"], item["productName"]),
        )[:limit]

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        cached = cls._catalog_cache
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        html = fetch_text(cls.source_url, encoding="utf-8")
        category_positions = [
            {"start": match.start(), "category": clean_html(match.group(2) or match.group(1) or "")}
            for match in re.finditer(
                r'<a href="javascript:void\(0\);" onclick="fnRetrieveProductInfo\(\'[A-Z0-9]+\'\)(?:;return false;)?"\s+title="([^"]*)">([^<]+)</a>',
                html,
                re.S,
            )
        ]

        products: list[dict[str, Any]] = []
        for match in re.finditer(
            r'<a href="/product/retrieveProduct\.nhfire\?pdtCd=([A-Z0-9]+)"\s+title="([^"]+)"[^>]*>(.*?)</a>',
            html,
            re.S,
        ):
            product_code = match.group(1)
            product_name = clean_html(match.group(3) or match.group(2))
            if not product_name:
                continue
            products.append(
                {
                    "provider": "nhfire",
                    "insurerName": "NH농협손해보험",
                    "productName": product_name,
                    "productCode": product_code,
                    "insuranceType": cls.category_for_position(category_positions, match.start()),
                    "status": "판매중",
                    "sourceUrl": cls.detail_page_url(product_code),
                    "documents": [],
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "updatedAt": None,
                    "officialSource": "NH농협손해보험 상품공시",
                    "keywords": "",
                }
            )

        catalog = unique_by(products, "productCode", "productName")
        cls._catalog_cache = (now, catalog)
        return [dict(item) for item in catalog]

    @classmethod
    def search_catalog(cls, query: str) -> list[dict[str, Any]]:
        normalized_query = query.strip()
        if not normalized_query:
            return cls.fetch_catalog()

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.open(urllib.request.Request(cls.search_url, headers={"User-Agent": USER_AGENT}), timeout=30).read()

        body = urllib.parse.urlencode(
            {
                "pdtSelYn": "Y",
                "basicDate": "",
                "flag": "",
                "searchWord": normalized_query,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            cls.search_url,
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": cls.search_url,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        html = opener.open(request, timeout=30).read().decode("utf-8", errors="ignore")

        block_match = re.search(r'<ul class="pdtCd_Y">(.*?)</ul>', html, re.S)
        if not block_match:
            return cls.fetch_catalog()

        template = cls.fetch_catalog()
        template_by_code = {item.get("productCode"): dict(item) for item in template}
        products: list[dict[str, Any]] = []
        for product_code, raw_name in re.findall(
            r"fnRetrievePdtInfo\('([A-Z0-9]+)'[^)]*\)\">(.+?)</a>",
            block_match.group(1),
            re.S,
        ):
            product_name = re.sub(r"\s+", " ", clean_html(raw_name)).strip()
            if not product_name:
                continue
            base_item = template_by_code.get(product_code)
            if base_item:
                base_item["productName"] = product_name
                products.append(base_item)
                continue
            products.append(
                {
                    "provider": "nhfire",
                    "insurerName": "NH농협손해보험",
                    "productName": product_name,
                    "productCode": product_code,
                    "insuranceType": "",
                    "status": "판매중",
                    "sourceUrl": cls.detail_page_url(product_code),
                    "documents": [],
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "updatedAt": None,
                    "officialSource": "NH농협손해보험 상품공시",
                    "keywords": "",
                }
            )

        return unique_by(products, "productCode", "productName") or template

    @staticmethod
    def category_for_position(categories: list[dict[str, Any]], position: int) -> str:
        current = ""
        for item in categories:
            if item["start"] > position:
                break
            current = item["category"]
        return current

    @classmethod
    def fetch_detail(cls, product_code: str) -> dict[str, Any]:
        cached = cls._detail_cache.get(product_code)
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return dict(cached[1])

        html = fetch_text(cls.detail_page_url(product_code), encoding="utf-8")
        keywords_match = re.search(r'<ul class="bar_area">\s*<li>\s*(.*?)\s*</li>', html, re.S)
        keywords = clean_html(keywords_match.group(1)) if keywords_match else ""
        disclosure = cls.fetch_disclosure(product_code)
        detail = {
            "documents": disclosure["documents"],
            "saleStartDate": disclosure["saleStartDate"],
            "saleEndDate": disclosure["saleEndDate"],
            "updatedAt": disclosure["updatedAt"],
            "keywords": keywords,
        }
        if not detail["documents"]:
            detail["documents"] = cls.parse_detail_terms(product_code, html)
            if detail["documents"] and not detail["updatedAt"]:
                detail["updatedAt"] = detail["documents"][0].get("revisionDate")
        cls._detail_cache[product_code] = (now, detail)
        return dict(detail)

    @classmethod
    def fetch_disclosure(cls, product_code: str) -> dict[str, Any]:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        opener.open(urllib.request.Request(cls.source_url, headers={"User-Agent": USER_AGENT}), timeout=30).read()
        query = urllib.parse.urlencode({"type": "ajax", "fileType": "05", "pdtCd": product_code})
        request = urllib.request.Request(
            f"{cls.disclosure_ajax_url}?{query}",
            headers={"User-Agent": USER_AGENT, "Referer": cls.source_url, "X-Requested-With": "XMLHttpRequest"},
        )
        xml_text = opener.open(request, timeout=30).read().decode("utf-8", errors="ignore")
        rows = cls.parse_disclosure_rows(xml_text)
        row = cls.pick_current_row(rows)
        if not row:
            return {"documents": [], "saleStartDate": None, "saleEndDate": None, "updatedAt": None}
        return {
            "documents": cls.documents_from_row(product_code, row),
            "saleStartDate": clean_date(row.get("pdtSelStDt")),
            "saleEndDate": clean_date(row.get("pdtSelEdDt")),
            "updatedAt": clean_date(row.get("pdtSelStDt")),
        }

    @staticmethod
    def parse_disclosure_rows(xml_text: str) -> list[dict[str, str]]:
        root = ET.fromstring(xml_text)
        multi = root.find(".//LMultiData")
        if multi is None:
            return []
        grouped: dict[str, list[str]] = {}
        for child in multi:
            grouped.setdefault(child.tag, []).append((child.text or "").strip())
        row_count = max((len(values) for values in grouped.values()), default=0)
        return [{key: values[index] if index < len(values) else "" for key, values in grouped.items()} for index in range(row_count)]

    @staticmethod
    def pick_current_row(rows: list[dict[str, str]]) -> dict[str, str] | None:
        if not rows:
            return None
        def row_key(row: dict[str, str]) -> tuple[int, str]:
            end_date = row.get("pdtSelEdDt") or ""
            current_flag = 0 if end_date in {"99991231", "29991231", ""} else 1
            return (current_flag, -(int(row.get("pdtSelStDt") or "0")))
        return sorted(rows, key=row_key)[0]

    @classmethod
    def documents_from_row(cls, product_code: str, row: dict[str, str]) -> list[dict[str, Any]]:
        file_id = (row.get("fileId") or "").strip()
        revision_date = clean_date(row.get("pdtSelStDt"))
        mappings = [
            ("plcndAfileSeqn", "plcndAfileNm", "보험약관"),
            ("bzMtdAfileSeqn", "bzMtdAfileNm", "사업방법서"),
            ("smmrAfileSeqn", "smmrAfileNm", "상품요약서"),
        ]
        documents = []
        for seq_key, name_key, doc_type in mappings:
            seq = (row.get(seq_key) or "").strip()
            filename = (row.get(name_key) or "").strip()
            if not file_id or not seq or not filename:
                continue
            documents.append(
                {
                    "type": doc_type,
                    "title": doc_type,
                    "displayTitle": doc_type,
                    "url": (
                        f"/api/download/nhfire?pdtCd={urllib.parse.quote(product_code)}"
                        f"&fileId={urllib.parse.quote(file_id)}&seq={urllib.parse.quote(seq)}&name={urllib.parse.quote(filename)}"
                    ),
                    "revisionDate": revision_date or cls.extract_revision(filename),
                    "saleStartDate": clean_date(row.get("pdtSelStDt")),
                    "saleEndDate": clean_date(row.get("pdtSelEdDt")),
                    "format": "PDF",
                }
            )
        return documents

    @classmethod
    def parse_detail_terms(cls, product_code: str, html: str) -> list[dict[str, Any]]:
        documents = []
        seen: set[tuple[str, str]] = set()
        for file_id, seq, filename in re.findall(r"fnPdtFileDownload\('([^']+)',\s*'([^']+)',\s*'([^']*)'\)", html):
            filename = filename.strip()
            if not filename:
                continue
            signature = (file_id, seq)
            if signature in seen:
                continue
            seen.add(signature)
            doc_type = "보험약관"
            documents.append(
                {
                    "type": doc_type,
                    "title": doc_type,
                    "displayTitle": doc_type,
                    "url": (
                        f"/api/download/nhfire?pdtCd={urllib.parse.quote(product_code)}"
                        f"&fileId={urllib.parse.quote(file_id)}&seq={urllib.parse.quote(seq)}&name={urllib.parse.quote(filename)}"
                    ),
                    "revisionDate": cls.extract_revision(filename),
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "format": "PDF",
                }
            )
        return documents

    @classmethod
    def download_document(cls, product_code: str, seq: str, preferred_name: str = "", file_id: str = "") -> tuple[bytes, str, str]:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        landing_html = opener.open(urllib.request.Request(cls.source_url, headers={"User-Agent": USER_AGENT}), timeout=30).read().decode("utf-8", errors="ignore")
        action_match = re.search(r'"(/imageView/downloadFile\.ajax;jsessionid=[^"]+)"', landing_html)
        if not action_match:
            raise ValueError("NH농협손해보험 다운로드 경로를 찾지 못했습니다.")

        resolved_file_id = file_id.strip()
        resolved_name = preferred_name.strip()
        if not resolved_file_id:
            disclosure = cls.fetch_disclosure(product_code)
            for document in disclosure["documents"]:
                parsed = urllib.parse.urlparse(document["url"])
                params = urllib.parse.parse_qs(parsed.query)
                if params.get("seq", [""])[0] == seq:
                    resolved_file_id = params.get("fileId", [""])[0]
                    resolved_name = urllib.parse.unquote(params.get("name", [""])[0]) or resolved_name
                    break
        if not resolved_file_id:
            raise ValueError("NH농협손해보험 문서 정보를 찾지 못했습니다.")

        body = urllib.parse.urlencode({"fileId": resolved_file_id, "afileSeqn": seq}).encode("utf-8")
        request = urllib.request.Request(
            urllib.parse.urljoin(cls.base, action_match.group(1)),
            data=body,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": cls.source_url,
                "Origin": cls.base,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with opener.open(request, timeout=30) as response:
            payload = response.read()
            content_type = response.getheader("Content-Type") or "application/octet-stream"
        if not payload.startswith(b"%PDF"):
            raise ValueError("NH농협손해보험 PDF 다운로드에 실패했습니다.")
        return payload, (resolved_name or preferred_name or f"nhfire-{product_code}-{seq}.pdf"), content_type

    @classmethod
    def detail_page_url(cls, product_code: str) -> str:
        return f"{cls.detail_url}?pdtCd={urllib.parse.quote(product_code)}"

    @staticmethod
    def extract_revision(value: str | None) -> str | None:
        if not value:
            return None
        compact = re.sub(r"[^0-9]", "", value)
        if len(compact) >= 8:
            return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"
        dotted = re.search(r"(?<!\d)(\d{2})\.(\d{1,2})(?!\d)", value)
        if dotted:
            return f"20{dotted.group(1)}-{int(dotted.group(2)):02d}-01"
        month = re.search(r"(?<!\d)(\d{2})(0[1-9]|1[0-2])(?!\d)", compact)
        if month:
            return f"20{month.group(1)}-{month.group(2)}-01"
        return None


class MgAdapter:
    base = "https://www.yebyeol.co.kr"
    current_source_url = f"{base}/PB031210DM.scp?menuId=MN0803006"
    stopped_source_url = f"{base}/PB031220DM.scp?menuId=MN0803006"
    list_api_url = f"{base}/PB031210_001.ajax"
    download_form_url = f"{base}/PB031130_003.form"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None
    _rows_cache: dict[tuple[str, str, str], tuple[float, list[dict[str, Any]]]] = {}

    CATEGORY_CODES = {
        "L": [
            ("06", "상해"),
            ("07", "운전자"),
            ("15", "건강"),
            ("16", "어린이"),
            ("09", "재물"),
            ("17", "실손"),
            ("10", "저축"),
            ("18", "연금저축"),
            ("19", "방카슈랑스"),
            ("20", "CM"),
            ("04", "독립특약"),
            ("21", "단체"),
        ],
        "A": [
            ("01", "개인용"),
            ("02", "업무용"),
            ("03", "영업용"),
            ("04", "운전자"),
            ("05", "이륜차"),
            ("06", "취급업자"),
            ("07", "공동물건"),
            ("99", "기타"),
        ],
        "G": [
            ("01", "상해보험"),
            ("02", "일반"),
            ("03", "특종보험"),
            ("04", "화재보험"),
            ("05", "방카슈랑스"),
        ],
    }

    DOC_TYPES = {
        "1": "상품요약서",
        "2": "보험약관",
        "3": "사업방법서",
    }

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        products = cls.search_categories(query, cls.category_plan(query))
        if products:
            return products[:limit]
        return cls.search_categories(query, [(lccd, mccd, category_name) for lccd, categories in cls.CATEGORY_CODES.items() for mccd, category_name in categories])[:limit]

    @classmethod
    def search_categories(cls, query: str, categories: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        for sale_flag in ["0", "1"]:
            for lccd, mccd, category_name in categories:
                for row in cls.fetch_cached_rows(lccd, mccd, sale_flag):
                    item = cls.row_to_result(row, lccd, mccd, category_name)
                    if not item:
                        continue
                    score = score_text(
                        query,
                        item["productName"],
                        item.get("insuranceType", ""),
                        item.get("keywords", ""),
                        item.get("productCode", ""),
                    )
                    if score <= 0:
                        continue
                    products.append({**item, "score": score})

        return sorted(
            unique_by(products, "id", "productName"),
            key=lambda item: (-item["score"], 0 if item.get("status") == "판매중" else 1, item["productName"]),
        )

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        cached = cls._catalog_cache
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        products: list[dict[str, Any]] = []
        for sale_flag, source_url in [("0", cls.current_source_url), ("1", cls.stopped_source_url)]:
            opener, token = cls.open_session(source_url)
            for lccd, categories in cls.CATEGORY_CODES.items():
                for mccd, category_name in categories:
                    rows = cls.fetch_rows(opener, token, source_url, lccd, mccd, sale_flag)
                    for row in rows:
                        item = cls.row_to_result(row, lccd, mccd, category_name)
                        if item:
                            products.append(item)

        catalog = unique_by(products, "id", "productName")
        cls._catalog_cache = (now, catalog)
        return [dict(item) for item in catalog]

    @classmethod
    def fetch_cached_rows(cls, lccd: str, mccd: str, sale_flag: str) -> list[dict[str, Any]]:
        cache_key = (sale_flag, lccd, mccd)
        cached = cls._rows_cache.get(cache_key)
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        source_url = cls.current_source_url if sale_flag == "0" else cls.stopped_source_url
        opener, token = cls.open_session(source_url)
        try:
            rows = cls.fetch_rows(opener, token, source_url, lccd, mccd, sale_flag)
        except Exception:
            rows = []
        cls._rows_cache[cache_key] = (now, rows)
        return [dict(item) for item in rows]

    @classmethod
    def open_session(cls, source_url: str) -> tuple[urllib.request.OpenerDirector, str]:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        request = urllib.request.Request(source_url, headers={"User-Agent": USER_AGENT})
        html = opener.open(request, timeout=30).read().decode("utf-8", errors="ignore")
        token_match = re.search(r'name="comToken"\s+value="([^"]+)"', html)
        if not token_match:
            raise ValueError("MG손해보험 세션 토큰을 찾지 못했습니다.")
        return opener, token_match.group(1)

    @classmethod
    def fetch_rows(
        cls,
        opener: urllib.request.OpenerDirector,
        token: str,
        source_url: str,
        lccd: str,
        mccd: str,
        sale_flag: str,
    ) -> list[dict[str, Any]]:
        payload = urllib.parse.urlencode(
            {
                "searchPrdtLccd": lccd,
                "searchPrdtMccd": mccd,
                "searchPrdtSaleYn": sale_flag,
                "searchText": "",
                "menuId": "MN0803006",
                "comToken": token,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            cls.list_api_url,
            data=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": source_url,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
            method="POST",
        )
        response = json.loads(opener.open(request, timeout=30).read().decode("utf-8", errors="ignore"))
        if response.get("prcSts") not in {"N", None}:
            raise ValueError(response.get("resMsg") or "MG손해보험 상품목록 조회에 실패했습니다.")
        return response.get("list", {}).get("rows", []) or []

    @classmethod
    def row_to_result(cls, row: dict[str, Any], lccd: str, mccd: str, category_name: str) -> dict[str, Any] | None:
        product_name = (row.get("inskdAbbrNm") or row.get("inskdRpsntNm") or row.get("inskdNm") or "").strip()
        data_id = str(row.get("dataIdno") or "").strip()
        if not product_name or not data_id:
            return None

        documents = cls.documents_from_row(row)
        sale_flag = str(row.get("prdtSaleYn") or "")
        status = "판매중" if sale_flag == "0" else "판매중지"
        sale_start = clean_date(row.get("saleDate"))
        sale_end = clean_date(row.get("saleEnddt"))
        updated_at = max((doc.get("revisionDate") or "" for doc in documents), default="") or sale_start
        period_label = "현재 판매상품목록" if sale_flag == "0" else "판매중지상품"

        return {
            "id": f"mg-{data_id}",
            "provider": "mg",
            "insurerName": "MG손해보험(예별손해보험)",
            "productName": product_name,
            "productCode": data_id,
            "groupCode": str(row.get("inskdRpsntCd") or ""),
            "insuranceType": cls.category_label(lccd, mccd, category_name),
            "status": status,
            "sourceUrl": cls.current_source_url if sale_flag == "0" else cls.stopped_source_url,
            "documents": documents,
            "saleStartDate": sale_start,
            "saleEndDate": sale_end,
            "updatedAt": updated_at,
            "officialSource": f"예별손해보험 상품공시실({period_label})",
            "keywords": " ".join(
                filter(
                    None,
                    [
                        row.get("inskdRpsntNm"),
                        row.get("inskdAbbrNm"),
                        row.get("inskdNm"),
                        category_name,
                    ],
                )
            ),
        }

    @classmethod
    def documents_from_row(cls, row: dict[str, Any]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        sale_flag = str(row.get("prdtSaleYn") or "")
        data_id = str(row.get("dataIdno") or "").strip()
        for doc_cfcd, doc_type in cls.DOC_TYPES.items():
            original_name = (row.get(f"doc{doc_cfcd}Org") or "").strip()
            if not original_name:
                continue
            params = urllib.parse.urlencode(
                {
                    "dataIdno": data_id,
                    "docCfcd": doc_cfcd,
                    "saleYn": sale_flag,
                    "name": original_name,
                }
            )
            documents.append(
                {
                    "type": doc_type,
                    "title": original_name,
                    "displayTitle": doc_type,
                    "url": f"/api/download/mg?{params}",
                    "revisionDate": cls.extract_revision(original_name) or clean_date(row.get("saleDate")),
                    "saleStartDate": clean_date(row.get("saleDate")),
                    "saleEndDate": clean_date(row.get("saleEnddt")),
                    "format": cls.document_format(original_name),
                }
            )
        return documents

    @classmethod
    def download_document(cls, data_id: str, doc_cfcd: str, sale_flag: str = "0", preferred_name: str = "") -> tuple[bytes, str, str]:
        source_url = cls.current_source_url if sale_flag == "0" else cls.stopped_source_url
        opener, token = cls.open_session(source_url)
        payload = urllib.parse.urlencode(
            {
                "dataIdno": data_id,
                "docCfcd": doc_cfcd,
                "menuId": "MN0803006",
                "comToken": token,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            cls.download_form_url,
            data=payload,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": source_url,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with opener.open(request, timeout=30) as response:
            body = response.read()
            content_type = response.getheader("Content-Type") or "application/octet-stream"
            disposition = response.getheader("Content-Disposition") or ""
        if not body:
            raise ValueError("MG손해보험 문서 다운로드에 실패했습니다.")
        filename = preferred_name.strip() or cls.filename_from_disposition(disposition) or f"mg-{data_id}-{doc_cfcd}.pdf"
        return body, filename, content_type

    @staticmethod
    def category_label(lccd: str, mccd: str, category_name: str) -> str:
        prefixes = {"L": "장기보험", "A": "자동차보험", "G": "일반보험"}
        prefix = prefixes.get(lccd, "")
        return f"{prefix}/{category_name}" if prefix else category_name

    @classmethod
    def category_plan(cls, query: str) -> list[tuple[str, str, str]]:
        normalized = normalize_text(query)
        if any(token in normalized for token in ["자동차", "이륜", "업무용", "영업용", "개인용"]):
            return [("A", mccd, name) for mccd, name in cls.CATEGORY_CODES["A"]]
        if any(token in normalized for token in ["화재", "재물", "배상", "골프", "여행", "특종"]):
            return [("G", mccd, name) for mccd, name in cls.CATEGORY_CODES["G"]] + [("L", "09", "재물")]
        if any(token in normalized for token in ["어린이", "아이", "태아", "mom", "맘"]):
            return [("L", "16", "어린이"), ("L", "15", "건강")]
        if any(token in normalized for token in ["실손", "의료비", "입원", "통원"]):
            return [("L", "17", "실손"), ("L", "20", "CM"), ("L", "15", "건강")]
        if any(token in normalized for token in ["운전자", "상해"]):
            return [("L", "07", "운전자"), ("L", "06", "상해"), ("A", "04", "운전자")]
        if any(token in normalized for token in ["연금", "저축"]):
            return [("L", "18", "연금저축"), ("L", "10", "저축")]
        if any(token in normalized for token in ["원더풀", "올케어", "건강", "암", "질병", "치아", "수술", "간병", "뇌", "심"]):
            return [("L", "15", "건강"), ("L", "16", "어린이"), ("L", "06", "상해"), ("L", "17", "실손"), ("L", "20", "CM")]
        return [("L", mccd, name) for mccd, name in cls.CATEGORY_CODES["L"]]

    @staticmethod
    def extract_revision(value: str | None) -> str | None:
        if not value:
            return None
        full_year_matches = re.findall(r"20\d{6}", value)
        if full_year_matches:
            latest = full_year_matches[-1]
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        compact_matches = re.findall(r"(?<!\d)\d{6}(?!\d)", value)
        if compact_matches:
            latest = compact_matches[-1]
            return f"20{latest[:2]}-{latest[2:4]}-{latest[4:6]}"
        return None

    @staticmethod
    def document_format(filename: str) -> str:
        ext = Path(filename).suffix.lower().lstrip(".")
        return ext.upper() if ext else "FILE"

    @staticmethod
    def filename_from_disposition(disposition: str) -> str | None:
        match = re.search(r"filename\*=UTF-8''([^;]+)", disposition, re.I)
        if match:
            return urllib.parse.unquote(match.group(1))
        match = re.search(r'filename="?([^";]+)"?', disposition, re.I)
        if match:
            return urllib.parse.unquote(match.group(1))
        return None


class HanwhaFireAdapter:
    base = "https://m.hwgeneralins.com"
    file_base = "https://www.hwgeneralins.com"
    api_url = f"{base}/smt/prd/cmn/select-ins-gd-info"
    source_url = f"{base}/product/catalog/product-info.do"
    current_disclosure_url = "https://www.hwgeneralins.com/notice/ir/product-ing01.do"
    stopped_disclosure_url = "https://www.hwgeneralins.com/notice/ir/product-end01.do"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None
    _document_exists_cache: dict[str, bool] = {}

    PRODUCT_META = {
        "CA00044001": ("자동차", "한화 자동차보험"),
        "CA00077001": ("자동차", "ECO마일리지 특약"),
        "CA00088002": ("자동차", "첨단안전장치특약"),
        "CA00088003": ("자동차", "커넥티드카 할인특약"),
        "CA00088004": ("자동차", "안전운전점수할인특약"),
        "CA00088005": ("자동차", "후측방충돌방지장치 할인특약"),
        "CA00088006": ("자동차", "어라운드뷰모니터장착 할인특약"),
        "CA00088007": ("자동차", "헤드업디스플레이장착 할인특약"),
        "CA00100001": ("자동차", "퍼마일 특별약관(월정산형)"),
        "FA00045003": ("여행/레저", "해외유학생보험"),
        "FA00131001": ("기업", "재난배상책임보험"),
        "LA01381001": ("건강/종합", "한화 더건강한 한아름종합보험 무배당"),
        "LA01406001": ("건강/종합", "한화실손의료보험(갱신형)"),
        "LA01416001": ("연금/저축", "골드연금보험"),
        "LA01988002": ("건강/종합", "한화 시그니처 여성건강보험"),
        "LA02821001": ("가족", "한화 건강쑥쑥 어린이보험 무배당"),
    }

    AUXILIARY_PRODUCTS = [
        {
            "productCode": "HANWHA-HANAREUM-SILSOK-GANPYEON",
            "productName": "한화 한아름 실속 건강보험(연만기갱신형) 무배당(간편고지형)",
            "displayName": "한화 한아름 실속 건강보험(연만기갱신형) 무배당(간편고지형)",
            "insuranceType": "건강/종합",
            "status": "판매중",
            "sourceUrl": current_disclosure_url,
            "officialSource": "한화손해보험 보험상품공시(현재판매상품)",
            "notice": "공식 공시실 검색 결과 기반 보조 검색 결과입니다.",
        },
        {
            "productCode": "HANWHA-HANAREUM-SILSOK-ILBAN",
            "productName": "한화 한아름 실속 건강보험(연만기갱신형) 무배당(일반/건강고지형)",
            "displayName": "한화 한아름 실속 건강보험(연만기갱신형) 무배당(일반/건강고지형)",
            "insuranceType": "건강/종합",
            "status": "판매중",
            "sourceUrl": current_disclosure_url,
            "officialSource": "한화손해보험 보험상품공시(현재판매상품)",
            "notice": "공식 공시실 검색 결과 기반 보조 검색 결과입니다.",
        },
        {
            "productCode": "HANWHA-LIFEPLUS-HANAREUM",
            "productName": "무배당 LIFEPLUS 한아름종합보험",
            "displayName": "무배당 LIFEPLUS 한아름종합보험",
            "insuranceType": "건강/종합",
            "status": "판매중지",
            "sourceUrl": "https://www.hwgeneralins.com/upload/hmpag_upload/product/hanareum_02.pdf",
            "officialSource": "한화손해보험 사업방법서 PDF",
            "notice": "공식 PDF 공시 문서 기반 보조 검색 결과입니다.",
        },
        {
            "productCode": "HANWHA-LIFEPLUS-HANAREUM-2204",
            "productName": "무배당 LIFEPLUS 한아름종합보험2204",
            "displayName": "무배당 LIFEPLUS 한아름종합보험2204",
            "insuranceType": "건강/종합",
            "status": "판매중지",
            "sourceUrl": "https://www.hwgeneralins.com/upload/hmpag_upload/product/hanareum%282204%29_02.pdf",
            "officialSource": "한화손해보험 사업방법서 PDF",
            "notice": "공식 PDF 공시 문서 기반 보조 검색 결과입니다.",
        },
        {
            "productCode": "HANWHA-LIFEPLUS-HANAREUM-2301",
            "productName": "무배당 LIFEPLUS 한아름종합보험2301",
            "displayName": "무배당 LIFEPLUS 한아름종합보험2301",
            "insuranceType": "건강/종합",
            "status": "판매중지",
            "sourceUrl": "https://www.hwgeneralins.com/upload/hmpag_upload/product/hanareum%282301%29_02.pdf",
            "officialSource": "한화손해보험 사업방법서 PDF",
            "notice": "공식 PDF 공시 문서 기반 보조 검색 결과입니다.",
        },
        {
            "productCode": "HANWHA-LIFEPLUS-HANAREUM-2404",
            "productName": "LIFEPLUS 더건강한 한아름종합보험 무배당2404",
            "displayName": "LIFEPLUS 더건강한 한아름종합보험 무배당2404",
            "insuranceType": "건강/종합",
            "status": "판매중지",
            "sourceUrl": stopped_disclosure_url,
            "officialSource": "한화손해보험 보험상품공시(판매중지상품)",
            "notice": "공식 공시실 검색 결과 기반 보조 검색 결과입니다.",
        },
        {
            "productCode": "HANWHA-LIFEPLUS-HANAREUM-LEGACY",
            "productName": "LIFEPLUS 더건강한 한아름종합보험 무배당",
            "displayName": "LIFEPLUS 더건강한 한아름종합보험 무배당",
            "insuranceType": "건강/종합",
            "status": "판매중지",
            "sourceUrl": stopped_disclosure_url,
            "officialSource": "한화손해보험 보험상품공시(판매중지상품)",
            "notice": "공식 공시실 검색 결과 기반 보조 검색 결과입니다.",
        },
    ]

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        products = []
        for item in cls.search_catalog():
            score = score_text(
                query,
                item["productName"],
                item.get("displayName", ""),
                item.get("insuranceType", ""),
                item.get("productCode", ""),
            )
            if score <= 0:
                continue
            item["score"] = score
            products.append(item)

        return sorted(
            unique_by(products, "productCode", "productName"),
            key=lambda item: (-item["score"], 0 if item.get("status") == "판매중" else 1, item["productName"]),
        )[:limit]

    @classmethod
    def search_catalog(cls) -> list[dict[str, Any]]:
        products = cls.fetch_catalog()
        products.extend(cls.auxiliary_catalog())
        return unique_by(products, "productCode", "productName")

    @classmethod
    def fetch_catalog(cls) -> list[dict[str, Any]]:
        cached = cls._catalog_cache
        now = time.time()
        if cached and now - cached[0] < cls.CACHE_SECONDS:
            return [dict(item) for item in cached[1]]

        products: list[dict[str, Any]] = []
        for product_code, (category, fallback_name) in cls.PRODUCT_META.items():
            product = cls.fetch_product(product_code)
            if not product:
                continue
            item = cls.to_result(product_code, category, fallback_name, product)
            if item:
                products.append(item)

        cls._catalog_cache = (now, products)
        return [dict(item) for item in products]

    @classmethod
    def auxiliary_catalog(cls) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        for item in cls.AUXILIARY_PRODUCTS:
            product = dict(item)
            documents = cls.documents_from_auxiliary(product)
            product["provider"] = "hanwhafire"
            product["insurerName"] = "한화손해보험"
            product["documents"] = documents
            product["saleStartDate"] = None
            product["saleEndDate"] = None
            product["updatedAt"] = cls.extract_revision(product.get("productName")) or (documents[0]["revisionDate"] if documents else None)
            products.append(product)
        return products

    @classmethod
    def fetch_product(cls, product_code: str) -> dict[str, Any] | None:
        payload = json.dumps({"insGdcd": product_code}, ensure_ascii=False).encode("utf-8")
        raw = fetch_text(
            cls.api_url,
            method="POST",
            data=payload,
            headers={
                "Origin": cls.base,
                "Referer": cls.product_url(product_code),
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "X-SMT-Scr-Url": f"/product/catalog/product-info.do?insGdcd={product_code}",
            },
        )
        response = json.loads(raw)
        if response.get("code") not in {"00000", None}:
            return None
        payload_body = response.get("payload") or {}
        return payload_body.get("prdCmnInsGd") or None

    @classmethod
    def to_result(
        cls,
        product_code: str,
        category: str,
        fallback_name: str,
        product: dict[str, Any],
    ) -> dict[str, Any] | None:
        product_name = (product.get("insGdnm") or product.get("prsGdnm") or fallback_name).strip()
        if not product_name:
            return None

        documents = cls.documents_from_product(product_name, product)
        revision_date = documents[0]["revisionDate"] if documents else cls.extract_revision(product_name)
        return {
            "provider": "hanwhafire",
            "insurerName": "한화손해보험",
            "productName": product_name,
            "displayName": product.get("prsGdnm") or product.get("insGdDtnm") or fallback_name,
            "productCode": product_code,
            "insuranceType": category,
            "status": "판매중" if product.get("usYn") == "Y" else "판매중지",
            "sourceUrl": cls.product_url(product_code),
            "documents": documents,
            "saleStartDate": None,
            "saleEndDate": None,
            "updatedAt": revision_date,
            "officialSource": "한화손해보험 모바일 상품공시",
        }

    @classmethod
    def documents_from_product(cls, product_name: str, product: dict[str, Any]) -> list[dict[str, Any]]:
        document_path = product.get("insClaUrlAdr")
        if not document_path:
            return []
        filename = urllib.parse.unquote(str(document_path).rsplit("/", 1)[-1])
        revision_date = cls.extract_revision(filename) or cls.extract_revision(product_name)
        return [
            {
                "type": "보험약관",
                "title": filename or f"{product_name} 약관.pdf",
                "url": cls.official_file_url(str(document_path)),
                "revisionDate": revision_date,
                "saleStartDate": None,
                "saleEndDate": None,
                "format": "PDF",
            }
        ]

    @classmethod
    def documents_from_auxiliary(cls, item: dict[str, Any]) -> list[dict[str, Any]]:
        source_url = str(item.get("sourceUrl") or "")
        if not source_url.lower().endswith(".pdf"):
            return []
        term_url = cls.derive_terms_pdf_url(source_url)
        if not term_url or not cls.document_exists(term_url):
            return []
        revision_date = cls.extract_revision(item.get("productName"))
        title = urllib.parse.unquote(term_url.rsplit("/", 1)[-1])
        return [
            {
                "type": "보험약관",
                "title": title,
                "url": term_url,
                "revisionDate": revision_date,
                "saleStartDate": None,
                "saleEndDate": None,
                "format": "PDF",
            }
        ]

    @classmethod
    def derive_terms_pdf_url(cls, source_url: str) -> str | None:
        if not source_url.lower().endswith(".pdf"):
            return None
        if re.search(r"_03\.pdf$", source_url, flags=re.IGNORECASE):
            return source_url
        if re.search(r"_02\.pdf$", source_url, flags=re.IGNORECASE):
            return re.sub(r"_02\.pdf$", "_03.pdf", source_url, flags=re.IGNORECASE)
        return None

    @classmethod
    def document_exists(cls, url: str) -> bool:
        cached = cls._document_exists_cache.get(url)
        if cached is not None:
            return cached
        try:
            fetch_url(url, method="HEAD")
            exists = True
        except Exception:
            exists = False
        cls._document_exists_cache[url] = exists
        return exists

    @classmethod
    def official_file_url(cls, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return cls.file_base + urllib.parse.quote(path, safe="/%()_-.")

    @classmethod
    def product_url(cls, product_code: str) -> str:
        return f"{cls.source_url}?insGdcd={urllib.parse.quote(product_code)}"

    @staticmethod
    def extract_revision(value: str | None) -> str | None:
        if not value:
            return None
        match = re.search(r"(?<!\d)(20)?(\d{2})(0[1-9]|1[0-2])(?!\d)", value)
        if not match:
            return None
        year = match.group(2)
        month = match.group(3)
        return f"20{year}-{month}-01"


class HeungkukAdapter:
    base = "https://m.heungkukfire.co.kr"
    source_url = f"{base}/product/insr/CPDIS0001_M00/CPDIS0001_M00.do"
    list_page_url = f"{base}/product/insr/CPDIS0001_M10/CPDIS0001_M10.do"
    list_api_url = f"{base}/product/insr/CPDIS0001_M10/CPDIS0001_M10_S01.do?getInsGoodsList"
    detail_api_url = f"{base}/product/insr/CPDIS0001_M01/CPDIS0001_M01_S01.do?selectInsGoods"
    download_popup_url = f"{base}/product/insr/CPDIS0001_L13/CPDIS0001_L13.do"
    download_url = f"{base}/common/download.do"

    CATEGORIES = {
        "001": "의료/건강보험",
        "002": "자녀보험",
        "003": "운전자/상해보험",
        "004": "연금/저축보험",
        "005": "화재/재물보험",
        "006": "방카슈랑스",
        "007": "자동차보험",
        "008": "단체보험",
        "009": "여행/레저보험",
        "010": "다이렉트",
    }

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        opener, csrf = cls.open_session(cls.list_page_url)
        products: list[dict[str, Any]] = []
        for category_code, category_name in cls.CATEGORIES.items():
            response = cls.fetch_json(
                opener,
                cls.list_api_url,
                {"gubunCd": category_code, "gubunCd2": ""},
                referer=cls.list_page_url,
                csrf=csrf,
            )
            for item in response.get("resultInfoList", []):
                product_name = cls.product_name(item)
                if not product_name:
                    continue
                score = score_text(query, product_name, item.get("menuNm", ""), item.get("itemCd", ""), category_name)
                if score <= 0:
                    continue
                products.append(
                    {
                        "provider": "heungkuk",
                        "insurerName": "흥국화재",
                        "productName": product_name,
                        "productCode": str(item.get("seq") or ""),
                        "insuranceType": category_name,
                        "status": "판매중",
                        "sourceUrl": cls.detail_page_url(item.get("seq")),
                        "documents": [],
                        "saleStartDate": None,
                        "saleEndDate": None,
                        "updatedAt": item.get("uptDt") or item.get("regDt"),
                        "officialSource": "흥국화재 보험상품공시",
                        "score": score,
                    }
                )

        ranked = sorted(unique_by(products, "productCode", "productName"), key=result_sort_key)
        enriched: list[dict[str, Any]] = []
        for item in ranked[: expanded_limit(limit)]:
            detail = cls.fetch_detail(opener, csrf, item["productCode"])
            item["documents"] = cls.documents_from_detail(item["productCode"], detail)
            if detail.get("gubunCd"):
                item["insuranceType"] = cls.CATEGORIES.get(detail.get("gubunCd"), item["insuranceType"])
            enriched.append(item)
        return sorted(enriched, key=result_sort_key)[:limit]

    @classmethod
    def fetch_detail(cls, opener: urllib.request.OpenerDirector, csrf: str, seq: str) -> dict[str, Any]:
        response = cls.fetch_json(
            opener,
            cls.detail_api_url,
            {"seq": seq},
            referer=cls.detail_page_url(seq),
            csrf=csrf,
        )
        return response.get("result", {}) or {}

    @classmethod
    def documents_from_detail(cls, seq: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for doc_key, doc_type, label in [
            ("terms", "보험약관", "약관 다운로드"),
            ("advice", "상품안내장", "안내장 다운로드"),
        ]:
            prefix = "terms" if doc_key == "terms" else "advice"
            saved_name = detail.get(f"{prefix}FileNm")
            original_name = detail.get(f"{prefix}FileOrgNm")
            if not saved_name:
                continue
            params = urllib.parse.urlencode({"seq": seq, "doc": doc_key})
            documents.append(
                {
                    "type": doc_type,
                    "title": original_name or label,
                    "url": f"/api/heungkuk_download?{params}",
                    "revisionDate": cls.clean_revision(detail.get("uptDt") or detail.get("regDt")),
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "format": "PDF",
                }
            )
        return documents

    @classmethod
    def download_document(cls, seq: str, doc: str = "terms") -> tuple[bytes, str]:
        if doc not in {"terms", "advice"}:
            raise ValueError("지원하지 않는 문서 유형입니다.")

        opener, csrf = cls.open_session(cls.detail_page_url(seq))
        detail = cls.fetch_detail(opener, csrf, seq)
        prefix = "terms" if doc == "terms" else "advice"
        file_path = detail.get(f"{prefix}FilePath")
        file_name = detail.get(f"{prefix}FileNm")
        original_name = detail.get(f"{prefix}FileOrgNm") or file_name or "heungkuk_terms.pdf"
        if not file_path or not file_name:
            raise FileNotFoundError("흥국화재 공식 사이트에서 해당 문서를 찾지 못했습니다.")

        popup_html = cls.open_text(opener, cls.download_popup_url, referer=cls.detail_page_url(seq))
        popup_csrf = cls.extract_csrf(popup_html) or csrf
        form = urllib.parse.urlencode(
            {
                "_csrf": popup_csrf,
                "mode": "View",
                "filePath": file_path,
                "fileRealName": original_name,
                "fileSaveName": file_name,
                "desYn": "",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{cls.download_url}?temp={int(time.time() * 1000)}",
            data=form,
            method="POST",
            headers={
                "User-Agent": USER_AGENT,
                "Referer": cls.download_popup_url,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/pdf,application/octet-stream,*/*",
            },
        )
        with opener.open(request, timeout=30) as response:
            return response.read(), original_name

    @classmethod
    def fetch_json(
        cls,
        opener: urllib.request.OpenerDirector,
        url: str,
        payload: dict[str, Any],
        *,
        referer: str,
        csrf: str,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "User-Agent": USER_AGENT,
                "Referer": referer,
                "Origin": cls.base,
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-TOKEN": csrf,
                "Cache-Control": "no-cache",
            },
        )
        with opener.open(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8", errors="ignore"))

    @classmethod
    def open_session(cls, page_url: str) -> tuple[urllib.request.OpenerDirector, str]:
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        html = cls.open_text(opener, page_url)
        csrf = cls.extract_csrf(html)
        if not csrf:
            raise RuntimeError("흥국화재 공식 사이트의 CSRF 토큰을 확인하지 못했습니다.")
        return opener, csrf

    @classmethod
    def open_text(cls, opener: urllib.request.OpenerDirector, url: str, *, referer: str | None = None) -> str:
        headers = {"User-Agent": USER_AGENT}
        if referer:
            headers["Referer"] = referer
        request = urllib.request.Request(url, headers=headers)
        with opener.open(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="ignore")

    @staticmethod
    def extract_csrf(html: str) -> str | None:
        meta_match = re.search(r'name="_csrf"\s+content="([^"]+)"', html)
        if meta_match:
            return meta_match.group(1)
        input_match = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
        return input_match.group(1) if input_match else None

    @staticmethod
    def product_name(item: dict[str, Any]) -> str:
        parts = [item.get("goodsNm1"), item.get("goodsNm2"), item.get("goodsNm3")]
        name = "".join(part.strip() for part in parts if part)
        return name or (item.get("menuNm") or "").strip()

    @classmethod
    def detail_page_url(cls, seq: str | int | None) -> str:
        return f"{cls.base}/product/insr/CPDIS0001_M01/CPDIS0001_M01.do?seq={seq or ''}"

    @staticmethod
    def clean_revision(value: str | None) -> str | None:
        if not value:
            return None
        compact = re.sub(r"[^0-9]", "", value)
        if len(compact) < 8:
            return None
        return f"{compact[:4]}-{compact[4:6]}-{compact[6:8]}"


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


def search_all(raw_query: str, insurer_key: str | None = None) -> dict[str, Any]:
    context = parse_query(raw_query, insurer_key)
    provider_keys = [context.insurer_key] if context.insurer_key else ["kb", "db", "hyundai", "samsung", "lotte", "nhfire", "meritz", "heungkuk", "hanwhafire", "mg"]
    adapter_limit = 40
    results = []
    errors = []
    for provider_key in provider_keys:
        try:
            if provider_key == "kb":
                results.extend(KbAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "db":
                results.extend(DbAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "hyundai":
                results.extend(HyundaiAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "samsung":
                results.extend(SamsungAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "lotte":
                results.extend(LotteAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "nhfire":
                results.extend(NhFireLiveAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "meritz":
                results.extend(MeritzAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "heungkuk":
                results.extend(HeungkukAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "hanwhafire":
                results.extend(HanwhaFireAdapter.search(context.product_query, limit=adapter_limit))
            elif provider_key == "mg":
                results.extend(MgAdapter.search(context.product_query, limit=adapter_limit))
            else:
                results.extend(landing_result(provider_key, context.product_query))
        except Exception as exc:
            errors.append({"provider": INSURER_REGISTRY[provider_key]["name"], "message": str(exc)})

    final_results = finalize_results(results, context.product_query, limit=20)
    return {
        "query": raw_query,
        "parsedInsurer": context.insurer_name,
        "parsedProduct": context.product_query,
        "resultCount": len(final_results),
        "results": final_results,
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
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            insurer_key = params.get("insurer", [""])[0].strip() or None
            if not query:
                self.send_json({"error": "query is required"}, status=400)
                return
            self.send_json(search_all(query, insurer_key))
            return
        if parsed.path in {"/api/download/heungkuk", "/api/heungkuk_download", "/api/heungkuk-download"}:
            params = urllib.parse.parse_qs(parsed.query)
            seq = params.get("seq", [""])[0].strip()
            doc = params.get("doc", ["terms"])[0].strip() or "terms"
            if not seq:
                self.send_json({"error": "seq is required"}, status=400)
                return
            try:
                body, filename = HeungkukAdapter.download_document(seq, doc)
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=502)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path in {"/api/download/nhfire", "/api/nhfire_download", "/api/nhfire-download"}:
            params = urllib.parse.parse_qs(parsed.query)
            product_code = params.get("pdtCd", [""])[0].strip()
            file_id = params.get("fileId", [""])[0].strip()
            seq = params.get("seq", [""])[0].strip()
            preferred_name = params.get("name", ["nhfire.pdf"])[0].strip() or "nhfire.pdf"
            if not product_code or not seq:
                self.send_json({"error": "pdtCd and seq are required"}, status=400)
                return
            try:
                body, filename, content_type = NhFireLiveAdapter.download_document(product_code, seq, preferred_name, file_id)
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=502)
                return
            guessed_type = mimetypes.guess_type(filename)[0] or content_type or "application/pdf"
            self.send_response(200)
            self.send_header("Content-Type", guessed_type)
            self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path in {"/api/download/meritz", "/api/meritz_download", "/api/meritz-download"}:
            params = urllib.parse.parse_qs(parsed.query)
            product_code = params.get("productCode", [""])[0].strip()
            original_name = params.get("name", ["meritz.pdf"])[0].strip() or "meritz.pdf"
            if not product_code:
                self.send_json({"error": "productCode is required"}, status=400)
                return
            try:
                body, filename, content_type = MeritzAdapter.download_document(product_code, original_name)
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=502)
                return
            guessed_type = mimetypes.guess_type(filename)[0] or content_type or "application/pdf"
            self.send_response(200)
            self.send_header("Content-Type", guessed_type)
            self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path in {"/api/download/mg", "/api/mg_download", "/api/mg-download"}:
            params = urllib.parse.parse_qs(parsed.query)
            data_id = params.get("dataIdno", [""])[0].strip()
            doc_cfcd = params.get("docCfcd", [""])[0].strip()
            sale_flag = params.get("saleYn", ["0"])[0].strip() or "0"
            original_name = params.get("name", ["mg.pdf"])[0].strip() or "mg.pdf"
            if not data_id or not doc_cfcd:
                self.send_json({"error": "dataIdno and docCfcd are required"}, status=400)
                return
            try:
                body, filename, content_type = MgAdapter.download_document(data_id, doc_cfcd, sale_flag, original_name)
            except Exception as exc:
                self.send_json({"error": str(exc)}, status=502)
                return
            guessed_type = mimetypes.guess_type(filename)[0] or content_type or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", guessed_type)
            self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{urllib.parse.quote(filename)}")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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
