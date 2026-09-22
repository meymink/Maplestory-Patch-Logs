#!/usr/bin/env python3
import json
import pathlib
import re
from typing import Dict, List, Optional, Tuple

PATCH_DIR = pathlib.Path("patch-jsons")
OUTPUT_FILE = pathlib.Path("../README.md")

def extract_version_num(version: str) -> Tuple[int, int]:
    """Extracts major and minor version numbers as a tuple (major, minor)."""
    m = re.search(r"(\d+)(?:\.(\d+))?", version)
    if not m:
        return (0, 0)
    major = int(m.group(1))
    minor = int(m.group(2)) if m.group(2) else 0
    return (major, minor)

def format_patch_summary(version: str, date: Optional[str], url: Optional[str], title: Optional[str], sections: Dict[str, List]) -> str:
    date_part = f" ({date})" if date else ""
    title_part = f" - {title}" if title and title.upper() != "TITLE" else ""
    summary = f"{version}{date_part}{title_part}"
    md = [f"<details>\n  <summary>\n            {summary}\n  </summary>"]
    if url:
        md.append(f"\n  URL: {url}\n")

    def flatten_items(prefix: str, items):
        for item in items:
            if isinstance(item, dict):
                for k, v in item.items():
                    flatten_items(f"{prefix}: {k}", v)
            else:
                md.append(f"     - {prefix}: {item}")

    for section, items in sections.items():
        if section.startswith("__"):
            continue
        flatten_items(section, items)

    md.append("</details>\n")
    return "\n".join(md)


def load_patches(dir_path: pathlib.Path) -> List[Dict]:
    patches = []
    for file in dir_path.glob("*.json"):
        if file.name == "template.json":
            continue  # skip template.json
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            url = data.get("__url__", None)
            date = data.get("__date__", None)
            title = data.get("__title__", None)
            sections = {k: v for k, v in data.items() if not k.startswith("__")}
            version = file.stem
            patches.append({
                "version": version,
                "date": date,
                "url": url,
                "title": title,
                "sections": sections
            })
        except Exception as e:
            print(f"Warning: failed to load {file}: {e}")
    return patches


def extract_versions_from_readme(readme_path: pathlib.Path) -> List[str]:
    if not readme_path.exists():
        return []
    text = readme_path.read_text(encoding="utf-8")
    # Match lines like: <summary>   v235 (Aug 30, 2022) </summary>
    versions = re.findall(r"<summary>\s*([vV]?\d+(?:\.\d+)?)", text)
    return versions

def main():
    patches = load_patches(PATCH_DIR)
    existing_versions = set(extract_versions_from_readme(OUTPUT_FILE))

    # Filter out patches already in README
    new_patches = [p for p in patches if p["version"] not in existing_versions]

    if not new_patches:
        print("No new patches to add.")
        return

    # Sort new patches descending by version number
    new_patches.sort(
        key=lambda p: extract_version_num(p["version"]),
        reverse=True
    )

    new_md_blocks = [format_patch_summary(p["version"], p["date"], p["url"], p["title"], p["sections"]) for p in new_patches]
    new_content = "\n".join(new_md_blocks) + "\n"

    if OUTPUT_FILE.exists():
        old_text = OUTPUT_FILE.read_text(encoding="utf-8")
    else:
        old_text = ""

    combined = new_content + "\n\n" + old_text
    OUTPUT_FILE.write_text(combined, encoding="utf-8")
    print(f"Added {len(new_patches)} new patch(es) to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()