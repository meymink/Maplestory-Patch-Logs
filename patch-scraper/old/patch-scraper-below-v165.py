#!/usr/bin/env python3
"""
patch-scraper-below-v165.py – scrape MapleStory legacy patch-note pages (v140-v165).
Outputs JSON with __url__, __date__, __title__.
"""

import argparse, json, re, time, pathlib
from typing import Dict, List
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import OrderedDict

# ───────────────────── HTML fetch ─────────────────────
def fetch_rendered_html(url: str, timeout: int = 20) -> BeautifulSoup:
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

# ───────────────────── section parser ────────────────
EXCLUDE = {"overview", "gameplay", "rewards", "requirement",
           "beginner", "1st job", "2nd job", "3rd job", "4th job",
           "hyper skills"}

def parse_legacy_sections(soup: BeautifulSoup) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {}
    for h1 in soup.find_all("h1"):
        strong = h1.find("strong")
        if not strong:
            continue
        header = strong.get_text(strip=True)
        if header.lower().startswith("check out"):
            continue

        items = []
        for sib in h1.next_siblings:
            if isinstance(sib, Tag) and sib.name == "h1":
                break
            if isinstance(sib, Tag) and sib.name == "h3":
                st = sib.find("strong")
                if not st:
                    continue
                item = st.get_text(strip=True)
                if not item or item.lower() in EXCLUDE:
                    continue
                items.append(item)
        if items:
            sections[header] = items
    return sections

# ───────────────────── metadata helpers ──────────────
VERSION_RE = re.compile(r"\bv[.\-\s]?(\d{2,3})\b", re.I)

def extract_version(soup: BeautifulSoup, url: str) -> str:
    m = VERSION_RE.search(url)
    if not m and soup.title:
        m = VERSION_RE.search(soup.title.get_text())
    return f"v{m.group(1)}" if m else f"unknown_{int(time.time())}"

def extract_date(soup: BeautifulSoup) -> str:
    div = soup.find("div", class_="news-detail__live-date")
    return div.get_text(strip=True) if div else ""

TITLE_CLEAN_RE = re.compile(
    r"""
    ^\s*\[.*?\]\s*|
    ^\s*[Vv][.\s]?\d{1,3}\s*[–-]\s*|
    \s*(?:Patch\s*Notes|Update\s*Highlights)\s*$""",
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

# ───────────────────── main scrape ───────────────────
def scrape(url: str, out_dir: pathlib.Path, overwrite: bool):
    try:
        soup = fetch_rendered_html(url)
        body = parse_legacy_sections(soup)
        if not body:
            raise RuntimeError("No legacy sections found")

        version = extract_version(soup, url)
        date    = extract_date(soup)
        title   = extract_title(soup)

        data = OrderedDict()
        data["__url__"]   = url
        data["__date__"]  = date
        data["__title__"] = title
        data.update(body)

        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{version}.json"
        if out_file.exists() and not overwrite:
            print(f"⚠  {out_file.name} exists – skip (use --overwrite)")
            return
        out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓  {url}  →  {out_file}")
    except Exception as e:
        print(f"✗  {url} :: {e}")

# ───────────────────── CLI ───────────────────────────
def load_urls(path: pathlib.Path) -> List[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="Single patch-note URL")
    ap.add_argument("--url-file", default="patch-urls-below-v165.txt")
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
