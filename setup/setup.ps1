# Setup script for Intelligent Web Scraper
# This script creates a virtual environment and installs dependencies
# Requires: Python 3.13

Write-Host "Setting up Intelligent Web Scraper..." -ForegroundColor Green
Write-Host ""

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Cyan
    
    # Extract version number
    if ($pythonVersion -match 'Python (\d+)\.(\d+)') {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        
        if ($major -ne 3 -or $minor -ne 13) {
            Write-Host "Error: Python 3.13 is required." -ForegroundColor Red
            Write-Host "Current version: $pythonVersion" -ForegroundColor Yellow
            Write-Host "Please install Python 3.13 from: https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }
} catch {
    Write-Host "Error: Python not found." -ForegroundColor Red
    Write-Host "Please install Python 3.13 from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check if .venv exists
if (Test-Path ".venv") {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
    $response = Read-Host "Do you want to recreate it? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Removing existing .venv..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
    } else {
        Write-Host "Using existing .venv." -ForegroundColor Green
        Write-Host ""
        Write-Host "To activate the virtual environment, run:" -ForegroundColor Cyan
        Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
        exit 0
    }
}

# Create virtual environment
Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
python -m venv .venv

if (-not (Test-Path ".venv")) {
    Write-Host "Failed to create virtual environment." -ForegroundColor Red
    Write-Host "Make sure Python 3.13 is installed and in your PATH." -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Copy template.env to .env" -ForegroundColor White
    Write-Host "   Copy-Item template.env .env" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Edit .env and add your NVIDIA_API_KEY" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Run the scraper:" -ForegroundColor White
    Write-Host "   python main.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To activate the virtual environment in future sessions:" -ForegroundColor Cyan
    Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "Installation failed. Please check the errors above." -ForegroundColor Red
    exit 1
}
