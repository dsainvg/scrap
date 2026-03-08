"""
utils/course_analyzer.py
------------------------
Reusable pipeline for IIT Kharagpur course page analysis.

Public API
----------
fetch_html(url, timeout, max_retries) -> str | None
make_soup(html) -> BeautifulSoup
extract_manual_fields(url, html, soup) -> dict
classify_manual_page_type(extracted, html) -> str
ai_enrich_page(extracted, html) -> dict
merge_results(extracted, manual_page_type, ai_data) -> dict
write_csv(rows, path) -> None
process_url(url) -> dict | None

Constants
---------
OUTPUT_CSV      — default CSV output path
CSV_COLUMNS     — ordered list of CSV column names

Import anywhere:
    from utils.course_analyzer import process_url, write_csv, OUTPUT_CSV
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import time
from collections import Counter
from typing import Optional
from urllib.parse import urljoin, urlparse
import pandas as pd
import requests
from bs4 import BeautifulSoup

from .api_key_manager import get_key_manager
from setup.config import (
    CONTENT_VERIFICATION_MAX_TOKENS,
    CONTENT_VERIFICATION_MODEL,
    CONTENT_VERIFICATION_TEMPERATURE,
    CONTENT_VERIFICATION_TOP_P,
    MAX_CONTENT_LENGTH,
    NVIDIA_API_ENDPOINT,
    SCRAPER_TIMEOUT,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Root of the project is two levels up from this file (utils/course_analyzer.py)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROMPT_FILE = os.path.join(_PROJECT_ROOT, "prompts", "course_page_analysis.txt")

OUTPUT_CSV: str = os.path.join(_PROJECT_ROOT, "data", "courses_output.csv")
INPUT_CSV : str = os.path.join(_PROJECT_ROOT, "data", "unique_course_urls.csv")
# ---------------------------------------------------------------------------
# CSV schema
# ---------------------------------------------------------------------------
CSV_COLUMNS: list[str] = [
    "url",
    "course_code",
    "course_title",
    "semester",
    "year",
    "manual_page_type",
    "ai_page_type",
    "ai_confidence",
    "ai_reasoning",
    "has_notes",
    "notes_type",
    "notes_details",
    "further_course_related_data_present",
    "has_syllabus_or_logistics",
    "is_useful",
    "conflict_flag",
    "recheck_needed",
    "all_files_json",
    "all_internal_links_json",
]

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------
# Maps manual heuristic labels to their coarse AI-equivalent for conflict detection
_MANUAL_TO_AI: dict[str, str] = {
    "course_page_like":    "course_page",
    "syllabus_like":       "syllabus_pdf_link",
    "notes_subpage_like":  "notes_subpage",
    "curricula_list_like": "curricula_list",
    "logistics_only_like": "logistics_only",
    "other":               "other",
}

# Downloadable file extensions (not navigable web pages)
_FILE_EXTS: frozenset[str] = frozenset(
    {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".rar"}
)

# Compiled regex patterns for Step 3 classification
_SYLLABUS_KW = re.compile(r'\b(unit|topic|syllabus|outline|module)\b', re.IGNORECASE)
_LOGISTICS_KW = re.compile(r'\b(time|venue|room|slot|instructor|timing|schedule)\b', re.IGNORECASE)
_NOTES_KW = re.compile(r'\b(lecture|lec\d*|week\d*|slide|tutorial|assignment)\b', re.IGNORECASE)

# AI fallback when the API call fails
_AI_FALLBACK: dict = {
    "ai_page_type": "other",
    "ai_confidence": "low",
    "ai_reasoning": "AI call failed; defaulted to 'other'.",
    "course_code": None,
    "course_title": None,
    "semester": None,
    "year": None,
    "has_notes": False,
    "notes_type": "unknown",
    "notes_details": "",
    "further_course_related_data_present": False,
    "has_syllabus_or_logistics": False,
    "is_useful": False,
}


# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------

def _load_prompt_template() -> str:
    """
    Load the AI prompt template from ``prompts/course_page_analysis.txt``.

    Falls back to a minimal inline template if the file is missing.
    The template uses plain ``{manual_json}`` and ``{html_snippet}``
    placeholders (not Python format-string syntax with escaped braces).
    """
    try:
        with open(_PROMPT_FILE, "r", encoding="utf-8") as fh:
            template = fh.read()
        logger.debug(f"Loaded prompt template from {_PROMPT_FILE}")
        return template
    except FileNotFoundError:
        logger.warning(
            f"Prompt file not found at {_PROMPT_FILE}. Using inline fallback template."
        )
        return (
            "Classify the following academic page.\n\n"
            "Manual JSON:\n{manual_json}\n\n"
            "HTML snippet:\n{html_snippet}\n\n"
            'Respond with JSON: {"page_type":...,"confidence":...,"ai_reasoning":...,'
            '"has_notes":...,"notes_type":...,"notes_details":...,'
            '"further_course_related_data_present":...}'
        )


def _render_prompt(template: str, manual_json: str, html_snippet: str) -> str:
    """
    Fill *template* with *manual_json* and *html_snippet*.

    Uses plain string replacement so the JSON example block inside the
    template file (with literal ``{`` / ``}``) does not need escaping.
    """
    return (
        template
        .replace("{manual_json}", manual_json)
        .replace("{html_snippet}", html_snippet)
    )


# ===========================================================================
# STEP 1 — Fetch + Parse
# ===========================================================================

def fetch_html(
    url: str,
    timeout: int = SCRAPER_TIMEOUT,
    max_retries: int = 2,
) -> Optional[str]:
    """
    Fetch raw HTML from *url* with simple retry logic.

    Parameters
    ----------
    url:
        Target URL.
    timeout:
        Per-request timeout in seconds (default: ``config.SCRAPER_TIMEOUT``).
    max_retries:
        Number of *additional* attempts after the first failure.

    Returns
    -------
    HTML string on success, ``None`` if all attempts fail.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    for attempt in range(1, max_retries + 2):  # 1 initial + max_retries extras
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            logger.info(f"[OK] Fetched ({len(resp.text):,} chars): {url}")
            return resp.text
        except requests.RequestException as exc:
            logger.warning(f"[Attempt {attempt}] Fetch failed for {url}: {exc}")
            if attempt <= max_retries:
                time.sleep(1.5 * attempt)

    logger.error(f"All retry attempts exhausted for: {url}")
    return None


