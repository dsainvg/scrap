"""
utils/markdown_generator.py
---------------------------
Modular utilities for generating per-course markdown files from a cleaned CSV.

This module provides:
- Year parsing and grouping logic
- LLM-based and heuristic material extraction
- Markdown file generation following docsourous conventions

Public API
----------
load_grouped_links(path) -> list[dict]
    Load CSV and group rows by course_code, then course_title, then singletons.

parse_year_to_int(s) -> int
    Parse a year string to an integer for sorting (newest first).

extract_materials_heuristic(html, base_url) -> list[dict]
    Extract learning materials using local heuristics (no LLM).

extract_materials_llm(index_list, link_index, html) -> dict
    Extract learning materials using the NVIDIA LLM.

build_markdown(group_key, index_list, special_marks, per_link_items) -> str
    Build a markdown string for a single course group.

process_groups(path, outdir) -> tuple[list[dict], list[str]]
    Full orchestration: load, group, extract, write markdown files.

Constants
---------
MARKDOWN_OUTPUT_DIR - default output directory for markdown files
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import pandas as pd
from bs4 import BeautifulSoup

# Import shared utilities from course_analyzer
from .course_analyzer import (
    fetch_html,
    _call_nvidia_api,
    _parse_ai_json,
)
from setup.config import MAX_CONTENT_LENGTH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROMPT_file = os.path.join(_PROJECT_ROOT, "prompts", "markdown_extraction.txt")

MARKDOWN_OUTPUT_DIR: str = os.path.join(_PROJECT_ROOT, "data", "markdowns", "md")
DEFAULT_INPUT_CSV: str = os.path.join(_PROJECT_ROOT, "data", "courses_output_cleaned.csv")

# File extensions for learning materials
_FILE_EXTS = (".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".rar", ".ipynb", ".py", ".java", ".c", ".cpp")

POLITE_DELAY = 1.0  # seconds between requests


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def _load_extraction_prompt() -> str:
    """Load the markdown extraction prompt template."""
    try:
        with open(_PROMPT_file, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        logger.warning(f"Prompt file not found at {_PROMPT_file}. Using inline fallback.")
        return (
            "Extract learning materials (slides, question_papers, tutorials, example_code) "
            "from the HTML. Respond ONLY with JSON.\n\n"
            "INDEX_LIST:\n{index_list}\n\nHTML_CHUNK:\n{html_chunk}"
        )


def _render_extraction_prompt(index_list: List[Dict], html_chunk: str) -> str:
    """Render the extraction prompt with the index list and HTML chunk."""
    template = _load_extraction_prompt()
    return (
        template
        .replace("{index_list}", json.dumps(index_list, ensure_ascii=False, indent=2))
        .replace("{html_chunk}", html_chunk)
    )


# ---------------------------------------------------------------------------
# Year parsing
# ---------------------------------------------------------------------------

def parse_year_to_int(s: Optional[str]) -> int:
    """
    Parse a year/semester string to an integer for sorting.
    
    Strategies:
    - Extract 4-digit years starting with '20' (prefer the maximum)
    - Handle ranges like '2023-24' or '2023-2024'
    - Map 2-digit years to 20xx if reasonable
    - Return 0 if no year can be extracted
    
    Parameters
    ----------
    s : str or None
        Free-form year/semester string (e.g., "Autumn 2024", "2023-24")
    
    Returns
    -------
    int
        Parsed year as integer, or 0 if unparseable
    """
    if not s:
        return 0
    text = str(s)
    
    # 4-digit years (20xx)
    y4 = re.findall(r"20\d{2}", text)
    if y4:
        return max(int(y) for y in y4)
    
    # Year ranges like 2023-24
    m = re.search(r"(20\d{2})\s*[-/]\s*(\d{2,4})", text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    
    # 2-digit years
    two = re.findall(r"\b(\d{2})\b", text)
    if two:
        now = datetime.datetime.now().year
        cur2 = now % 100
        candidates = []
        for t in two:
            v = int(t)
            if v <= cur2 + 5:
                candidates.append(2000 + v)
            else:
                candidates.append(1900 + v)
        if candidates:
            return max(candidates)
    
    return 0


def _extract_year_from_html(html: str) -> int:
    """Extract year from HTML content when not available in CSV."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return parse_year_to_int(text)


# ---------------------------------------------------------------------------
# Grouping logic
# ---------------------------------------------------------------------------

