---

# MapleStory Patch Notes Scraper & Formatter

This repository contains Python scripts to scrape MapleStory patch notes from Nexon's website, extract useful information, and convert it into nicely formatted markdown for easy viewing in a `README.md`.

---

## Files Overview

### 1. `patch-scraper.py`

* **Purpose:** Scrapes **modern** MapleStory patch note pages.
* **Features:**

  * Fetches the fully rendered HTML using Selenium.
  * Parses patch notes navigation into grouped sections.
  * Extracts patch version, date, and source URL.
  * Saves output as JSON files named by patch version, e.g. `v237.json`.
  * Skips existing files unless `--overwrite` is specified.
* **Usage:**

  ```
  python patch-scraper.py https://www.nexon.com/maplestory/news/update/13495/v-150-rising-heroes-elite-patch-notes
  ```

  Or supply a file with URLs (`patch-urls.txt`) and run:

  ```
  python patch-scraper.py --url-file patch-urls.txt
  ```

---

### 2. `patch-scraper-below-v165.py`

* **Purpose:** Scrapes **legacy** MapleStory patch notes pages with older HTML layout.
* **Features:**

  * Similar functionality to `patch-scraper.py` but uses a different parser suited for older page structures.
  * Extracts patch version, date, and URL.
  * Outputs JSON with the same format as the modern scraper.
* **Usage:** Same as `patch-scraper.py`.

---

### 3. `json-to-md.py`

* **Purpose:** Converts JSON patch files from the scrapers into markdown format and appends them to a `README.md`.
* **Features:**

  * Reads all JSON patch files from `patch-jsons/`.
  * Prevents duplicate patches in `README.md`.
  * Formats each patch inside a collapsible `<details>` block.
  * Includes patch version, date (formatted like `v237 (Nov 15, 2022)`), and URL.
  * Entries are grouped by category and indented with consistent spacing.
  * Appends new patches at the **top** of the existing `README.md`.
* **Usage:**

  ```
  python json-to-md.py
  ```

---

## Requirements

* Python 3.8+
* Packages:

  * `beautifulsoup4`
  * `selenium`
  * `lxml`

Install dependencies via pip:

```
pip install beautifulsoup4 selenium lxml
```

* ChromeDriver must be installed and accessible in your system PATH for Selenium to work.

---

## Workflow Example

1. Collect patch note URLs into `patch-urls.txt`.

2. Run the scraper to download and parse patch notes:

   ```
   python patch-scraper.py --url-file patch-urls.txt
   ```

3. Convert the JSON outputs to markdown and update your `README.md`:

   ```
   python json-to-md.py
   ```

4. Open `README.md` to browse your formatted patch notes.

---

## Notes

* JSON files include extra fields `__url` and `__date` to support markdown formatting.
* The scrapers automatically detect patch version and release date from the page.
* The markdown output is optimized for easy reading with collapsible sections per patch.


*this whole directory was made by chatgpt lol*

---