def make_soup(html: str) -> BeautifulSoup:
    """Parse *html* into a ``BeautifulSoup`` tree using ``html.parser``."""
    return BeautifulSoup(html, "html.parser")


# ===========================================================================
# STEP 2 — Manual field extraction  (no AI)
# ===========================================================================

def extract_manual_fields(
    url: str,
    html: str,
    soup: BeautifulSoup,
) -> dict:
    """
    Extract structured fields from *url* / *html* / *soup* without any AI.

    Returns
    -------
    dict with keys:
        ``url``, ``course_code``, ``course_title``, ``semester``, ``year``,
        ``all_files``, ``all_internal_links``
    """
    domain = urlparse(url).netloc
    visible_text = soup.get_text(" ", strip=True)

    # -- course_code -------------------------------------------------------
    _CODE_RE = re.compile(r'\b([A-Z]{2,3}\s?\d{2,5})\b')
    all_codes = _CODE_RE.findall(visible_text)
    course_code: Optional[str] = None
    if all_codes:
        freq = Counter(all_codes)
        course_code = freq.most_common(1)[0][0].replace(" ", "")

    # -- course_title ------------------------------------------------------
    course_title: Optional[str] = None
    for tag_name in ("h1", "h2"):
        tag = soup.find(tag_name)
        if tag:
            text = tag.get_text(" ", strip=True)
            if text:
                course_title = re.sub(r'\s+', ' ', text)
                break
    if not course_title:
        title_tag = soup.find("title")
        if title_tag:
            course_title = re.sub(r'\s+', ' ', title_tag.get_text(" ", strip=True))

    # -- semester ----------------------------------------------------------
    _SEM_RE = re.compile(
        r'\b(Autumn|Spring|Fall|Monsoon|Winter|Even\s+Semester|Odd\s+Semester|'
        r'Autumn\s+\d{4}|Spring\s+\d{4}|Fall\s+\d{4})',
        re.IGNORECASE,
    )
    sem_match = _SEM_RE.search(visible_text)
    semester: Optional[str] = sem_match.group(0).strip() if sem_match else None

    # -- year --------------------------------------------------------------
    _YEAR_RE = re.compile(r'\b(20\d{2}(?:-\d{2,4})?)\b')
    year_match = _YEAR_RE.search(visible_text)
    year: Optional[str] = year_match.group(0) if year_match else None

    # -- all_files ---------------------------------------------------------
    all_files: list[dict] = []
    seen_file_hrefs: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        abs_href = urljoin(url, href)
        path_lower = urlparse(abs_href).path.lower()
        if any(path_lower.endswith(ext) for ext in _FILE_EXTS):
            if abs_href not in seen_file_hrefs:
                seen_file_hrefs.add(abs_href)
                all_files.append({"href": abs_href, "text": a.get_text(" ", strip=True)})

    # -- all_internal_links ------------------------------------------------
    all_internal_links: list[dict] = []
    seen_internal_hrefs: set[str] = set()
    _SKIP_PREFIXES = ("#", "javascript:", "mailto:", "tel:", "ftp:", "data:", "blob:")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or any(href.startswith(p) for p in _SKIP_PREFIXES):
            continue
        abs_href = urljoin(url, href)
        parsed = urlparse(abs_href)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc == domain and abs_href not in seen_internal_hrefs:
            seen_internal_hrefs.add(abs_href)
            all_internal_links.append({"href": abs_href, "text": a.get_text(" ", strip=True)})

    return {
        "url": url,
        "course_code": course_code,
        "course_title": course_title,
        "semester": semester,
        "year": year,
        "all_files": all_files,
        "all_internal_links": all_internal_links,
    }


