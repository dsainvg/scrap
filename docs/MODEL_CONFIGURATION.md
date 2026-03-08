# AI Model Configuration Guide

All AI model settings are centralized in `setup/config.py`.

## Current Model Assignments

| Stage | Task | Setting | Current Model |
|---|---|---|---|
| Stage 1 | Link classification (batch) | `LINK_CLASSIFICATION_MODEL` | `meta/llama-3.3-70b-instruct` |
| Stage 1 (optional) | Course page content verification | `CONTENT_VERIFICATION_MODEL` | `meta/llama-3.1-70b-instruct` |
| Stage 2 | Course page AI enrichment | `CONTENT_VERIFICATION_MODEL` | `meta/llama-3.1-70b-instruct` |
| Stage 3 | Learning material extraction | `CONTENT_VERIFICATION_MODEL` | `meta/llama-3.1-70b-instruct` |

> Stage 2 and Stage 3 share the `CONTENT_VERIFICATION_MODEL` setting from `setup/config.py`.

---

## Link Classification Settings (Stage 1)

Used for classifying each link as a course page, course-relevant, back link, or irrelevant.

```python
# setup/config.py
LINK_CLASSIFICATION_MODEL = "meta/llama-3.3-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.1    # Low = deterministic (0.0–2.0)
LINK_CLASSIFICATION_MAX_TOKENS = 512     # Response length limit
LINK_CLASSIFICATION_TOP_P = 0.9          # Nucleus sampling (0.0–1.0)
```

---

## Content Verification / Analysis Settings (Stage 1 optional, Stage 2, Stage 3)

Used for page-level HTML analysis: verifying course pages, extracting metadata, extracting materials.

```python
# setup/config.py
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
CONTENT_VERIFICATION_MAX_TOKENS = 4096   # Increased to avoid truncation
CONTENT_VERIFICATION_TOP_P = 0.7
MAX_CONTENT_LENGTH = 8000                # Max HTML characters sent per request
```

---

## Batch Processing Settings (Stage 1)

```python
# setup/config.py
BATCH_SIZE = 7              # Links per API call (keep ≤ 5–7 for 70B+ models)
BATCH_API_TIMEOUT = 120     # Seconds per batch call
BATCH_INTER_DELAY = 2       # Seconds between consecutive batch calls
BATCH_MAX_RETRIES = 3       # Retry count on timeout (exponential backoff)
```

---

## Model Parameter Explanations

### Temperature
- `0.0–0.2`: Very deterministic — best for classification and factual extraction
- `0.3–0.6`: Slightly varied — acceptable for structured generation
- `0.7+`: Creative / diverse — avoid for JSON-output tasks

### Max Tokens
- Keep at `512` for link classification (short JSON responses)
- Use `4096` for page analysis to avoid truncated JSON

### Top P (Nucleus Sampling)
- `0.7–0.9`: Focused, reliable — recommended for all stages

---

## Example Presets

### Maximum Accuracy (slowest)
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.3-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.1
LINK_CLASSIFICATION_MAX_TOKENS = 512
BATCH_SIZE = 5

CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.05
CONTENT_VERIFICATION_MAX_TOKENS = 4096
MAX_CONTENT_LENGTH = 12000
```

### Balanced (current default)
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.3-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.1
LINK_CLASSIFICATION_MAX_TOKENS = 512
BATCH_SIZE = 7

CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
CONTENT_VERIFICATION_MAX_TOKENS = 4096
MAX_CONTENT_LENGTH = 8000
```

### Maximum Speed
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.1-70b-instruct"  # Faster than 3.3
LINK_CLASSIFICATION_TEMPERATURE = 0.2
LINK_CLASSIFICATION_MAX_TOKENS = 256
BATCH_SIZE = 10

CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.2
CONTENT_VERIFICATION_MAX_TOKENS = 2048
MAX_CONTENT_LENGTH = 5000
```

### Cost-Optimized (minimal API usage)
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.1-8b-instruct"
LINK_CLASSIFICATION_MAX_TOKENS = 256
BATCH_SIZE = 10

CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-8b-instruct"
CONTENT_VERIFICATION_MAX_TOKENS = 1024
MAX_CONTENT_LENGTH = 4000
```

---

## Available NVIDIA Models

| Speed | Model | Notes |
|---|---|---|
| ⚡⚡⚡ | `meta/llama-3.1-8b-instruct` | Fast; lower accuracy on complex pages |
| ⚡⚡ | `meta/llama-3.1-70b-instruct` | **Recommended for all stages** — best speed/quality |
| ⚡ | `meta/llama-3.3-70b-instruct` | **Default for link classification** — strong reasoning; slower |
| ⚡ | `meta/llama-3.1-405b-instruct` | Highest accuracy; very slow |

Full catalog: https://build.nvidia.com/explore/discover

---

## How to Change

1. Edit `setup/config.py`
2. Modify values in the "AI Model Configuration" section
3. Save — changes take effect on the next run
4. Config is validated automatically on import (invalid values raise `ValueError`)

---

## Runtime Override (Programmatic)

```python
from utils.link_classifier import LinkClassifier

# Override model for this instance
classifier = LinkClassifier(
    model="meta/llama-3.1-70b-instruct",
    cache_file="data/custom_cache.json"
)
```

---

## Monitoring

### Logs
All AI calls and their results are logged to:
- `logs/scraper.log` — Stage 1 classification decisions
- `logs/main_data.log` — Stage 2 analysis results
- `logs/generate_mdfiles.log` — Stage 3 extraction results

### Cache Statistics (Stage 1)
Printed after each scraping run:
```
CLASSIFICATION CACHE STATISTICS
================================
Cache Size: 1500 entries
Cache Hits: 850  (56.7%)
Cache Misses: 650
```

### API Key Statistics
Printed after each run when multiple keys are in use:
```
API KEY USAGE STATISTICS
========================
Key ...abc123: 450 calls, 5 errors
Key ...def456: 420 calls, 3 errors
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Low classification accuracy | Lower temperature (0.1), larger model, smaller batch size |
| API timeouts | Increase `BATCH_API_TIMEOUT`, reduce `MAX_CONTENT_LENGTH`, use faster model |
| Truncated JSON responses | Increase `CONTENT_VERIFICATION_MAX_TOKENS` to 4096 |
| Inconsistent results | Lower temperature (0.1), lower `TOP_P` (0.7) |
| High API usage | Enable classification cache (on by default), reduce `MAX_CONTENT_LENGTH` |

---

## Best Practices

1. **Keep the defaults** for first-time use — they are well-tuned
2. **Never disable the cache** — it avoids duplicate API calls across runs
3. **Test with `--depth 1`** or `--test` (Stage 3) after changing models
4. **Prefer `meta/llama-3.1-70b-instruct`** over 3.3 for speed-sensitive work
5. **Comment changes** in `setup/config.py` so you know what was changed and why
