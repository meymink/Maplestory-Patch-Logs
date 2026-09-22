#!/usr/bin/env python3
"""
patch-scraper.py – scrape MapleStory patch-note pages (modern layout).

• If no URL is given, reads URLs from patch-urls.txt.
• Outputs JSON into patch-jsons/v###.json with __url__, __date__, __title__.
"""

import argparse, json, re, time, pathlib
from typing import Dict, List
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ───────────────────── HTML fetch ─────────────────────
def fetch_rendered_html(url: str, timeout: int = 25) -> BeautifulSoup:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=opts)
    driver.get(url)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    html = driver.page_source
    driver.quit()
    return BeautifulSoup(html, "lxml")

# ───────────────────── navigation UL ───────────────────
def parse_modern_nav(soup: BeautifulSoup) -> Dict[str, List[str]]:
    for ul in soup.find_all("ul"):
        if ul.find("a", href=lambda h: h and h.startswith("#")):
            sections: Dict[str, List[str]] = {}
            current = None
            for el in ul.find_all(["strong", "a"], recursive=True):
                if el.name == "strong":
                    current = el.get_text(strip=True)
                    sections[current] = []
                elif el.name == "a" and current:
                    txt = el.get_text(strip=True)
                    if txt:
                        sections[current].append(txt)
            if sections:
                return sections
    return {}

# ───────────────────── metadata helpers ────────────────
VERSION_RE = re.compile(r"\bv[.\-\s]?(\d{3})\b", re.I)

def extract_version(soup: BeautifulSoup, url: str) -> str:
    m = VERSION_RE.search(url)
    if not m and soup.title:
        m = VERSION_RE.search(soup.title.get_text())
    return f"v{m.group(1)}" if m else f"unknown_{int(time.time())}"

def extract_date(soup: BeautifulSoup) -> str:
    div = soup.select_one("div.news-detail__live-date")
    return div.get_text(strip=True) if div else ""

TITLE_CLEAN_RE = re.compile(
    r"""
    ^\s*\[.*?\]\s*|                 # leading [Updated …]
    ^\s*[Vv][.\s]?\d{1,3}\s*[–-]\s* # leading version prefix
    |\s*(?:Patch\s*Notes|Update\s*Highlights)\s*$  # trailing words
    """,
    re.I | re.X,
)

def extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("h1.news-detail__title") or soup.find("h1")
    if not h1:
        return ""
    raw = h1.get_text(strip=True)

    # Step-by-step cleaning
    raw = re.sub(r"^\s*\[.*?\]\s*", "", raw)                   # remove [Updated ...]
    raw = re.sub(r"^\s*[Vv][.\s]?\d{1,3}\s*[–-]\s*", "", raw)  # remove version prefix and dash
    raw = re.sub(r"\s*(Patch\s*Notes|Update\s*Highlights)\s*$", "", raw, flags=re.I)  # remove trailing

    return raw.strip(" –-")

# ───────────────────── page parser ─────────────────────
def parse_page(soup: BeautifulSoup) -> Dict[str, List[str]]:
    return parse_modern_nav(soup) or {}

# ───────────────────── main scrape ─────────────────────
def scrape(url: str, out_dir: pathlib.Path, overwrite: bool):
    try:
        soup = fetch_rendered_html(url)
        body = parse_page(soup)
        version = extract_version(soup, url)
        date = extract_date(soup)
        title = extract_title(soup)

        # metadata first
        data = {"__url__": url, "__date__": date, "__title__": title, **body}

        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{version}.json"
        if out_file.exists() and not overwrite:
            print(f"⚠  {out_file.name} exists – skip (use --overwrite)")
            return
        out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓  {url}  →  {out_file}")
    except Exception as e:
        print(f"✗  {url}  :: {e}")

# ───────────────────── CLI ────────────────────────
def load_urls(path: pathlib.Path) -> List[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="Single patch-note URL")
    ap.add_argument("--url-file", default="patch-urls.txt")
    ap.add_argument("--out-dir", default="patch-jsons")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    urls = [args.url] if args.url else load_urls(pathlib.Path(args.url_file))
    if not urls:
        print("No URLs provided.")
        return

    out_dir = pathlib.Path(args.out_dir)
    for u in urls:
        scrape(u, out_dir, args.overwrite)

if __name__ == "__main__":
    main()