def _safe_str(v: Any) -> str:
    """Safely convert a value to string, returning empty string for None/NaN."""
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v).strip()


def _safe_filename(s: str) -> str:
    """Create a filesystem-safe filename from a string."""
    s2 = re.sub(r"[^A-Za-z0-9_.-]", "_", s)
    return s2[:120]


def load_grouped_links(path: str = DEFAULT_INPUT_CSV) -> List[Dict[str, Any]]:
    """
    Load a CSV and group rows by course_code, then course_title, then singletons.
    
    Grouping order:
    1. All rows with a non-empty course_code -> grouped by course_code
    2. Remaining rows with a non-empty course_title -> grouped by course_title  
    3. Remaining rows -> each as a singleton group
    
    Within each group, rows are sorted by year (descending, newest first).
    
    Parameters
    ----------
    path : str
        Path to the input CSV file
    
    Returns
    -------
    list[dict]
        List of group dicts, each with keys:
        - group_key: str (course_code, course_title, or "singleton_N")
        - group_type: 'course_code' | 'course_title' | 'singleton'
        - rows: list[dict] (sorted by year descending)
    """
    df = pd.read_csv(path, dtype=str).fillna("")
    
    # Normalize column names
    colmap = {}
    for c in df.columns:
        lc = c.strip().lower()
        if lc in ("url", "link", "href"):
            colmap[c] = "url"
        elif lc in ("course_code", "code"):
            colmap[c] = "course_code"
        elif lc in ("course_title", "title"):
            colmap[c] = "course_title"
        elif lc == "year":
            colmap[c] = "year"
        elif lc == "semester":
            colmap[c] = "semester"
    if colmap:
        df = df.rename(columns=colmap)
    
    if "url" not in df.columns:
        raise ValueError("Input CSV must contain a 'url' column")
    
    rows = df.to_dict(orient="records")
    
    # Separate rows with and without course_code
    with_code = [r for r in rows if _safe_str(r.get("course_code"))]
    without_code = [r for r in rows if not _safe_str(r.get("course_code"))]
    
    groups: List[Dict[str, Any]] = []
    
    # Group by course_code
    code_map: Dict[str, List[Dict]] = {}
    for r in with_code:
        key = _safe_str(r.get("course_code"))
        code_map.setdefault(key, []).append(r)
    
    for k in sorted(code_map.keys()):
        rows_sorted = sorted(
            code_map[k],
            key=lambda r: -parse_year_to_int(r.get("year") or r.get("semester") or "")
        )
        groups.append({"group_key": k, "group_type": "course_code", "rows": rows_sorted})
    
    # Group remaining by course_title
    title_map: Dict[str, List[Dict]] = {}
    singletons: List[Dict] = []
    for r in without_code:
        title = _safe_str(r.get("course_title"))
        if title:
            title_map.setdefault(title, []).append(r)
        else:
            singletons.append(r)
    
    for t in sorted(title_map.keys()):
        rows_sorted = sorted(
            title_map[t],
            key=lambda r: -parse_year_to_int(r.get("year") or r.get("semester") or "")
        )
        groups.append({"group_key": t, "group_type": "course_title", "rows": rows_sorted})
    
    # Each singleton as its own group
    for idx, r in enumerate(singletons, start=1):
        groups.append({
            "group_key": f"singleton_{idx}",
            "group_type": "singleton",
            "rows": [r],
        })
    
    return groups


# ---------------------------------------------------------------------------
# Heuristic extraction (no LLM)
# ---------------------------------------------------------------------------

# Compiled regex patterns for material classification
# Using (?:^|[^a-zA-Z]) and (?:[^a-zA-Z]|$) to handle underscores in filenames
_SLIDES_RE = re.compile(r'(?:^|[^a-zA-Z])(slide|lecture|lec\d*|ppt|presentation)(?:[^a-zA-Z]|$)', re.IGNORECASE)
_QUESTION_PAPERS_RE = re.compile(r'(?:^|[^a-zA-Z])(question|exam|midterm|endsem|midsem|end[-_]?sem|mid[-_]?sem|test|paper|previous)(?:[^a-zA-Z]|$)', re.IGNORECASE)
_TUTORIALS_RE = re.compile(r'(?:^|[^a-zA-Z])(tutorial|tut\d*|lab|exercise|assignment|homework)(?:[^a-zA-Z]|$)', re.IGNORECASE)
_CODE_RE = re.compile(r'(?:^|[^a-zA-Z])(example|sample|demo|code|program)(?:[^a-zA-Z]|$)', re.IGNORECASE)

