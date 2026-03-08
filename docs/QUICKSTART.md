# Quick Start Guide

## Step 1: Get Your NVIDIA API Key

1. Visit: https://build.nvidia.com/
2. Sign in or create a free account
3. Navigate to any model page
4. Click "Get API Key"
5. Copy your API key

## Step 2: Set Up Virtual Environment

**Option A — PowerShell (Windows):**
```powershell
.\setup\setup.ps1
```

**Option B — CMD (Windows):**
```cmd
setup\setup.bat
```

**Option C — Manual:**
```bash
python -m venv venv
# Activate (PowerShell)
.\venv\Scripts\Activate.ps1
# Activate (CMD)
venv\Scripts\activate.bat
# Activate (Linux/macOS)
source venv/bin/activate

pip install -r requirements.txt
```

> **Requires Python 3.13+**

## Step 3: Configure Environment

```powershell
# Copy template
Copy-Item template.env .env

# Edit and add your NVIDIA API key(s)
notepad .env
```

Minimum `.env` content:
```env
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**For higher throughput**, add multiple keys:
```env
NVIDIA_API_KEY_1=nvapi-xxxxx
NVIDIA_API_KEY_2=nvapi-yyyyy
NVIDIA_API_KEY_3=nvapi-zzzzz
```
The system rotates between them automatically.

## Step 4: Run the Pipeline

This project has three stages. Run them in order.

---

### Stage 1 — Scrape course page URLs

```bash
# Default: scrapes IIT KGP CSE faculty page
python main_scrape.py

# Custom URL, limited depth for a quick test
python main_scrape.py --url "https://example.edu/faculty" --depth 2

# Without AI (extract all links, no classification)
python main_scrape.py --no-ai
```

Output: `data/scraped_links.json`

Extract the course page URLs from the JSON's `course_pages` array and save as `data/unique_course_urls.csv` for Stage 2.

---

### Stage 2 — Analyze course pages

```bash
python main_data.py
```

Reads `data/unique_course_urls.csv`, fetches each URL, and runs heuristic + AI analysis.

Output: `data/courses_output.csv`

Clean/deduplicate the CSV (e.g., using `utils/clean_courses.py`) and save as `data/courses_output_cleaned.csv`.

---

### Stage 3 — Generate Markdown files

```bash
python main_generate_mdfiles.py

# Test with only 3 courses
python main_generate_mdfiles.py --test

# Heuristics only (no API calls)
python main_generate_mdfiles.py --no-llm
```

Output: `data/markdowns/md/<COURSE_CODE>.md`

---

## Troubleshooting

### PowerShell Execution Policy Error
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### `No NVIDIA API keys found`
1. Confirm `.env` exists (not `.env.txt`)
2. Check key format: `NVIDIA_API_KEY=nvapi-...` (no quotes, no spaces)
3. Re-run from the project root directory

### `API request timed out`
- The default models are large — timeouts are normal on slow connections
- Increase `BATCH_API_TIMEOUT` in `setup/config.py`
- Or switch to the faster `meta/llama-3.1-70b-instruct` for all stages

### Stage 2/3 input file not found
- Stage 2 reads `data/unique_course_urls.csv` — generate it from Stage 1 output
- Stage 3 tries several fallback CSV paths automatically; see `main_generate_mdfiles.py --dry-run`

### Python Not Found
Install Python 3.13+ from: https://www.python.org/downloads/

### Import Errors
Activate the virtual environment first:
```powershell
.\venv\Scripts\Activate.ps1
```
You should see `(venv)` in your terminal prompt.

## Where to Look Next

| After | Check |
|---|---|
| Stage 1 | `data/scraped_links.json`, `logs/scraper.log` |
| Stage 2 | `data/courses_output.csv`, `logs/main_data.log` |
| Stage 3 | `data/markdowns/md/`, `logs/generate_mdfiles.log` |

Full documentation: see `docs/ARCHITECTURE.md` and `docs/PIPELINE_GUIDE.md`
