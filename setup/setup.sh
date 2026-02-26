#!/bin/bash
# Setup script for Intelligent Web Scraper (Linux/Mac)
# Requires: Python 3.13

set -e  # Exit on error

echo "Setting up Intelligent Web Scraper..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed.${NC}"
    echo "Please install Python 3.13 and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${CYAN}Found Python:${NC} $PYTHON_VERSION"

# Check Python version (require 3.13)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -ne 13 ]; then
    echo -e "${RED}Error: Python 3.13 is required.${NC}"
    echo -e "${YELLOW}Current version: $PYTHON_VERSION${NC}"
    echo "Please install Python 3.13 from: https://www.python.org/downloads/"
    exit 1
fi

echo ""

# Check if .venv exists
if [ -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
    read -p "Do you want to recreate it? (y/N): " response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${YELLOW}Removing existing .venv...${NC}"
        rm -rf .venv
    else
        echo -e "${GREEN}Using existing .venv.${NC}"
        echo ""
        echo -e "${CYAN}To activate the virtual environment, run:${NC}"
        echo "  source .venv/bin/activate"
        exit 0
    fi
fi

# Create virtual environment
echo -e "${CYAN}Creating virtual environment (.venv)...${NC}"
python3 -m venv .venv

if [ ! -d ".venv" ]; then
    echo -e "${RED}Failed to create virtual environment.${NC}"
    echo "Make sure Python 3.13 and venv module are installed."
    exit 1
fi

# Activate virtual environment
echo -e "${CYAN}Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip
echo -e "${CYAN}Upgrading pip...${NC}"
python -m pip install --upgrade pip --quiet

# Install requirements
echo -e "${CYAN}Installing dependencies...${NC}"
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo -e "1. Copy template.env to .env"
    echo -e "   ${NC}cp template.env .env${NC}"
    echo ""
    echo -e "2. Edit .env and add your NVIDIA_API_KEY(s)"
    echo ""
    echo -e "3. Run the scraper:"
    echo -e "   ${NC}python main.py${NC}"
    echo ""
    echo -e "${CYAN}To activate the virtual environment in future sessions:${NC}"
    echo "  source .venv/bin/activate"
else
    echo ""
    echo -e "${RED}Installation failed. Please check the errors above.${NC}"
    exit 1
fi