def extract_materials_heuristic(html: str, base_url: str) -> List[Dict[str, Any]]:
    """
    Extract learning materials using local heuristics (no LLM).
    
    Looks for file links and classifies them based on keywords in
    the link text and URL.
    
    Parameters
    ----------
    html : str
        Raw HTML content of the page
    base_url : str
        Base URL for resolving relative links
    
    Returns
    -------
    list[dict]
        List of extracted items with keys:
        link_index, item_type, title, snippet, file_url, confidence
    """
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, Any]] = []
    seen: set = set()
    
    def add_item(item_type: str, title: str, file_url: Optional[str], snippet: str, confidence: str = "medium"):
        key = (item_type, file_url or title)
        if key in seen:
            return
        seen.add(key)
        items.append({
            "link_index": 0,  # will be set by caller
            "item_type": item_type,
            "title": title,
            "snippet": snippet[:200] if snippet else "",
            "file_url": file_url,
            "confidence": confidence,
        })
    
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(" ", strip=True)
        
        if not href or href.startswith(("#", "mailto:", "javascript:", "tel:")):
            continue
        
        abs_href = urljoin(base_url, href)
        low_href = abs_href.lower()
        low_text = (text or "").lower()
        combined = low_text + " " + low_href
        
        # Check if it's a file link
        is_file = any(low_href.endswith(ext) for ext in _FILE_EXTS)
        
        if is_file:
            title = text or os.path.basename(urlparse(abs_href).path)
            
            # Classify by keywords using regex word boundaries
            if _SLIDES_RE.search(combined) or low_href.endswith((".ppt", ".pptx")):
                add_item("slides", title, abs_href, text)
            elif _QUESTION_PAPERS_RE.search(combined):
                add_item("question_papers", title, abs_href, text)
            elif _TUTORIALS_RE.search(combined):
                add_item("tutorials", title, abs_href, text)
            elif _CODE_RE.search(combined) or low_href.endswith((".py", ".ipynb", ".java", ".c", ".cpp", ".zip")):
                add_item("example_code", title, abs_href, text)
            else:
                # Generic PDF - try to classify by broader context
                if _SLIDES_RE.search(low_text):
                    add_item("slides", title, abs_href, text, "low")
                elif _QUESTION_PAPERS_RE.search(low_text):
                    add_item("question_papers", title, abs_href, text, "low")
    
    # Check for inline code snippets
    for pre in soup.find_all(["pre", "code"]):
        txt = pre.get_text(" ", strip=True)
        if len(txt) > 50 and len(txt) < 5000:
            if re.search(r"\b(def |class |#include |import |package |function )", txt):
                add_item("example_code", "inline code snippet", None, txt[:200], "low")
    
    return items


# ---------------------------------------------------------------------------
# LLM-based extraction
# ---------------------------------------------------------------------------

def extract_materials_llm(
    index_list: List[Dict[str, Any]],
    link_index: int,
    html: str,
) -> Dict[str, Any]:
    """
    Extract learning materials using the NVIDIA LLM.
    
    Chunks large HTML and aggregates results from multiple LLM calls.
    
    Parameters
    ----------
    index_list : list[dict]
        The indexed list of all links in the group
    link_index : int
        The 1-based index of the current link being processed
    html : str
        Raw HTML content of the page
    
    Returns
    -------
    dict
        Contains 'extracted_items' and 'special_marks' lists
    """
    max_chunk = MAX_CONTENT_LENGTH or 18000
    chunks = [html[i:i + max_chunk] for i in range(0, len(html), max_chunk)] if html else [""]
    
    aggregated = {
        "extracted_items": [],
        "special_marks": [],
    }
    seen = set()
    
    for chunk in chunks:
        prompt = _render_extraction_prompt(index_list, chunk)
        
        try:
            raw = _call_nvidia_api(prompt)
            parsed = _parse_ai_json(raw)
            
            # Merge extracted items
            for it in parsed.get("extracted_items") or []:
                it["link_index"] = link_index
                key = (it.get("item_type"), it.get("file_url") or it.get("title"))
                if key not in seen:
                    seen.add(key)
                    aggregated["extracted_items"].append(it)
            
            # Merge special marks
            aggregated["special_marks"].extend(parsed.get("special_marks") or [])
            
        except Exception as exc:
            logger.warning(f"LLM extraction failed for chunk: {exc}")
            continue
    
    return aggregated


