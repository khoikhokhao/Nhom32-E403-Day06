#!/usr/bin/env python3
"""
VinFast data crawler for RAG knowledge base.

What this script does:
1. Crawl VinFast pages from seed URLs (BFS by depth).
2. Extract text facts from HTML content.
3. Normalize records to the schema used by data.json.
4. Infer topic and tags for RAG retrieval.
5. Deduplicate + validate and write final JSON.

Usage examples:
  python data_crawler.py --output data.json
  python data_crawler.py --max-pages 120 --depth 2 --output data.json
  python data_crawler.py --seeds-file seeds.txt --merge-existing data.json --output data.new.json

Dependencies:
  pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# -----------------------------
# Config
# -----------------------------
DEFAULT_ALLOWED_DOMAINS = {
    "vinfastauto.com",
    "shop.vinfastauto.com",
}

DEFAULT_SEED_URLS = [
    "https://vinfastauto.com/",
    "https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien",
    "https://vinfastauto.com/vn_vi/thong-tin-bao-hanh",
    "https://shop.vinfastauto.com/vn_vi/dat-lich-dich-vu.html",
    "https://vinfastauto.com/vn_vi/tim-kiem-showroom-tram-sac",
    "https://vinfastauto.com/vn_vi/ve-chung-toi",
    "https://vinfastauto.com/vn_vi/privacy-policy",
    "https://vinfastauto.com/dieu-khoan-phap-ly",
    "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf6.html",
    "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf7.html",
    "https://shop.vinfastauto.com/vn_vi/car-vf8.html",
    "https://shop.vinfastauto.com/vn_vi/car-vf9.html",
    "https://shop.vinfastauto.com/vn_vi/dat-coc-xe-dien-vf3.html",
    "https://vinfastauto.com/vn_vi/dat-coc-xe-vf-mpv7",
    "https://shop.vinfastauto.com/vn_vi/vinfast-ecvan.html",
    "https://vinfastauto.com/vn_vi/minio-green",
    "https://vinfastauto.com/vn_vi/limo-green",
    "https://vinfastauto.com/vn_vi/herio-green",
    "https://shop.vinfastauto.com/vn_vi/nerio-green.html",
    "https://vinfastauto.com/huong-dan-sac-pin-o-to-dien-vinfast",
    "https://vinfastauto.com/vn_vi/xe-may-dien-vinfast-viper",
    "https://vinfastauto.com/vn_vi/xe-may-dien-vinfast-amio",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

TOPIC_KEYWORDS = {
    "buying": [
        "gia",
        "đặt cọc",
        "dat coc",
        "thong so",
        "quãng đường",
        "range",
        "mô men",
        "công suất",
        "pin",
        "kwh",
        "km",
        "eco",
        "plus",
    ],
    "charging": [
        "sạc",
        "sac",
        "charging",
        "trạm sạc",
        "charger",
        "kwh",
        "dc",
        "ac",
        "10%-70%",
    ],
    "safety": [
        "an toàn",
        "canh bao",
        "cảnh báo",
        "nhiệt độ",
        "quá nhiệt",
        "tai nạn",
        "khẩn cấp",
        "phanh",
    ],
    "maintenance": [
        "bảo hành",
        "bao hanh",
        "xưởng dịch vụ",
        "sửa chữa",
        "maintenance",
        "warranty",
        "service",
    ],
    "service": [
        "đặt lịch",
        "dat lich",
        "hotline",
        "hỗ trợ",
        "support",
        "showroom",
        "liên hệ",
    ],
    "policy": [
        "privacy",
        "dữ liệu cá nhân",
        "chính sách",
        "điều khoản",
        "pháp lý",
        "cookies",
    ],
    "about": [
        "tầm nhìn",
        "sứ mệnh",
        "giá trị cốt lõi",
        "về chúng tôi",
        "vinfast",
    ],
}

COMMON_TAG_HINTS = {
    "price": ["giá", "vnđ", "vnd", "gia"],
    "range": ["km", "quãng đường", "range", "lần sạc"],
    "charging": ["sạc", "charging", "kwh", "dc", "ac"],
    "warranty": ["bảo hành", "warranty"],
    "policy": ["privacy", "chính sách", "điều khoản", "pháp lý"],
    "hotline": ["hotline", "1900"],
    "support": ["hỗ trợ", "support"],
    "booking": ["đặt lịch", "booking"],
    "safety": ["an toàn", "cảnh báo", "khẩn cấp", "tai nạn"],
}

MODEL_TAGS = {
    "vf3",
    "vf5",
    "vf6",
    "vf7",
    "vf8",
    "vf9",
    "ec van",
    "minio green",
    "limo green",
    "herio green",
    "nerio green",
    "vf mpv 7",
    "viper",
    "amio",
    "e34",
}

SKIP_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".pdf",
    ".zip",
    ".rar",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".mp4",
    ".mp3",
}


# -----------------------------
# Data models
# -----------------------------
@dataclass
class CrawlPage:
    url: str
    depth: int


# -----------------------------
# Helpers
# -----------------------------
def now_iso_date() -> str:
    return dt.date.today().isoformat()


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:64].strip("-") or "item"


def path_slug(url: str) -> str:
    parsed = urlparse(url)
    raw = parsed.path.strip("/")
    if not raw:
        return "home"
    raw = raw.replace("/", "-")
    return slugify(raw)


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def is_html_like(url: str) -> bool:
    lower = url.lower().split("?", 1)[0]
    return not any(lower.endswith(ext) for ext in SKIP_EXTENSIONS)


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    path = re.sub(r"/+", "/", path)
    # Keep meaningful query params out for stability.
    return f"{scheme}://{netloc}{path}".rstrip("/") + ("/" if path == "/" else "")


def is_allowed_url(url: str, allowed_domains: Set[str]) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    if not is_html_like(url):
        return False
    domain = get_domain(url)
    return any(domain == d or domain.endswith("." + d) for d in allowed_domains)


def read_seed_file(path: str) -> List[str]:
    urls: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


def merge_seed_urls(seed_urls: List[str], existing_json_path: Optional[str]) -> List[str]:
    all_urls = list(seed_urls)
    if not existing_json_path or not os.path.exists(existing_json_path):
        return all_urls

    try:
        with open(existing_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for doc in data.get("documents", []):
            url = doc.get("url")
            if isinstance(url, str) and url:
                all_urls.append(url)
    except Exception as exc:
        print(f"[WARN] Cannot read existing data for seed merge: {exc}")

    dedup = []
    seen = set()
    for url in all_urls:
        c = canonicalize_url(url)
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    return dedup


def fetch_page(session: requests.Session, url: str, timeout: int) -> Optional[str]:
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code != 200:
            print(f"[SKIP] {url} -> HTTP {resp.status_code}")
            return None
        content_type = resp.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            print(f"[SKIP] {url} -> Content-Type not HTML ({content_type})")
            return None
        return resp.text
    except requests.RequestException as exc:
        print(f"[SKIP] {url} -> Request error: {exc}")
        return None


def extract_links(html: str, base_url: str, allowed_domains: Set[str]) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        absolute = urljoin(base_url, href)
        canonical = canonicalize_url(absolute)
        if is_allowed_url(canonical, allowed_domains):
            links.append(canonical)

    out: List[str] = []
    seen = set()
    for link in links:
        if link not in seen:
            seen.add(link)
            out.append(link)
    return out


def extract_page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = normalize_space(soup.title.string)
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = normalize_space(h1.get_text(" ", strip=True))
    return title or "VinFast"


def extract_candidate_lines(html: str) -> List[str]:
    """
    Pull visible candidate text units and split into factual lines.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "canvas"]):
        tag.decompose()

    parts: List[str] = []
    for node in soup.select("h1,h2,h3,p,li,td,th"):
        text = normalize_space(node.get_text(" ", strip=True))
        if text:
            parts.append(text)

    whole = "\n".join(parts)
    raw_lines = re.split(r"[\n\r]+|(?<=[\.\!\?;:])\s+", whole)

    cleaned = []
    for line in raw_lines:
        line = normalize_space(line)
        if len(line) < 20:
            continue
        if len(line) > 350:
            continue
        cleaned.append(line)

    # Keep unique order.
    out = []
    seen = set()
    for line in cleaned:
        key = line.lower()
        if key not in seen:
            seen.add(key)
            out.append(line)
    return out


