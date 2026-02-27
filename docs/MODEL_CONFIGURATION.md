# AI Model Configuration Guide

This guide explains how to configure AI models and their parameters through the `setup/config.py` file.

## Overview

All AI model settings are centralized in `setup/config.py`, making it easy to:
- Switch between different models
- Adjust model parameters for better performance
- Optimize for speed vs. accuracy
- Control API usage and costs

## Configuration Location

**File**: `setup/config.py`

All model-related settings are in the "AI Model Configuration" section.

## Available Settings

### Link Classification (Stage 1)

Used for analyzing URLs and context to classify links into categories.

```python
# Model Selection
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"

# Model Parameters
LINK_CLASSIFICATION_TEMPERATURE = 0.2    # Lower = more deterministic (0.0 - 2.0)
LINK_CLASSIFICATION_MAX_TOKENS = 512    # Maximum response length
LINK_CLASSIFICATION_TOP_P = 0.9          # Nucleus sampling parameter (0.0 - 1.0)
```

**Available Models** (from NVIDIA API):
- `qwen/qwen3.5-397b-a17b` (default) - Excellent for reasoning, detailed analysis
- `meta/llama-3.1-405b-instruct` - Very capable, balanced performance
- `meta/llama-3.1-70b-instruct` - Good balance of speed and quality
- `meta/llama-3.1-8b-instruct` - Faster, good for simple tasks
- `mistralai/mixtral-8x7b-instruct-v0.1` - Fast and efficient

### Content Verification (Stage 2)

Used for analyzing actual page content to verify course pages and extract information.

```python
# Model Selection
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"

# Model Parameters
CONTENT_VERIFICATION_TEMPERATURE = 0.1   # Very low for factual extraction
CONTENT_VERIFICATION_MAX_TOKENS = 1024  # Longer for detailed analysis
CONTENT_VERIFICATION_TOP_P = 0.95        # Higher for more diverse outputs
```

**Recommended Models**:
- `meta/llama-3.1-70b-instruct` (default) - Fast content parsing
- `meta/llama-3.1-405b-instruct` - More accurate, slower
- `qwen/qwen3.5-397b-a17b` - Best reasoning for complex pages

### Batch Processing

```python
# Number of links to process per API request
BATCH_SIZE = 10
```

**Recommendations**:
- **5-10**: Good balance (default: 10)
- **1-5**: Better for complex classification
- **10-20**: Faster but may reduce accuracy

### API Configuration

```python
# NVIDIA API Endpoint
NVIDIA_API_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

# Cache Configuration
CLASSIFICATION_CACHE_FILE = "data/link_classification_cache.json"
```

### Content Analysis

```python
# Maximum characters of page content to send to AI
MAX_CONTENT_LENGTH = 8000
```

**Recommendations**:
- **5000-8000**: Good for most pages (default: 8000)
- **10000-15000**: More context for complex pages
- **3000-5000**: Faster, use less tokens

## Model Parameter Explanations

### Temperature

Controls randomness in responses.

- **0.0 - 0.3**: Very deterministic, consistent results (recommended for classification)
- **0.4 - 0.7**: Balanced creativity and consistency
- **0.8 - 1.5**: More creative, varied responses
- **1.6 - 2.0**: Highly creative, potentially inconsistent

**Recommendations**:
- Link classification: `0.2` (deterministic)
- Content verification: `0.1` (factual extraction)

### Max Tokens

Maximum number of tokens in the response.

- **256**: Very short responses, simple classifications
- **512**: Good for link classification (default)
- **1024**: Good for content analysis (default)
- **2048**: Detailed analysis with many course links

**Note**: Longer responses cost more API credits.

### Top P (Nucleus Sampling)

Controls diversity by filtering out low-probability tokens.

- **0.5 - 0.7**: Conservative, focused responses
- **0.8 - 0.9**: Balanced (default for classification: 0.9)
- **0.95 - 1.0**: More diverse (default for content: 0.95)

## Example Configurations

### 1. Maximum Accuracy (Slower, More Expensive)

```python
# Link Classification
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.1
LINK_CLASSIFICATION_MAX_TOKENS = 1024
LINK_CLASSIFICATION_TOP_P = 0.8
BATCH_SIZE = 5

# Content Verification
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-405b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.05
CONTENT_VERIFICATION_MAX_TOKENS = 2048
CONTENT_VERIFICATION_TOP_P = 0.9
MAX_CONTENT_LENGTH = 12000
```

### 2. Balanced Performance (Recommended)

```python
# Link Classification
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.2
LINK_CLASSIFICATION_MAX_TOKENS = 512
LINK_CLASSIFICATION_TOP_P = 0.9
BATCH_SIZE = 10

# Content Verification
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
CONTENT_VERIFICATION_MAX_TOKENS = 1024
CONTENT_VERIFICATION_TOP_P = 0.95
MAX_CONTENT_LENGTH = 8000
```

### 3. Maximum Speed (Less Accurate, Cheaper)

```python
# Link Classification
LINK_CLASSIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.3
LINK_CLASSIFICATION_MAX_TOKENS = 256
LINK_CLASSIFICATION_TOP_P = 0.9
BATCH_SIZE = 15

# Content Verification
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.2
CONTENT_VERIFICATION_MAX_TOKENS = 512
CONTENT_VERIFICATION_TOP_P = 0.9
MAX_CONTENT_LENGTH = 5000
```

