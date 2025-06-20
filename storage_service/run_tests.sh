#!/bin/bash

# Script to run storage service tests

# Parse command line arguments
FILE_SIZE="small"  # Default to small (10MB)
while [[ $# -gt 0 ]]; do
  case $1 in
    --size=*)
      FILE_SIZE="${1#*=}"
      shift
      ;;
    --help)
      echo "Usage: $0 [--size=small|medium|large|extra_large|all]"
      echo "  small: 10MB (default)"
      echo "  medium: 50MB"
      echo "  large: 500MB"
      echo "  extra_large: 1GB"
      echo "  all: Run all sizes (warning: takes a long time)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo "Running storage service tests with file size: $FILE_SIZE"
echo "Setting up test environment..."

# Create a virtual environment for testing if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install pytest and required packages
echo "Installing required packages..."
pip install pytest pytest-asyncio httpx aiofiles pydantic-settings fastapi python-multipart requests

# Set environment variables for testing
export STORAGE_SERVICE_API_KEY="test-api-key"
export STORAGE_BASE_PATH="/tmp/selfdb-test-storage"
export TEST_FILE_SIZE="$FILE_SIZE"

# Create test storage directory
mkdir -p "$STORAGE_BASE_PATH"

# Clear any cached data
echo "Clearing any cached data..."
rm -rf "$STORAGE_BASE_PATH"/*

# Run the requirements test with the specified file size
echo "Running requirements test with $FILE_SIZE file size..."
PYTHONPATH=$(pwd) python tests/test_requirements.py

# Deactivate the virtual environment
deactivate
