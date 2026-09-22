#!/usr/bin/env python3
"""
patch-scraper-wayback.py — Scrape MapleStory patch notes from Wayback URLs.

• Supports single URL or batch via patch-urls-wayback.txt
• Extracts:
  - __url__
  - __date__   (e.g. Jun 19, 2013)
  - __title__  (e.g. Unleashed)
  - Patch section TOC items
• Outputs JSON to patch-jsons/vXXX.json
"""

import argparse, json, re, time
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import requests
from bs4 import BeautifulSoup, Tag

# ───────────────────── fetch + utilities ─────────────────────
def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def version_from(url: str, soup: BeautifulSoup) -> str:
    m = re.search(r"\bv[.\-\s]?(\d{3})\b", url, re.I) \
        or (soup.title and re.search(r"\bv[.\-\s]?(\d{3})\b", soup.title.get_text(), re.I))
    return f"v{m.group(1)}" if m else f"unknown_{int(time.time())}"

def title_from(soup: BeautifulSoup) -> str:
    hdr = soup.find("div", id="m-news-detail-header")
    if hdr:
        h4 = hdr.find("h4")
        if h4:
            title = h4.get_text(strip=True)
            title = re.sub(r"^v[.\-\s]?\d+\s*-\s*", "", title, flags=re.I)
            title = re.sub(r"\s*Update Notes$", "", title, flags=re.I)
            return title.strip()
    return "Untitled"

def date_from(soup: BeautifulSoup, url: str) -> str:
    hdr = soup.find("div", id="m-news-detail-header")
    if hdr:
        info = hdr.find("div", class_="info")
        if info:
            m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", info.get_text())
            if m:
                dt = datetime.strptime(m.group(1), "%m/%d/%Y")
                return dt.strftime("%b %d, %Y")
    # fallback to Wayback timestamp
    m = re.search(r"/web/(\d{14})/", url)
    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").strftime("%b %d, %Y") if m else "Unknown"

# ───────────────────── TOC scraper ─────────────────────
def parse_wayback_toc(soup: BeautifulSoup) -> dict:
    """
    Handles legacy TOCs with either:
    - <p><b>Header</b></p><ul>…</ul>
    - or <p><b>Header</b><ul>…</ul></p>
    Stops parsing when layout changes (e.g. hits a <div class="hr">).
    """
    toc_start = soup.find("h1", string=re.compile("Table of Contents", re.I))
    if not toc_start:
        raise RuntimeError("Couldn't find Table of Contents heading.")

    result = {}
    el = toc_start

    while el:
        el = el.find_next_sibling()
        if not el or el.name == "h1":
            break
        if isinstance(el, Tag) and el.name == "div" and "hr" in el.get("class", []):
            break  # Stop after ToC section

        if el.name == "p":
            b = el.find("b")
            if not b:
                continue
            section = b.get_text(strip=True)

            # Option 1: inline <ul> inside <p>
            inline_ul = el.find("ul")
            if inline_ul:
                items = [li.get_text(strip=True) for li in inline_ul.find_all("li")]
                if items:
                    result[section] = items
                continue

            # Option 2: next sibling <ul>
            next_ul = el.find_next_sibling()
            while next_ul and next_ul.name != "ul":
                if next_ul.name and next_ul.name.startswith("h"):
                    break
                next_ul = next_ul.find_next_sibling()

            if next_ul and next_ul.name == "ul":
                items = [li.get_text(strip=True) for li in next_ul.find_all("li")]
                if items:
                    result[section] = items

    if not result:
        raise RuntimeError("No TOC sections found.")

    return result

def parse_headings_as_toc(soup: BeautifulSoup) -> dict:
    """
    Fallback if no ToC found: use top-level <h1> headings as sections.
    """
    headers = soup.find_all("h1")
    if not headers or len(headers) < 2:
        raise RuntimeError("Not enough headings to infer TOC.")

    result = {}
    for h in headers[1:]:  # skip the first title h1
        text = h.get_text(strip=True)
        if text and len(text) < 80:
            result[text] = []
    return result


# ───────────────────── scrape & write ─────────────────────
def scrape(url: str, out_dir: Path, overwrite: bool):
    soup = fetch(url)
    try:
        toc = parse_wayback_toc(soup)
    except RuntimeError:
        toc = parse_headings_as_toc(soup)

    if not toc:
        raise RuntimeError("No TOC sections found")

    data = {
        "__url__": url,
        "__date__": date_from(soup, url),
        "__title__": title_from(soup),
        **toc
    }

    version = version_from(url, soup)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{version}.json"
    if out_file.exists() and not overwrite:
        print(f"⚠  {out_file.name} exists – skipping (use --overwrite)")
        return

    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓  {url} → {out_file}")

# ───────────────────── CLI + batch ─────────────────────
def load_urls(path: Path) -> List[str]:
    return [
        ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="Single Wayback patch URL (optional)")
    ap.add_argument("--url-file", default="patch-urls-wayback.txt", help="URL list (default: patch-urls-wayback.txt)")
    ap.add_argument("--out-dir", default="patch-jsons", help="Output directory")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing JSON")
    args = ap.parse_args()

    urls = [args.url] if args.url else load_urls(Path(args.url_file))
    if not urls:
        print("No URLs provided.")
        return

    for u in urls:
        try:
            scrape(u, Path(args.out_dir), args.overwrite)
        except Exception as e:
            print(f"✗  {u} :: {e}")

if __name__ == "__main__":
    main()