# ===========================================================================
# STEP 3 — Manual page classification  (rule-based, no AI)
# ===========================================================================

def classify_manual_page_type(extracted: dict, html: str) -> str:
    """
    Rule-based page type classification — no AI.

    Parameters
    ----------
    extracted:
        Output of :func:`extract_manual_fields`.
    html:
        Raw HTML string of the page.

    Returns
    -------
    One of:
        ``"course_page_like"``, ``"syllabus_like"``, ``"notes_subpage_like"``,
        ``"curricula_list_like"``, ``"logistics_only_like"``, ``"other"``
    """
    soup = make_soup(html)
    visible = soup.get_text(" ", strip=True)
    files: list[dict] = extracted.get("all_files", [])
    course_code = extracted.get("course_code")
    has_sem_or_year = bool(extracted.get("semester") or extracted.get("year"))

    # curricula_list_like: many distinct course codes on one page
    distinct_codes = set(re.findall(r'\b[A-Z]{2,3}\s?\d{2,5}\b', visible))
    if len(distinct_codes) > 5:
        return "curricula_list_like"

    # notes_subpage_like: >= 2 file links whose text/href hints at notes/lectures
    notes_files = [
        f for f in files
        if _NOTES_KW.search(f.get("text", "")) or _NOTES_KW.search(f.get("href", ""))
    ]
    if len(notes_files) >= 2:
        return "notes_subpage_like"

    # syllabus_like: a dedicated syllabus file is linked
    syllabus_files = [
        f for f in files
        if "syllabus" in f.get("href", "").lower()
        or "syllabus" in f.get("text", "").lower()
    ]
    if syllabus_files:
        return "syllabus_like"

    # course_page_like: course code + temporal marker + list/table with topics
    if course_code and has_sem_or_year:
        for element in soup.find_all(["table", "ul", "ol"]):
            if _SYLLABUS_KW.search(element.get_text()):
                return "course_page_like"

    # logistics_only_like: many venue/time words, no syllabus/notes hints
    if (
        len(_LOGISTICS_KW.findall(visible)) >= 3
        and not _NOTES_KW.search(visible)
        and not _SYLLABUS_KW.search(visible)
    ):
        return "logistics_only_like"

    return "other"


# ===========================================================================
# STEP 4 — AI enrichment via NVIDIA LLM
# ===========================================================================

