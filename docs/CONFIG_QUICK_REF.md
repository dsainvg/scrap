# Quick Reference: AI Model Configuration

## File Location
`setup/config.py` - Edit this file to configure AI models and parameters

---

## Link Classification (Stage 1)
Classifies URLs based on context

```python
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.2     # 0.0 = deterministic, 2.0 = creative
LINK_CLASSIFICATION_MAX_TOKENS = 512      # Response length limit
LINK_CLASSIFICATION_TOP_P = 0.9           # Diversity (0.0-1.0)
BATCH_SIZE = 10                           # Links per API call
```

---

## Content Verification (Stage 2)
Verifies course pages by analyzing content (when `--verify-content` enabled)

```python
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1    # Low for factual extraction
CONTENT_VERIFICATION_MAX_TOKENS = 1024    # Longer for detailed analysis
CONTENT_VERIFICATION_TOP_P = 0.95         # Higher diversity
MAX_CONTENT_LENGTH = 8000                 # Max chars to analyze
```

---

## Recommended Models

| Speed | Model | Best For |
|-------|-------|----------|
| ⚡⚡⚡ | `meta/llama-3.1-8b-instruct` | Fast, simple tasks |
| ⚡⚡ | `meta/llama-3.1-70b-instruct` | Balanced speed/quality |
| ⚡ | `meta/llama-3.1-405b-instruct` | High accuracy |
| ⚡ | `qwen/qwen3.5-397b-a17b` | Best reasoning |

---

## Quick Presets

### Maximum Accuracy
```python
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.1
BATCH_SIZE = 5
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-405b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.05
```

### Balanced (Default)
```python
LINK_CLASSIFICATION_MODEL = "qwen/qwen3.5-397b-a17b"
LINK_CLASSIFICATION_TEMPERATURE = 0.2
BATCH_SIZE = 10
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.1
```

### Maximum Speed
```python
LINK_CLASSIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
LINK_CLASSIFICATION_TEMPERATURE = 0.3
BATCH_SIZE = 15
CONTENT_VERIFICATION_MODEL = "meta/llama-3.1-70b-instruct"
CONTENT_VERIFICATION_TEMPERATURE = 0.2
```

---

## Parameter Guide

| Parameter | Range | Recommended | Effect |
|-----------|-------|-------------|--------|
| **Temperature** | 0.0 - 2.0 | 0.1 - 0.3 | Lower = more consistent |
| **Max Tokens** | 100 - 4096 | 512 - 1024 | Higher = longer responses |
| **Top P** | 0.0 - 1.0 | 0.9 - 0.95 | Higher = more diverse |
| **Batch Size** | 1 - 50 | 10 - 15 | Higher = faster, less accurate |

---

## How to Change

1. Edit `setup/config.py`
2. Modify values in "AI Model Configuration" section
3. Save file
4. Run: `python main.py`

Changes take effect immediately!

---

## Testing Changes

```bash
# Quick test
python main.py --depth 1

# Test content verification
python tests/test_content_verification.py

# Check logs
tail -f logs/scraper.log
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Low accuracy | ↓ Temperature (0.1), ↑ Model size |
| Too slow | ↓ Model size, ↑ Batch size |
| High costs | ↓ Max tokens, ↓ Content length |
| Inconsistent | ↓ Temperature, ↓ Top P |

---

**Full Documentation**: See `docs/MODEL_CONFIGURATION.md`