def looks_like_fact(line: str) -> bool:
    lower = line.lower()

    has_number = bool(re.search(r"\d", line))
    has_unit = bool(
        re.search(r"km|kwh|kw|nm|hp|vnđ|vnd|%|phút|năm|year|w", lower)
    )
    has_keyword = any(
        kw in lower
        for kw in [
            "giá",
            "bảo hành",
            "quãng đường",
            "sạc",
            "pin",
            "hotline",
            "privacy",
            "điều khoản",
            "công suất",
            "mô men",
            "thời gian",
            "dịch vụ",
            "showroom",
            "hỗ trợ",
            "chính sách",
        ]
    )
    return (has_number and (has_unit or has_keyword)) or has_keyword


def infer_topic(text: str, url: str) -> str:
    lower = text.lower()
    url_lower = url.lower()

    # URL hints first because pages often have specific purpose.
    url_hint_map = {
        "privacy": "policy",
        "phap-ly": "policy",
        "dieu-khoan": "policy",
        "bao-hanh": "maintenance",
        "dich-vu": "service",
        "tram-sac": "charging",
        "sac-pin": "charging",
        "ve-chung-toi": "about",
        "car-vf": "buying",
        "dat-coc": "buying",
    }
    for hint, topic in url_hint_map.items():
        if hint in url_lower:
            return topic

    scores = {k: 0 for k in TOPIC_KEYWORDS}
    for topic, kws in TOPIC_KEYWORDS.items():
        for kw in kws:
            if kw in lower:
                scores[topic] += 1

    best_topic = max(scores.items(), key=lambda x: x[1])[0]
    if scores[best_topic] == 0:
        return "service"
    return best_topic