def _call_nvidia_api(prompt: str, timeout: int = 120) -> str:
    """
    Send *prompt* to the NVIDIA chat completions endpoint using key rotation.

    Parameters
    ----------
    prompt : str
        The prompt to send to the API
    timeout : int
        Request timeout in seconds (default: 120). Increased from 60 to handle
        slower models like llama-3.3-70b-instruct which can take 15-60s per request.

    Returns
    -------
    Raw text content of the model response.

    Raises
    ------
    RuntimeError
        If the HTTP request fails after the key manager's built-in handling.
    """
    key_manager = get_key_manager()
    api_key = key_manager.get_next_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CONTENT_VERIFICATION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an expert academic page analyzer. "
                    "Respond ONLY with valid JSON — no prose, no code fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": CONTENT_VERIFICATION_MAX_TOKENS,
        "temperature": CONTENT_VERIFICATION_TEMPERATURE,
        "top_p": CONTENT_VERIFICATION_TOP_P,
        "stream": False,
    }

    try:
        logger.debug(f"Calling NVIDIA API with model={CONTENT_VERIFICATION_MODEL}, timeout={timeout}s")
        response = requests.post(
            NVIDIA_API_ENDPOINT, headers=headers, json=payload, timeout=timeout
        )
        response.raise_for_status()
        key_manager.report_success(api_key)
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        logger.debug(f"API call successful, response length: {len(content)} chars")
        return content
    except requests.Timeout as exc:
        key_manager.report_error(api_key)
        error_msg = (
            f"NVIDIA API request timed out after {timeout}s. "
            f"Model: {CONTENT_VERIFICATION_MODEL}. "
            f"Consider: 1) Using a faster model (e.g., meta/llama-3.1-70b-instruct), "
            f"2) Reducing MAX_CONTENT_LENGTH in config, "
            f"3) Increasing timeout further."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from exc
    except requests.RequestException as exc:
        key_manager.report_error(api_key)
        error_msg = f"NVIDIA API request failed: {exc}"
        if hasattr(exc, 'response') and exc.response is not None:
            error_msg += f" | Status: {exc.response.status_code} | Response: {exc.response.text[:200]}"
        raise RuntimeError(error_msg) from exc


def _parse_ai_json(text: str) -> dict:
    """
    Robustly extract a JSON object from *text*.

    Handles markdown code fences, stray prose around the JSON block,
    and incomplete responses.
    """
    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown fences
    clean = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Try to find the main JSON object (greedy match for nested structures)
    # Look for opening { and try to find the matching closing }
    m = re.search(r'\{.*\}', clean, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    
    # If still failing, try to extract and repair incomplete JSON
    # Find the first { and take everything after it
    start = clean.find('{')
    if start != -1:
        potential_json = clean[start:]
        
        # Try adding closing braces if incomplete
        for _ in range(5):  # Try up to 5 levels of nesting
            try:
                return json.loads(potential_json)
            except json.JSONDecodeError as e:
                # If error is about unexpected end, try adding }
                if 'Expecting' in str(e) or 'Unterminated' in str(e):
                    potential_json += '}'
                else:
                    break

    raise ValueError(f"Cannot parse JSON from AI response:\n{text[:400]}")


def ai_enrich_page(extracted: dict, html: str) -> dict:
    """
    Call the NVIDIA LLM to classify and enrich a page.

    The prompt template is loaded from
    ``prompts/course_page_analysis.txt`` at call time (cached after first
    load via module-level lazy pattern — callers need not worry about it).

    Parameters
    ----------
    extracted:
        Output of :func:`extract_manual_fields`.
    html:
        Raw HTML string of the page.

    Returns
    -------
    dict with keys:
        ``ai_page_type``, ``ai_confidence``, ``ai_reasoning``,
        ``has_notes``, ``notes_type``, ``notes_details``,
        ``further_course_related_data_present``
    """
    template = _load_prompt_template()
    manual_json = json.dumps(extracted, ensure_ascii=False, indent=2)
    html_snippet = html[:MAX_CONTENT_LENGTH]
    prompt = _render_prompt(template, manual_json, html_snippet)

    try:
        raw = _call_nvidia_api(prompt)
        logger.debug(f"AI raw response for {extracted['url']}: {raw[:300]}")
        parsed = _parse_ai_json(raw)

        ai_result = {
            "ai_page_type":                     str(parsed.get("page_type", "other")),
            "ai_confidence":                    str(parsed.get("confidence", "low")),
            "ai_reasoning":                     str(parsed.get("ai_reasoning", "")),
            "course_code":                      parsed.get("course_code") or None,
            "course_title":                     parsed.get("course_title") or None,
            "semester":                         parsed.get("semester") or None,
            "year":                             parsed.get("year") or None,
            "has_notes":                        bool(parsed.get("has_notes", False)),
            "notes_type":                       str(parsed.get("notes_type", "unknown")),
            "notes_details":                    str(parsed.get("notes_details", "")),
            "further_course_related_data_present": bool(
                parsed.get("further_course_related_data_present", False)
            ),
            "has_syllabus_or_logistics":         bool(parsed.get("has_syllabus_or_logistics", False)),
            "is_useful":                        bool(parsed.get("is_useful", False)),
        }
        logger.info(
            f"[AI] {extracted['url']} -> page_type={ai_result['ai_page_type']} "
            f"confidence={ai_result['ai_confidence']}"
        )
        return ai_result

    except Exception as exc:
        logger.error(f"AI enrichment failed for {extracted['url']}: {exc}")
        return dict(_AI_FALLBACK)


# ===========================================================================
# STEP 5 — Merge manual + AI results
# ===========================================================================

def merge_results(
    extracted: dict,
    manual_page_type: str,
    ai_data: dict,
) -> dict:
    """
    Combine manually extracted fields with AI enrichment into one record.

    AI classification is preferred as the final classification.
    Sets ``conflict_flag`` when manual and AI types diverge, and
    ``recheck_needed`` when there is a conflict **or** AI confidence is "low".

    Parameters
    ----------
    extracted:
        Output of :func:`extract_manual_fields`.
    manual_page_type:
        Output of :func:`classify_manual_page_type`.
    ai_data:
        Output of :func:`ai_enrich_page`.

    Returns
    -------
    Single flat dict with all data-model fields.
    """
    ai_page_type = ai_data["ai_page_type"]
    manual_coarse = _MANUAL_TO_AI.get(manual_page_type, "other")

    conflict_flag = manual_coarse != ai_page_type
    recheck_needed = conflict_flag or ai_data["ai_confidence"] == "low"

    logger.info(
        f"MERGE [{extracted['url']}] "
        f"manual={manual_page_type} (coarse={manual_coarse}) | "
        f"ai={ai_page_type} | conflict={conflict_flag} | recheck={recheck_needed}"
    )

    return {
        "url":                              extracted["url"],
        "course_code":                      ai_data.get("course_code"),
        "course_title":                     ai_data.get("course_title"),
        "semester":                         ai_data.get("semester"),
        "year":                             ai_data.get("year"),
        "all_files":                        extracted.get("all_files", []),
        "all_internal_links":               extracted.get("all_internal_links", []),
        "manual_page_type":                 manual_page_type,
        "ai_page_type":                     ai_page_type,
        "ai_confidence":                    ai_data["ai_confidence"],
        "ai_reasoning":                     ai_data["ai_reasoning"],
        "has_notes":                        ai_data["has_notes"],
        "notes_type":                       ai_data["notes_type"],
        "notes_details":                    ai_data["notes_details"],
        "further_course_related_data_present": ai_data["further_course_related_data_present"],
        "has_syllabus_or_logistics":         ai_data["has_syllabus_or_logistics"],
        "is_useful":                        ai_data["is_useful"],
        "conflict_flag":                    conflict_flag,
        "recheck_needed":                   recheck_needed,
    }


# ===========================================================================
# STEP 6 — CSV output
# ===========================================================================

def write_csv(rows: list[dict], path: str = OUTPUT_CSV) -> None:
    """
    Write *rows* to a CSV file at *path*.

    List fields (``all_files``, ``all_internal_links``) are serialised as
    JSON strings in the ``all_files_json`` / ``all_internal_links_json`` columns.

    Parameters
    ----------
    rows:
        List of merged result dicts (output of :func:`merge_results`).
    path:
        Destination CSV file path.  Parent directories are created if needed.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            flat["all_files_json"] = json.dumps(
                row.get("all_files", []), ensure_ascii=False
            )
            flat["all_internal_links_json"] = json.dumps(
                row.get("all_internal_links", []), ensure_ascii=False
            )
            writer.writerow(flat)

    logger.info(f"Wrote {len(rows)} record(s) to {path}")


# ===========================================================================
# STEP 7 — Single-URL orchestration (reusable entry point)
# ===========================================================================

def process_url(url: str) -> Optional[dict]:
    """
    Run the full 5-step analysis pipeline for a single *url*.

    Steps: fetch -> parse -> manual extract -> manual classify
           -> AI enrich -> merge

    Parameters
    ----------
    url:
        The page to analyse.

    Returns
    -------
    Merged result dict, or ``None`` if HTML could not be fetched.
    """
    logger.info(f"== Processing: {url}")

    html = fetch_html(url)
    if html is None:
        logger.warning(f"Skipping {url} — HTML unavailable.")
        return None

    soup = make_soup(html)
    extracted = extract_manual_fields(url, html, soup)
    manual_page_type = classify_manual_page_type(extracted, html)
    ai_data = ai_enrich_page(extracted, html)
    merged = merge_results(extracted, manual_page_type, ai_data)

    return merged

def load_data(path: str = OUTPUT_CSV) -> list[str]:
    
    data = pd.read_csv(path)
    return data['url'].dropna().tolist()