### 4. Cost-Optimized (Minimal API Usage)

```python
# Link Classification
LINK_CLASSIFICATION_MODEL = "meta/llama-3.1-8b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.3
LINK_CLASSIFICATION_MAX_TOKENS = 256
LINK_CLASSIFICATION_TOP_P = 0.85
BATCH_SIZE = 20

# Content Verification
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.2
CONTENT_VERIFICATION_MAX_TOKENS = 512
CONTENT_VERIFICATION_TOP_P = 0.9
MAX_CONTENT_LENGTH = 4000
```

## How to Change Configuration

1. **Edit the config file**:
   ```bash
   # Open in your editor
   notepad setup\config.py
   # or
   code setup\config.py
   ```

2. **Modify the values** in the "AI Model Configuration" section

3. **Save the file** - Changes take effect immediately on next run

4. **No need to restart** - The scraper reads config on startup

## Validation

The config file automatically validates settings:

```python
# These checks run when config is imported
if LINK_CLASSIFICATION_TEMPERATURE < 0 or LINK_CLASSIFICATION_TEMPERATURE > 2:
    raise ValueError("LINK_CLASSIFICATION_TEMPERATURE must be between 0 and 2")
```

Invalid values will cause an error with a helpful message.

## Testing Configuration Changes

After changing configuration, test with a small scrape:

```bash
# Test with depth 1 (minimal scraping)
python main.py --depth 1 --save-interval 50

# Or test specific content verification
python tests/test_content_verification.py
```

## Monitoring Model Performance

### Check Logs

```bash
# View recent classification decisions
tail -f logs/scraper.log

# Search for confidence scores
grep "confidence" logs/scraper.log
```

### View Cache Stats

The classifier caches results. Check stats in logs:

```
CLASSIFICATION CACHE STATISTICS
================================
Cache Size: 1500 entries
Cache Hits: 850
Cache Misses: 650
Hit Rate: 56.7%
```

### API Usage

If using key rotation, see API stats after scraping:

```
API KEY USAGE STATISTICS
========================
Key 1: 450 calls, 5 failures
Key 2: 420 calls, 3 failures
Key 3: 380 calls, 2 failures
```

## Model Selection Tips

### For Link Classification (Stage 1)

**Use Larger Models When**:
- Dealing with ambiguous URLs
- Need high accuracy for course detection
- Can tolerate slower processing

**Use Smaller Models When**:
- URLs are straightforward
- Speed is critical
- Working with limited API credits

### For Content Verification (Stage 2)

**Use Larger Models When**:
- Pages have complex layouts
- Need accurate metadata extraction
- Want to find all embedded course links

**Use Smaller Models When**:
- Just need basic verification
- Content is well-structured
- Optimizing for speed

## Troubleshooting

### Issue: Low Classification Accuracy

**Solution**: Try:
1. Lower temperature (0.1 - 0.2)
2. Use larger model (e.g., qwen/qwen3.5-397b-a17b)
3. Reduce batch size (5-10)
4. Increase max_tokens (1024)

### Issue: Too Slow

**Solution**: Try:
1. Use smaller/faster model (llama-3.1-70b)
2. Increase batch size (15-20)
3. Reduce max_tokens (256-512)
4. Lower max_content_length (5000)

### Issue: High API Costs

**Solution**: Try:
1. Use smaller models (llama-3.1-8b)
2. Reduce max_tokens
3. Reduce max_content_length
4. Increase batch size
5. Disable content verification (`--verify-content`) for initial scraping

### Issue: Inconsistent Results

**Solution**: Try:
1. Lower temperature (0.1)
2. Lower top_p (0.7-0.8)
3. Use more deterministic model
4. Enable caching (always on by default)

## Advanced: Runtime Model Override

You can override config values programmatically:

```python
from utils.link_classifier import LinkClassifier

# Override default model
classifier = LinkClassifier(
    model="meta/llama-3.1-405b-instruct",  # Different model
    cache_file="data/custom_cache.json"
)

# Use custom model for content verification
result = classifier.verify_course_page_content(
    url="https://example.edu/course/",
    content_model="qwen/qwen3.5-397b-a17b"  # Override
)
```

## Best Practices

1. **Start with defaults** - They're well-tuned for general use
2. **Test changes** - Always test after modifying config
3. **Monitor logs** - Watch for accuracy and performance issues
4. **Use caching** - Significantly reduces API calls
5. **Balance cost vs. accuracy** - Adjust based on your budget
6. **Document changes** - Comment your modifications in config.py

## NVIDIA API Model Catalog

For the full list of available models:
- Visit: https://build.nvidia.com/explore/discover
- Filter by "Chat" or "Text" models
- Check model cards for capabilities and pricing

## Summary

- ✅ All model settings are in one place: `setup/config.py`
- ✅ Change models and parameters without touching code
- ✅ Automatic validation prevents invalid configurations
- ✅ Multiple preset configurations for different use cases
- ✅ Easy testing and monitoring of configuration changes