def infer_tags(text: str, topic: str) -> List[str]:
    lower = text.lower()
    tags = [topic]

    for model in MODEL_TAGS:
        if model in lower:
            tags.append(model)

    # Normalize VF references like VF 6 -> vf6
    for m in re.findall(r"vf\s*([0-9]{1,2})", lower):
        tags.append(f"vf{m}")

    for tag, hints in COMMON_TAG_HINTS.items():
        if any(h in lower for h in hints):
            tags.append(tag)

    if "eco" in lower:
        tags.append("eco")
    if "plus" in lower:
        tags.append("plus")
    if "trạm sạc" in lower:
        tags.append("trạm sạc")
    if "xe máy điện" in lower:
        tags.append("xe máy điện")

    out = []
    seen = set()
    for tag in tags:
        tag = normalize_space(tag.lower())
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)

    return out[:10]


def build_doc_id(url: str, snippet: str) -> str:
    slug = path_slug(url)
    short_hash = hashlib.sha1(snippet.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{short_hash}"


def build_snippet(line: str) -> str:
    # Keep one line per record to stay aligned with current KB style.
    return normalize_space(line)


def validate_document(doc: Dict[str, object]) -> Tuple[bool, str]:
    required = ["id", "sourceTitle", "url", "topic", "tags", "snippet", "updatedAt"]
    for key in required:
        if key not in doc:
            return False, f"missing field: {key}"

    if not isinstance(doc["tags"], list) or not doc["tags"]:
        return False, "tags must be non-empty list"

    if not isinstance(doc["snippet"], str) or len(doc["snippet"].strip()) < 20:
        return False, "snippet too short"

    return True, "ok"


# -----------------------------
# Pipeline
# -----------------------------
def crawl_pages(
    seeds: List[str],
    allowed_domains: Set[str],
    max_pages: int,
    max_depth: int,
    timeout: int,
) -> Dict[str, str]:
    """
    Returns {url: html} for crawled pages.
    """
    queue: deque[CrawlPage] = deque()
    visited: Set[str] = set()
    pages: Dict[str, str] = {}

    for s in seeds:
        c = canonicalize_url(s)
        if is_allowed_url(c, allowed_domains):
            queue.append(CrawlPage(c, 0))

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while queue and len(pages) < max_pages:
        current = queue.popleft()
        if current.url in visited:
            continue
        visited.add(current.url)

        html = fetch_page(session, current.url, timeout=timeout)
        if html is None:
            continue

        pages[current.url] = html
        print(f"[OK] Crawled ({len(pages)}/{max_pages}) depth={current.depth}: {current.url}")

        if current.depth >= max_depth:
            continue

        for link in extract_links(html, current.url, allowed_domains):
            if link not in visited:
                queue.append(CrawlPage(link, current.depth + 1))

    return pages


def extract_documents_from_page(url: str, html: str, date_str: str) -> List[Dict[str, object]]:
    title = extract_page_title(html)
    lines = extract_candidate_lines(html)

    docs: List[Dict[str, object]] = []
    for line in lines:
        if not looks_like_fact(line):
            continue

        snippet = build_snippet(line)
        topic = infer_topic(snippet, url)
        tags = infer_tags(snippet, topic)
        doc_id = build_doc_id(url, snippet)

        doc: Dict[str, object] = {
            "id": doc_id,
            "sourceTitle": title,
            "url": url,
            "topic": topic,
            "tags": tags,
            "snippet": snippet,
            "updatedAt": date_str,
        }

        ok, reason = validate_document(doc)
        if ok:
            docs.append(doc)
        else:
            print(f"[SKIP] invalid doc from {url}: {reason}")

    return docs


def dedupe_documents(docs: Iterable[Dict[str, object]]) -> List[Dict[str, object]]:
    # Dedupe by (url, snippet_lower) first, then by id fallback.
    seen_pairs = set()
    seen_ids = set()
    out = []

    for doc in docs:
        url = str(doc.get("url", ""))
        snippet = str(doc.get("snippet", "")).lower()
        doc_id = str(doc.get("id", ""))
        pair = (url, snippet)

        if pair in seen_pairs:
            continue
        if doc_id in seen_ids:
            continue

        seen_pairs.add(pair)
        seen_ids.add(doc_id)
        out.append(doc)

    return out


def merge_existing_docs(
    existing_path: Optional[str],
    new_docs: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    if not existing_path or not os.path.exists(existing_path):
        return new_docs

    try:
        with open(existing_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        existing_docs = existing.get("documents", [])
        if not isinstance(existing_docs, list):
            existing_docs = []
    except Exception as exc:
        print(f"[WARN] Cannot parse existing file for merge: {exc}")
        existing_docs = []

    merged = []
    merged.extend(existing_docs)
    merged.extend(new_docs)
    return dedupe_documents(merged)


def sort_documents(docs: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return sorted(
        docs,
        key=lambda d: (
            str(d.get("topic", "")),
            str(d.get("sourceTitle", "")),
            str(d.get("id", "")),
        ),
    )


def run_pipeline(args: argparse.Namespace) -> None:
    date_str = now_iso_date()

    seed_urls = list(DEFAULT_SEED_URLS)
    if args.seeds_file:
        file_seeds = read_seed_file(args.seeds_file)
        seed_urls.extend(file_seeds)

    seed_urls = merge_seed_urls(seed_urls, args.merge_existing)

    print("[INFO] Seed URLs:", len(seed_urls))
    print("[INFO] Max pages:", args.max_pages)
    print("[INFO] Max depth:", args.depth)

    pages = crawl_pages(
        seeds=seed_urls,
        allowed_domains=set(DEFAULT_ALLOWED_DOMAINS),
        max_pages=args.max_pages,
        max_depth=args.depth,
        timeout=args.timeout,
    )

    all_docs: List[Dict[str, object]] = []
    for url, html in pages.items():
        all_docs.extend(extract_documents_from_page(url, html, date_str))

    all_docs = dedupe_documents(all_docs)
    all_docs = merge_existing_docs(args.merge_existing, all_docs)
    all_docs = sort_documents(all_docs)

    output = {
        "updatedAt": date_str,
        "documents": all_docs,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Wrote {len(all_docs)} documents -> {args.output}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="VinFast crawler -> normalized RAG JSON")
    p.add_argument(
        "--output",
        default="data.crawled.json",
        help="Output JSON path (default: data.crawled.json)",
    )
    p.add_argument(
        "--seeds-file",
        default="",
        help="Optional text file containing one URL per line",
    )
    p.add_argument(
        "--merge-existing",
        default="",
        help="Optional existing JSON file to merge with",
    )
    p.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Maximum number of pages to crawl",
    )
    p.add_argument(
        "--depth",
        type=int,
        default=1,
        help="BFS crawl depth from seeds",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP timeout seconds",
    )
    return p


if __name__ == "__main__":
    parser = build_arg_parser()
    cli_args = parser.parse_args()
    run_pipeline(cli_args)
