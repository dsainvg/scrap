"""
main_data.py — Entry point for the IIT Kharagpur course page analysis pipeline.

All logic lives in utils/course_analyzer.py (reusable everywhere).
The AI prompt template lives in prompts/course_page_analysis.txt.

Usage
-----
    python main_data.py

Output: data/courses_output.csv  |  logs/main_data.log
"""

from __future__ import annotations

import logging
import os
import sys
import time

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path setup — ensures utils/ and setup/ resolve from any working directory
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# ---------------------------------------------------------------------------
# Logging (before importing utils so handlers are in place)
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/main_data.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import the reusable pipeline from utils
# ---------------------------------------------------------------------------
from utils.course_analyzer import (   # noqa: E402
    OUTPUT_CSV,INPUT_CSV,
    process_url,
    write_csv,
    load_data,
)


def main() -> None:
    """Entry point: process all target URLs and write the CSV database."""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # ── Sample URLs — replace or extend as needed ──────────────────────────
    urls: list[str] = load_data(path=INPUT_CSV)  # loads from OUTPUT_CSV, or replace with a hardcoded list
    rows: list[dict] = []
    failed: list[str] = []

    for url in urls:
        result = process_url(url)
        if result is None:
            failed.append(url)
        else:
            rows.append(result)
        time.sleep(1)  # polite delay between requests

    write_csv(rows, OUTPUT_CSV)

    # ── Summary ────────────────────────────────────────────────────────────
    recheck_count = sum(1 for r in rows if r.get("recheck_needed"))
    conflict_count = sum(1 for r in rows if r.get("conflict_flag"))
    useful_count = sum(1 for r in rows if r.get("is_useful"))
    not_useful_count = len(rows) - useful_count
    syllabus_only_count = sum(
        1 for r in rows
        if not r.get("is_useful") and r.get("has_syllabus_or_logistics")
    )

    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Total URLs attempted : {len(urls)}")
    print(f"Successfully processed: {len(rows)}")
    print(f"Failed (no HTML)     : {len(failed)}")
    print(f"Conflicts flagged    : {conflict_count}")
    print(f"Recheck needed       : {recheck_count}")
    print(f"Useful pages found   : {useful_count}")
    print(f"Not-useful pages     : {not_useful_count}")
    print(f"  ↳ Syllabus/logistics only (no materials): {syllabus_only_count}")
    print(f"Output written to    : {OUTPUT_CSV}")
    print("=" * 60)

    if failed:
        print("\nFailed URLs:")
        for u in failed:
            print(f"  - {u}")


if __name__ == "__main__":
    main()
