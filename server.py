from __future__ import annotations

import json
import os
import re
import time
import http.cookiejar
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
        "type": "live",
        "official_url": "https://children.hi.co.kr/bin/CI/ON/CION3200G.jsp",
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

        ranked = sorted(
            aggregated,
            key=lambda item: (
                -item["score"],
                0 if item.get("status") == "판매중" else 1,
                item["productName"],
            ),
        )

        enriched: list[dict[str, Any]] = []
        for item in ranked[:limit]:
            documents = cls.fetch_documents(item["rawItem"], item["saleStartDate"], item["saleEndDate"])
            item["documents"] = documents
            enriched.append(item)
        return enriched

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
        products = []
        for item in cls.fetch_products():
            score = score_text(query, item["productName"], item["productCode"], item.get("insuranceType", ""))
            if score <= 0:
                continue
            item["score"] = score
            products.append(item)

        ranked = sorted(products, key=lambda item: (-item["score"], item["productName"]))
        enriched = []
        for item in ranked[:limit]:
            item["documents"] = cls.fetch_documents(item["documentProductCode"])
            enriched.append(item)
        return enriched

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
            params = urllib.parse.urlencode(
                {
                    "path": encrypted_path,
                    "id": encrypted_path,
                    "orgFileName": original_name,
                    "pdfView": "Y",
                }
            )
            documents.append(
                {
                    "type": doc_type,
                    "title": original_name,
                    "url": f"{cls.base}/hp/fileDownload.do?{params}",
                    "revisionDate": None,
                    "saleStartDate": None,
                    "saleEndDate": None,
                    "format": "PDF",
                }
            )
        return documents

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


class HanwhaFireAdapter:
    base = "https://m.hwgeneralins.com"
    file_base = "https://www.hwgeneralins.com"
    api_url = f"{base}/smt/prd/cmn/select-ins-gd-info"
    source_url = f"{base}/product/catalog/product-info.do"
    CACHE_SECONDS = 600
    _catalog_cache: tuple[float, list[dict[str, Any]]] | None = None

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

    @classmethod
    def search(cls, query: str, limit: int = 10) -> list[dict[str, Any]]:
        products = []
        for item in cls.fetch_catalog():
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

        ranked = sorted(unique_by(products, "productCode", "productName"), key=lambda item: (-item["score"], item["productName"]))
        enriched: list[dict[str, Any]] = []
        for item in ranked[:limit]:
            detail = cls.fetch_detail(opener, csrf, item["productCode"])
            item["documents"] = cls.documents_from_detail(item["productCode"], detail)
            if detail.get("gubunCd"):
                item["insuranceType"] = cls.CATEGORIES.get(detail.get("gubunCd"), item["insuranceType"])
            enriched.append(item)
        return enriched

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


def search_all(raw_query: str) -> dict[str, Any]:
    context = parse_query(raw_query)
    provider_keys = [context.insurer_key] if context.insurer_key else ["kb", "db", "hyundai", "meritz", "heungkuk", "hanwhafire"]
    results = []
    errors = []
    for provider_key in provider_keys:
        try:
            if provider_key == "kb":
                results.extend(KbAdapter.search(context.product_query))
            elif provider_key == "db":
                results.extend(DbAdapter.search(context.product_query))
            elif provider_key == "hyundai":
                results.extend(HyundaiAdapter.search(context.product_query))
            elif provider_key == "meritz":
                results.extend(MeritzAdapter.search(context.product_query))
            elif provider_key == "heungkuk":
                results.extend(HeungkukAdapter.search(context.product_query))
            elif provider_key == "hanwhafire":
                results.extend(HanwhaFireAdapter.search(context.product_query))
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
