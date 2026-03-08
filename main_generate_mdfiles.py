#!/usr/bin/env python3
"""
main_generate_mdfiles.py - Generate per-course markdown files from cleaned CSV.

This script reads the cleaned course links CSV, groups them by course_code
(then by course_title for remaining, then singletons), sorts each group by
year (newest first), extracts learning materials (slides, question papers,
tutorials, example code), and writes markdown files following docsourous
conventions.

All reusable logic lives in utils/markdown_generator.py.
The LLM prompt template lives in prompts/markdown_extraction.txt.

Usage
-----
    python main_generate_mdfiles.py
    python main_generate_mdfiles.py --input data/courses_cleaned.csv
    python main_generate_mdfiles.py --no-llm  # use only heuristics
    python main_generate_mdfiles.py --test    # test mode with limited URLs
    python main_generate_mdfiles.py --limit 5 # process only 5 URLs

Output: data/markdowns/md/<course_code>.md  |  logs/generate_mdfiles.log

Model: meta/llama-3.1-70b-instruct (via NVIDIA API)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path setup - ensures utils/ and setup/ resolve from any working directory
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/generate_mdfiles.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import utilities
# ---------------------------------------------------------------------------
from utils.markdown_generator import (  # noqa: E402
    MARKDOWN_OUTPUT_DIR,
    DEFAULT_INPUT_CSV,
    load_grouped_links,
    process_groups,
)


def main(argv: list[str] | None = None) -> int:
    """Entry point for markdown generation pipeline."""
    parser = argparse.ArgumentParser(
        description="Generate per-course markdown files from cleaned CSV."
    )
    parser.add_argument(
        "--input", "-i",
        default=DEFAULT_INPUT_CSV,
        help=f"Input CSV path (default: {DEFAULT_INPUT_CSV})"
    )
    parser.add_argument(
        "--output", "-o",
        default=MARKDOWN_OUTPUT_DIR,
        help=f"Output directory for markdown files (default: {MARKDOWN_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--no-llm",
        dest="use_llm",
        action="store_false",
        help="Disable LLM extraction; use only heuristics"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: process only first 3 groups"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of groups to process (0 = no limit)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run: show what would be processed without making API calls"
    )
    args = parser.parse_args(argv)
    
    # Test mode defaults
    if args.test:
        args.limit = args.limit or 3
        logger.info("TEST MODE: Processing limited groups")
    
    # Validate input file
    if not os.path.exists(args.input):
        # Try fallback paths
        fallbacks = [
            "data/courses_cleaned.csv",
            "data/courses_output_cleaned.csv",
            "data/courses_output.csv",
            "data/unique_course_urls.csv",
        ]
        found = None
        for fb in fallbacks:
            if os.path.exists(fb):
                found = fb
                break
        
        if found:
            logger.info(f"Input file {args.input} not found, using fallback: {found}")
            args.input = found
        else:
            logger.error(f"Input file not found: {args.input}")
            logger.error("Checked fallbacks: " + ", ".join(fallbacks))
            return 2
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("MARKDOWN GENERATION PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Input CSV      : {args.input}")
    logger.info(f"Output dir     : {args.output}")
    logger.info(f"Use LLM        : {args.use_llm}")
    logger.info(f"Model          : meta/llama-3.1-70b-instruct")
    logger.info(f"Limit          : {args.limit if args.limit else 'None'}")
    logger.info(f"Dry run        : {args.dry_run}")
    logger.info("=" * 60)
    
    # Dry run mode
    if args.dry_run:
        groups = load_grouped_links(args.input)
        if args.limit:
            groups = groups[:args.limit]
        
        print("\nDRY RUN - Would process these groups:")
        for g in groups:
            print(f"  - {g['group_key']} ({g['group_type']}): {len(g['rows'])} links")
        print(f"\nTotal: {len(groups)} groups")
        return 0
    
    # Run the pipeline
    rows, failed = process_groups(
        input_path=args.input,
        output_dir=args.output,
        use_llm=args.use_llm,
        limit=args.limit,
    )
    
    # Write summary JSON
    summary = {
        "processed_count": len(rows),
        "failed_count": len(failed),
        "failed_urls": failed,
    }
    summary_path = os.path.join(args.output, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # Print summary
    total_extracted = sum(r.get("extracted_count", 0) for r in rows if isinstance(r, dict))
    
    print("\n" + "=" * 60)
    print("GENERATION SUMMARY")
    print("=" * 60)
    print(f"Total URLs processed : {len(rows)}")
    print(f"Failed (no HTML)     : {len(failed)}")
    print(f"Total items extracted: {total_extracted}")
    print(f"Output directory     : {args.output}")
    print(f"Summary written to   : {summary_path}")
    print("=" * 60)
    
    if failed:
        print("\nFailed URLs:")
        for u in failed[:20]:  # limit display
            print(f"  - {u}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more (see summary.json)")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
