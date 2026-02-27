# Quick Start Guide - NVIDIA API Setup

## Step 1: Get Your NVIDIA API Key

1. Visit: https://build.nvidia.com/
2. Sign in or create a free account
3. Navigate to any model (e.g., Qwen 3.5)
4. Click "Get API Key" or "Build with this model"
5. Copy your API key

## Step 2: Set Up Virtual Environment

**Option A - Using PowerShell:**
```powershell
.\setup.ps1
```

**Option B - Using CMD:**
```cmd
setup.bat
```

**Option C - Manual Setup:**
```powershell
# Create venv
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# Or activate (CMD)
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Configure Environment

```powershell
# Copy template
Copy-Item template.env .env

# Edit .env file and add your NVIDIA API key(s)
notepad .env
```

Replace `your_nvidia_api_key_here` with your actual API key.

**Pro Tip:** Add multiple API keys for higher rate limits:
```
NVIDIA_API_KEY_1=nvapi-xxxxx
NVIDIA_API_KEY_2=nvapi-yyyyy
NVIDIA_API_KEY_3=nvapi-zzzzz
```
The system will automatically rotate between them!

## Step 4: Run the Scraper

**Basic usage:**
```powershell
python main.py
```

**Custom URL:**
```powershell
python main.py --url "https://example.edu/courses"
```

**Deeper crawl:**
```powershell
python main.py --depth 3
```

**Without AI (faster, no classification):**
```powershell
python main.py --no-ai
```

## Troubleshooting

### PowerShell Execution Policy Error

If you get an error running `setup.ps1`, you may need to allow script execution:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try running `.\setup.ps1` again.

### API Key Not Found

Make sure:
1. You copied `template.env` to `.env` (not `.env.txt`)
2. You added your actual API key without quotes
3. You're running from the correct directory

Example `.env` file:
```
NVIDIA_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Python Not Found

Install Python 3.8+ from: https://www.python.org/downloads/

### Import Errors

Make sure you activated the virtual environment:
```powershell
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` in your terminal prompt.

## Next Steps

- Check `data/scraped_links.json` for results
- Review `logs/` folder for detailed logs
- Modify `prompts/sys.txt` to customize AI behavior
- See `examples.py` for more usage patterns

## NVIDIA API Notes

- **Free tier**: Available with rate limits
- **Model used**: Qwen 3.5 (397B parameters)
- **Alternative models**: Check https://build.nvidia.com/explore/discover
- **Response time**: Typically 1-3 seconds per link classification

Enjoy your intelligent web scraping! 🚀
