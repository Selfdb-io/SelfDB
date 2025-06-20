#!/bin/bash
set -e

# Path to .env file
ENV_FILE=".env"

# Check if .env file exists, create from example if not
if [ ! -f "$ENV_FILE" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env file from .env.example..."
        cp ".env.example" "$ENV_FILE"
        echo "Created .env file from .env.example"
    else
        echo "Error: Neither .env nor .env.example file found. Please create .env.example first."
        exit 1
    fi
fi

# Check if ANON_KEY already exists and has a value in .env
ANON_KEY_VALUE=$(grep "^ANON_KEY=" "$ENV_FILE" | cut -d '=' -f2 | sed 's/#.*//' | tr -d ' ')

if [ -n "$ANON_KEY_VALUE" ] && [ "$ANON_KEY_VALUE" != "" ]; then
    echo "ANON_KEY already exists with value in $ENV_FILE. Skipping generation."
else
    # Generate a secure random key
    ANON_KEY=$(openssl rand -hex 32)
    
    # Check if ANON_KEY line exists (but empty)
    if grep -q "^ANON_KEY=" "$ENV_FILE"; then
        # Replace the existing empty ANON_KEY line
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^ANON_KEY=.*/ANON_KEY=$ANON_KEY/" "$ENV_FILE"
        else
            sed -i "s/^ANON_KEY=.*/ANON_KEY=$ANON_KEY/" "$ENV_FILE"
        fi
        echo "Updated existing ANON_KEY in $ENV_FILE"
    else
        # Append ANON_KEY to .env file
        echo "" >> "$ENV_FILE"
        echo "# Anonymous API Key for public access" >> "$ENV_FILE"
        echo "ANON_KEY=$ANON_KEY" >> "$ENV_FILE"
        echo "Added new ANON_KEY to $ENV_FILE"
    fi
fi

# Check if STORAGE_SERVICE_API_KEY already exists and has a value in .env
STORAGE_API_KEY_VALUE=$(grep "^STORAGE_SERVICE_API_KEY=" "$ENV_FILE" | cut -d '=' -f2 | sed 's/#.*//' | tr -d ' ')

if [ -n "$STORAGE_API_KEY_VALUE" ] && [ "$STORAGE_API_KEY_VALUE" != "" ]; then
    echo "STORAGE_SERVICE_API_KEY already exists with value in $ENV_FILE. Skipping generation."
else
    # Generate a secure random key for storage service
    STORAGE_API_KEY=$(openssl rand -hex 32)
    
    # Check if STORAGE_SERVICE_API_KEY line exists (but empty)
    if grep -q "^STORAGE_SERVICE_API_KEY=" "$ENV_FILE"; then
        # Replace the existing empty STORAGE_SERVICE_API_KEY line
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^STORAGE_SERVICE_API_KEY=.*/STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY/" "$ENV_FILE"
        else
            sed -i "s/^STORAGE_SERVICE_API_KEY=.*/STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY/" "$ENV_FILE"
        fi
        echo "Updated existing STORAGE_SERVICE_API_KEY in $ENV_FILE"
    else
        # Append STORAGE_SERVICE_API_KEY to .env file
        echo "" >> "$ENV_FILE"
        echo "# Storage Service API Key" >> "$ENV_FILE"
        echo "STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY" >> "$ENV_FILE"
        echo "Added new STORAGE_SERVICE_API_KEY to $ENV_FILE"
    fi
fi