# ---------------------------------------------------------------------------
# Markdown building
# ---------------------------------------------------------------------------

# Human-readable labels for item types
_TYPE_LABELS: Dict[str, str] = {
    "slides": "Lecture Slides",
    "question_papers": "Question Papers",
    "tutorials": "Tutorials & Assignments",
    "example_code": "Example Code",
    "unknown": "[FILE] Other Materials",
}

_GENERIC_TEXTS = {"click here", "download", "pdf", "here", "link", "file", "view", "open", ""}

def _is_generic(text: str) -> bool:
    return text.lower().strip() in _GENERIC_TEXTS

def _friendly_title_from_url(url: str) -> str:
    """Derive a human-readable title from a filename in a URL."""
    basename = os.path.basename(urlparse(url).path)
    name, _ = os.path.splitext(basename)
    name = re.sub(r"[-_]+", " ", name).strip()
    name = re.sub(r"\bLec(\d+)\b", r"Lecture \1", name, flags=re.IGNORECASE)
    name = re.sub(r"\bAss?n?(\d+)\b", r"Assignment \1", name, flags=re.IGNORECASE)
    name = re.sub(r"\bTut(\d+)\b", r"Tutorial \1", name, flags=re.IGNORECASE)
    return name.title() if name else basename

def build_markdown(
    group_key: str,
    index_list: List[Dict[str, Any]],
    special_marks: List[Dict[str, Any]],
    per_link_items: Dict[int, List[Dict[str, Any]]],
) -> str:
    lines: List[str] = []

    # Resolve course title and code
    course_title = ""
    course_code = group_key
    for item in index_list:
        if item.get("course_title"):
            course_title = item["course_title"]
        if item.get("course_code"):
            course_code = item["course_code"]
        if course_title and course_code:
            break

    display_title = course_title or course_code
    full_title = (
        f"{display_title} — {course_code}"
        if (course_title and course_code and course_title != course_code)
        else display_title
    )

    # Docusaurus frontmatter
    lines.append("---")
    lines.append(f'title: "{full_title}"')
    lines.append(f'course_code: "{course_code}"')
    if course_title:
        lines.append(f'course_title: "{course_title}"')
    lines.append("---")
    lines.append("")

    # H1
    lines.append(f"# {full_title}")
    lines.append("")

    # One H2 section per semester/link
    for item in index_list:
        idx = item.get("index")
        url = item.get("url", "")
        sem = item.get("semester") or ""
        yr = item.get("year") or ""

        # Build semester label for H2
        sem_parts = []
        if sem:
            sem_parts.append(sem)
        if yr and yr not in sem:
            sem_parts.append(yr)
        sem_label = " ".join(sem_parts) if sem_parts else "Course Materials"

        lines.append(f"## {sem_label}")
        lines.append("")
        lines.append(f"**Source:** [Course Page]({url})")
        lines.append("")

        link_items = per_link_items.get(idx) or []

        if not link_items:
            lines.append("*No learning materials could be extracted from this page.*")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        # Group by type
        by_type: Dict[str, List[Dict]] = {}
        for it in link_items:
            by_type.setdefault(it.get("item_type", "unknown"), []).append(it)

        type_order = ["slides", "question_papers", "tutorials", "example_code", "unknown"]
        for itype in type_order:
            type_items = by_type.get(itype)
            if not type_items:
                continue

            label = _TYPE_LABELS.get(itype, f"[FILE] {itype.replace('_', ' ').title()}")
            lines.append(f"### {label}")
            lines.append("")

            for it in type_items:
                raw_title = it.get("title") or ""
                file_url = it.get("file_url") or ""
                description = (it.get("description") or it.get("snippet") or "").replace("\n", " ").strip()

                # Use meaningful title: if generic or empty, derive from URL
                title = (
                    raw_title
                    if raw_title and not _is_generic(raw_title)
                    else (_friendly_title_from_url(file_url) if file_url else "(untitled)")
                )

                # Clickable H4 or plain H4
                if file_url:
                    lines.append(f"#### [{title}]({file_url})")
                else:
                    lines.append(f"#### {title}")

                if description:
                    lines.append(f"> {description[:200]}")

                lines.append("")

        lines.append(f"*Full course page: [{url}]({url})*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def process_groups(
    input_path: str = DEFAULT_INPUT_CSV,
    output_dir: str = MARKDOWN_OUTPUT_DIR,
    use_llm: bool = True,
    limit: int = 0,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Full orchestration: load CSV, group links, extract materials, write markdown.
    
    Parameters
    ----------
    input_path : str
        Path to the input CSV file
    output_dir : str
        Directory to write markdown files
    use_llm : bool
        Whether to use LLM for extraction (falls back to heuristics if False or on error)
    limit : int
        Maximum number of groups to process (0 = no limit)
    
    Returns
    -------
    tuple[list[dict], list[str]]
        (all_rows, failed_urls) where all_rows contains extracted data
        and failed_urls contains URLs that could not be fetched
    """
    os.makedirs(output_dir, exist_ok=True)
    
    groups = load_grouped_links(input_path)
    
    # Apply limit if specified
    if limit > 0:
        groups = groups[:limit]
        logger.info(f"Limited to {limit} groups")
    
    logger.info(f"Loaded {len(groups)} groups from {input_path}")
    
    all_rows: List[Dict[str, Any]] = []
    failed: List[str] = []
    
    for g in groups:
        key = g["group_key"]
        group_type = g["group_type"]
        rows = g["rows"]
        
        logger.info(f"Processing group: {key} ({group_type}) with {len(rows)} links")
        
        # Prefetch HTML for rows missing year info (to enable proper sorting)
        for r in rows:
            r["_year_int"] = parse_year_to_int(r.get("year") or r.get("semester"))
            r["_html"] = None
            
            if r["_year_int"] == 0:
                html = fetch_html(r.get("url"))
                time.sleep(POLITE_DELAY)
                if html:
                    r["_html"] = html
                    r["_year_int"] = _extract_year_from_html(html)
                else:
                    failed.append(r.get("url"))
        
        # Re-sort by year after prefetch
        rows = sorted(rows, key=lambda rr: -int(rr.get("_year_int") or 0))
        g["rows"] = rows
        
        # Build index list
        index_list: List[Dict[str, Any]] = []
        for i, r in enumerate(rows):
            index_list.append({
                "index": i + 1,
                "url": r.get("url"),
                "course_code": _safe_str(r.get("course_code")) or None,
                "course_title": _safe_str(r.get("course_title")) or None,
                "semester": _safe_str(r.get("semester")) or None,
                "year": _safe_str(r.get("year")) or None,
            })
        
        # Write index JSON
        idx_path = os.path.join(output_dir, f"{_safe_filename(key)}.index.json")
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump({"links": index_list}, f, ensure_ascii=False, indent=2)
        
        # Extract materials for each link
        per_link_items: Dict[int, List[Dict]] = {}
        all_special_marks: List[Dict] = []
        
        for i, r in enumerate(rows):
            idx = i + 1
            url = r.get("url")
            html = r.get("_html") or fetch_html(url)
            time.sleep(POLITE_DELAY)
            
            if not html:
                failed.append(url)
                per_link_items[idx] = []
                all_rows.append({"url": url, "status": "failed"})
                continue
            
            # Extract materials
            extracted_items: List[Dict] = []
            
            if use_llm:
                try:
                    result = extract_materials_llm(index_list, idx, html)
                    extracted_items = result.get("extracted_items") or []
                    all_special_marks.extend(result.get("special_marks") or [])
                except Exception as exc:
                    logger.warning(f"LLM extraction failed for {url}: {exc}, falling back to heuristics")
                    extracted_items = extract_materials_heuristic(html, url)
            else:
                extracted_items = extract_materials_heuristic(html, url)
            
            # Set link_index for heuristic items
            for it in extracted_items:
                if not it.get("link_index"):
                    it["link_index"] = idx
            
            per_link_items[idx] = extracted_items
            
            # Record for output
            all_rows.append({
                "url": url,
                "course_code": _safe_str(r.get("course_code")),
                "course_title": _safe_str(r.get("course_title")),
                "semester": _safe_str(r.get("semester")),
                "year": _safe_str(r.get("year")),
                "extracted_count": len(extracted_items),
                "extracted_items": extracted_items,
            })
        
        # Build and write markdown
        md_content = build_markdown(key, index_list, all_special_marks, per_link_items)
        md_path = os.path.join(output_dir, f"{_safe_filename(key)}.md")
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        
        logger.info(f"Wrote markdown: {md_path}")
    
    return all_rows, failed
