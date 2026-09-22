#!/usr/bin/env python3
"""
patch-scraper.py – scrape MapleStory patch-note pages (current Nexon layout).

• If no URL is given, reads URLs from patch-urls.txt.
• Outputs JSON into patch-jsons/v###.json with __url__, __date__, __title__.
"""

import argparse
import json
import pathlib
import re
import time
import traceback
from typing import Any, Dict, List, Union

from bs4 import BeautifulSoup
from bs4.element import Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


DEFAULT_URL_FILE = "patch-urls.txt"
DEFAULT_OUTPUT_DIR = "patch-jsons"
DEBUG_DIR = "debug"


# ───────────────────── HTML fetch ─────────────────────
def fetch_rendered_html(url: str, timeout: int = 30) -> BeautifulSoup:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    opts.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(timeout)

    try:
        driver.get(url)

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Allow Nexon Vue/CMS content to finish rendering
        time.sleep(5)

        return BeautifulSoup(driver.page_source, "lxml")

    except Exception:
        print("⚠ Timeout/error loading page")
        return BeautifulSoup(driver.page_source, "lxml")

    finally:
        driver.quit()


# ───────────────────── navigation UL ───────────────────
def parse_modern_nav(soup: BeautifulSoup) -> Dict[str, Any]:
    toc = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3"]
        and "TABLE OF CONTENTS" in tag.get_text(strip=True).upper()
    )

    if toc:
        ul = toc.find_next("ul")
    else:
        ul = soup.find("ul")

    if not ul:
        return {}

    sections = {}

    for li in ul.find_all("li", recursive=False):
        span = li.find("span", recursive=False)

        if span:
            strong = span.find("strong", recursive=False)
        else:
            strong = li.find("strong", recursive=False)

        if strong:
            section_title = strong.get_text(strip=True)
            sections[section_title] = []

            nested_ul = li.find("ul", recursive=False)
            if nested_ul:
                sections[section_title] = parse_nav_items(nested_ul)

    return sections


def parse_nav_items(ul_tag: Tag) -> List[Union[str, dict]]:
    """
    Recursively parse <ul> of TOC items into list.

    Each <li> can be:
    - a link (string)
    - or a nested dict if contains nested ul
    """

    items = []

    for li in ul_tag.find_all("li", recursive=False):
        a = li.find("a", recursive=False)
        nested_ul = li.find("ul", recursive=False)

        if a and nested_ul:
            key = a.get_text(strip=True)
            items.append({key: parse_nav_items(nested_ul)})

        elif a:
            items.append(a.get_text(strip=True))

        elif nested_ul:
            items.extend(parse_nav_items(nested_ul))

        else:
            text = li.get_text(strip=True)
            if text:
                items.append(text)

    return items


# ───────────────────── metadata helpers ────────────────
VERSION_RE = re.compile(r"\bv[.\-\s]?(\d{3})\b", re.I)


def extract_version(soup: BeautifulSoup, url: str) -> str:
    m = VERSION_RE.search(url)

    if not m and soup.title:
        m = VERSION_RE.search(soup.title.get_text())

    return f"v{m.group(1)}" if m else f"unknown_{int(time.time())}"


def extract_date(soup: BeautifulSoup) -> str:
    div = soup.select_one(".news-detail__live-date")

    if div:
        return div.get_text(strip=True)

    meta = soup.find("meta", property="article:published_time")

    if meta:
        return meta.get("content", "")

    return ""


def extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.select_one("h1.news-detail__title") or soup.find("h1")

    if not h1:
        return ""

    raw = h1.get_text(strip=True)

    # Remove [Updated ...]
    raw = re.sub(r"^\s*\[.*?\]\s*", "", raw)

    # Remove version prefix
    raw = re.sub(
        r"^\s*[Vv][.\s]?\d{1,3}\s*[-–]?\s*",
        "",
        raw
    )

    # Remove trailing labels
    raw = re.sub(
        r"\s*(Patch\s*Notes|Update\s*Highlights)\s*$",
        "",
        raw,
        flags=re.I
    )

    return raw.strip(" –-")


# ───────────────────── page parser ─────────────────────
def parse_page(soup: BeautifulSoup) -> Dict[str, Any]:
    content = (
        soup.select_one(".fr-view")
        or soup.select_one(".news-detail__content")
        or soup.select_one(".cms-html-wrapper")
        or soup
    )

    return parse_modern_nav(content) or {}


# ───────────────────── main scrape ─────────────────────
def scrape(
    url: str,
    out_dir: pathlib.Path,
    overwrite: bool,
    debug: bool
):
    try:
        soup = fetch_rendered_html(url)

        version = extract_version(soup, url)

        if debug:
            debug_dir = pathlib.Path(DEBUG_DIR)
            debug_dir.mkdir(exist_ok=True)

            debug_file = debug_dir / f"{version}.html"

            debug_file.write_text(
                str(soup),
                encoding="utf-8"
            )

            print(f"✓ Saved {debug_file}")

        body = parse_page(soup)
        date = extract_date(soup)
        title = extract_title(soup)

        data = {
            "__url__": url,
            "__date__": date,
            "__title__": title,
            **body
        }

        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"{version}.json"

        if out_file.exists() and not overwrite:
            print(
                f"⚠ {out_file.name} exists – skip "
                "(use --overwrite)"
            )
            return

        out_file.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        print(
            f"✓ {version} | "
            f"{title} | "
            f"{len(body)} sections → {out_file}"
        )

    except Exception as e:
        print(f"✗ {url}")
        print(f"  Error: {e}")

        if debug:
            traceback.print_exc()


# ───────────────────── CLI ────────────────────────
def load_urls(path: pathlib.Path) -> List[str]:
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "url",
        nargs="?",
        help="Single patch-note URL"
    )

    ap.add_argument(
        "--url-file",
        default=DEFAULT_URL_FILE
    )

    ap.add_argument(
        "--out-dir",
        default=DEFAULT_OUTPUT_DIR
    )

    ap.add_argument(
        "--overwrite",
        action="store_true"
    )

    ap.add_argument(
        "--debug",
        action="store_true"
    )

    args = ap.parse_args()

    urls = (
        [args.url]
        if args.url
        else load_urls(pathlib.Path(args.url_file))
    )

    if not urls:
        print("No URLs provided.")
        return

    out_dir = pathlib.Path(args.out_dir)

    for url in urls:
        scrape(
            url,
            out_dir,
            args.overwrite,
            args.debug
        )


if __name__ == "__main__":
    main()