# Quick Reference: Configuration (`setup/config.py`)

## File Location
`setup/config.py` — edit this file to configure scraper and AI model settings.
Environment variables (API keys only) go in `.env`.

---

## Scraper Settings

```python
SCRAPER_TIMEOUT = 45       # HTTP request timeout (seconds)
SCRAPER_DELAY   = 1        # Polite delay between page fetches (seconds)
MAX_SCRAPING_DEPTH = 7     # Maximum recursion depth (Stage 1)
```

---

## Link Classification (Stage 1)

```python
LINK_CLASSIFICATION_MODEL       = "meta/llama-3.3-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.1    # 0.0 = fully deterministic
LINK_CLASSIFICATION_MAX_TOKENS  = 512
LINK_CLASSIFICATION_TOP_P       = 0.9
```

---

## Content Verification / Analysis (Stage 1 optional, Stage 2, Stage 3)

```python
CONTENT_VERIFICATION_MODEL       = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
CONTENT_VERIFICATION_MAX_TOKENS  = 4096   # High to avoid truncated JSON
CONTENT_VERIFICATION_TOP_P       = 0.7
MAX_CONTENT_LENGTH               = 8000   # Max HTML chars sent to AI
```

---

## Batch Processing (Stage 1)

```python
BATCH_SIZE       = 7     # Links per API call (keep ≤ 7 for large models)
BATCH_API_TIMEOUT = 120  # Seconds before a batch call times out
BATCH_INTER_DELAY = 2    # Seconds between consecutive batch calls
BATCH_MAX_RETRIES = 3    # Retry count on timeout (exponential backoff)
```

---

## API & Cache

```python
NVIDIA_API_ENDPOINT      = "https://integrate.api.nvidia.com/v1/chat/completions"
CLASSIFICATION_CACHE_FILE = "data/link_classification_cache.json"
```

---

## Recommended Models

| Speed | Model | Use case |
|---|---|---|
| ⚡⚡⚡ | `meta/llama-3.1-8b-instruct` | Cost-optimized runs |
| ⚡⚡ | `meta/llama-3.1-70b-instruct` | **Recommended default** |
| ⚡ | `meta/llama-3.3-70b-instruct` | Better reasoning, slower |
| ⚡ | `meta/llama-3.1-405b-instruct` | Highest accuracy |

---

## Quick Presets

### Balanced (current default)
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.3-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.1
BATCH_SIZE = 7
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
```

### Maximum Speed
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.2
BATCH_SIZE = 10
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_MAX_TOKENS = 2048
```

### Maximum Accuracy
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.3-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.1
BATCH_SIZE = 5
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_MAX_TOKENS = 4096
MAX_CONTENT_LENGTH = 12000
```

---

## Parameter Guide

| Parameter | Range | Effect |
|---|---|---|
| Temperature | 0.0–2.0 | Lower = more consistent (use 0.1 for JSON tasks) |
| Max Tokens | 64–4096 | Higher = longer responses; 4096 needed for page analysis |
| Top P | 0.0–1.0 | Lower = more focused |
| Batch Size | 1–20 | Higher = fewer API calls; lower = more accurate |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Timeout errors | ↑ `BATCH_API_TIMEOUT`, ↓ `MAX_CONTENT_LENGTH`, faster model |
| Truncated JSON | ↑ `CONTENT_VERIFICATION_MAX_TOKENS` to 4096 |
| Low accuracy | ↓ temperature (0.1), ↓ batch size, larger model |
| Slow runs | Switch to `meta/llama-3.1-70b-instruct`, ↑ batch size |

---

**Full docs**: `docs/MODEL_CONFIGURATION.md`
