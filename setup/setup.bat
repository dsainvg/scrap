@echo off
REM Setup script for Intelligent Web Scraper (Windows CMD)
REM Requires: Python 3.13

echo Setting up Intelligent Web Scraper...
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found.
    echo Please install Python 3.13 from: https://www.python.org/downloads/
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo Found: Python %PYTHON_VER%

REM Check if version is 3.13
echo %PYTHON_VER% | findstr /C:"3.13" >nul
if errorlevel 1 (
    echo Error: Python 3.13 is required.
    echo Current version: %PYTHON_VER%
    echo Please install Python 3.13 from: https://www.python.org/downloads/
    exit /b 1
)
echo.

REM Check if .venv exists
if exist ".venv" (
    echo Virtual environment already exists.
    set /p response="Do you want to recreate it? (y/N): "
    if /i "%response%"=="y" (
        echo Removing existing .venv...
        rmdir /s /q .venv
    ) else (
        echo Using existing .venv.
        echo.
        echo To activate the virtual environment, run:
        echo   .venv\Scripts\activate.bat
        exit /b 0
    )
)

REM Create virtual environment
echo Creating virtual environment (.venv)...
python -m venv .venv

if not exist ".venv" (
    echo Failed to create virtual environment.
    echo Make sure Python 3.13 is installed and in your PATH.
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Setup complete!
    echo.
    echo Next steps:
    echo 1. Copy template.env to .env
    echo    copy template.env .env
    echo.
    echo 2. Edit .env and add your NVIDIA_API_KEY
    echo.
    echo 3. Run the scraper:
    echo    python main.py
    echo.
    echo To activate the virtual environment in future sessions:
    echo   .venv\Scripts\activate.bat
) else (
    echo.
    echo Installation failed. Please check the errors above.
    exit /b 1
)
