#!/bin/bash

# NetStudio Virtual Environment Setup Script
# This script automates the creation and setup of a Python virtual environment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  NetStudio Virtual Environment Setup  ${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Check Python version
echo -e "${YELLOW}[1/7]${NC} Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"

    # Check if version is 3.8+
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        echo -e "${RED}✗${NC} Python 3.8+ is required. You have $PYTHON_VERSION"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Step 2: Check if venv exists
echo -e "\n${YELLOW}[2/7]${NC} Checking for existing virtual environment..."
if [ -d "$PROJECT_DIR/venv" ]; then
    echo -e "${YELLOW}!${NC} Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removing existing virtual environment...${NC}"
        rm -rf "$PROJECT_DIR/venv"
    else
        echo -e "${GREEN}✓${NC} Using existing virtual environment"
        SKIP_CREATE=true
    fi
fi

# Step 3: Create virtual environment
if [ "$SKIP_CREATE" != true ]; then
    echo -e "\n${YELLOW}[3/7]${NC} Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/venv"
    echo -e "${GREEN}✓${NC} Virtual environment created at $PROJECT_DIR/venv"
else
    echo -e "\n${YELLOW}[3/7]${NC} Skipping virtual environment creation"
fi

# Step 4: Activate virtual environment
echo -e "\n${YELLOW}[4/7]${NC} Activating virtual environment..."
source "$PROJECT_DIR/venv/bin/activate"
echo -e "${GREEN}✓${NC} Virtual environment activated"

# Step 5: Upgrade pip
echo -e "\n${YELLOW}[5/7]${NC} Upgrading pip..."
pip install --upgrade pip --quiet
PIP_VERSION=$(pip --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} pip upgraded to version $PIP_VERSION"

# Step 6: Install dependencies
echo -e "\n${YELLOW}[6/7]${NC} Installing dependencies..."
echo -e "This may take a few minutes..."

# Check if requirements.txt exists
if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${RED}✗${NC} requirements.txt not found!"
    exit 1
fi

# Install core dependencies
pip install -r "$PROJECT_DIR/requirements.txt" --quiet

echo -e "${GREEN}✓${NC} Dependencies installed successfully"

# Step 7: Set environment variables
echo -e "\n${YELLOW}[7/7]${NC} Setting environment variables..."

# Detect shell
if [ -n "$BASH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        SHELL_CONFIG="$HOME/.bash_profile"
    fi
elif [ -n "$ZSH_VERSION" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
else
    SHELL_CONFIG="$HOME/.profile"
fi

# Check if VECTOR_PY_DIR is already set
if grep -q "VECTOR_PY_DIR" "$SHELL_CONFIG" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} VECTOR_PY_DIR already configured in $SHELL_CONFIG"
else
    echo -e "Adding VECTOR_PY_DIR to $SHELL_CONFIG..."
    echo "" >> "$SHELL_CONFIG"
    echo "# NetStudio environment variables" >> "$SHELL_CONFIG"
    echo "export VECTOR_PY_DIR=\"$PROJECT_DIR\"" >> "$SHELL_CONFIG"
    echo "export PATH=\"\$PATH:$PROJECT_DIR\"" >> "$SHELL_CONFIG"
    echo -e "${GREEN}✓${NC} Environment variables added to $SHELL_CONFIG"
fi

# Set for current session
export VECTOR_PY_DIR="$PROJECT_DIR"
export PATH="$PATH:$PROJECT_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete! ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Virtual Environment Info:${NC}"
echo -e "  Location: $PROJECT_DIR/venv"
echo -e "  Python: $(python --version)"
echo -e "  Pip: $(pip --version | awk '{print $2}')"
echo -e "  Packages installed: $(pip list --format=freeze | wc -l)"
echo ""
echo -e "${BLUE}Environment Variables:${NC}"
echo -e "  VECTOR_PY_DIR=$VECTOR_PY_DIR"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. ${GREEN}Reload your shell configuration:${NC}"
echo -e "   ${BLUE}source $SHELL_CONFIG${NC}"
echo ""
echo -e "2. ${GREEN}Or activate the virtual environment manually:${NC}"
echo -e "   ${BLUE}source venv/bin/activate${NC}"
echo ""
echo -e "3. ${GREEN}Run the application:${NC}"
echo -e "   ${BLUE}python launcher.py${NC}        # TUI interface"
echo -e "   ${BLUE}python api/main.py${NC}        # API server"
echo -e "   ${BLUE}python main.py${NC}            # Legacy CLI"
echo ""
echo -e "4. ${GREEN}Check service status:${NC}"
echo -e "   ${BLUE}curl http://localhost:8000/api/health${NC}"
echo ""
echo -e "${YELLOW}To deactivate the virtual environment later, just run:${NC}"
echo -e "   ${BLUE}deactivate${NC}"
echo ""
echo -e "${GREEN}Happy automating! 🚀${NC}"
echo ""
