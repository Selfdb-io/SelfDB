#!/bin/bash

# SelfDB TDD Test Runner
# This script activates the virtual environment and runs all tests

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m' 
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 SelfDB TDD Test Runner${NC}"
echo -e "${BLUE}=========================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Run: uv venv${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if requirements are installed
if ! uv run python -c "import pytest" 2>/dev/null; then
    echo -e "${BLUE}📦 Installing requirements...${NC}"
    uv pip install -r requirements.txt
fi

# Set PYTHONPATH to current directory for importing src modules
export PYTHONPATH=".:$PYTHONPATH"

# Run tests with different options based on arguments
if [ "$1" = "unit" ]; then
    echo -e "${GREEN}🏃 Running unit tests only...${NC}"
    uv run pytest tests/ -m "unit" "${@:2}"
elif [ "$1" = "integration" ]; then
    echo -e "${GREEN}🏃 Running integration tests only...${NC}"
    uv run pytest tests/ -m "integration" "${@:2}"
elif [ "$1" = "coverage" ]; then
    echo -e "${GREEN}🏃 Running all tests with coverage...${NC}"
    uv run pytest tests/ --cov-report=html --cov-report=term "${@:2}"
elif [ "$1" = "watch" ]; then
    echo -e "${GREEN}👀 Running tests in watch mode...${NC}"
    uv run pytest tests/ --tb=short -v "${@:2}"
    # Note: For true watch mode, you'd need pytest-watch: pip install pytest-watch
else
    echo -e "${GREEN}🏃 Running all tests...${NC}"
    uv run pytest tests/ "$@"
fi

echo -e "${GREEN}✅ Test execution completed${NC}"