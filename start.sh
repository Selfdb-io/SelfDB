#!/bin/bash

# Using Docker named volumes instead of local directories
echo "Setting up Docker volumes..."

# Check if volumes exist and create them if needed
POSTGRES_VOLUME="$(docker volume ls -q | grep postgres_data)"
STORAGE_VOLUME="$(docker volume ls -q | grep storage_data)"
FUNCTIONS_VOLUME="$(docker volume ls -q | grep functions_data)"

# Remove existing volumes if they exist (optional, uncomment if needed)
# if [ ! -z "$POSTGRES_VOLUME" ]; then
#     echo "Removing existing PostgreSQL volume..."
#     docker volume rm postgres_data
# fi
#
# if [ ! -z "$STORAGE_VOLUME" ]; then
#     echo "Removing existing Storage volume..."
#     docker volume rm storage_data
# fi
#
# if [ ! -z "$FUNCTIONS_VOLUME" ]; then
# echo "Removing existing Functions volume..."
# docker volume rm functions_data
# fi

echo "Docker will automatically create and manage the volumes"

# Stop any existing containers
echo "Stopping any existing containers..."
docker compose down



# Generate environment file and keys if they don't exist
echo "Setting up environment file and generating keys..."
./scripts/generate_anon_key.sh

# Synchronize ANON_KEY with the backend
echo "Synchronizing ANON_KEY with the backend..."
# Check if ANON_KEY exists in .env file
if [ ! -f ".env" ]; then
    echo "Error: .env file not found. Please run scripts/generate_anon_key.sh first."
    exit 1
fi

ANON_KEY_CHECK=$(grep "^ANON_KEY=" ".env" | cut -d '=' -f2)
if [ -z "$ANON_KEY_CHECK" ]; then
    echo "Error: ANON_KEY not found in .env file. Please run scripts/generate_anon_key.sh first."
    exit 1
fi

echo "Found ANON_KEY in .env file: ${ANON_KEY_CHECK:0:5}..."
echo "ANON_KEY is now synchronized with the backend."
echo "The backend will use this key for anonymous authentication."

# Synchronize ANON_KEY with the frontend
echo "Synchronizing ANON_KEY with the frontend..."
# Path to main .env file and frontend .env file
MAIN_ENV_FILE=".env"
FRONTEND_ENV_FILE="frontend/.env"
FRONTEND_EXAMPLE_FILE="frontend/.env.example"

# Check if main .env file exists
if [ ! -f "$MAIN_ENV_FILE" ]; then
    echo "Error: Main .env file not found. Please ensure it exists before running this script."
    exit 1
fi

# Extract ANON_KEY from main .env file
ANON_KEY=$(grep "^ANON_KEY=" "$MAIN_ENV_FILE" | cut -d '=' -f2)

if [ -z "$ANON_KEY" ]; then
    echo "Error: ANON_KEY not found in main .env file. Please ensure it's properly set."
    exit 1
fi

# Extract SECRET_KEY from main .env file
SECRET_KEY=$(grep "^SECRET_KEY=" "$MAIN_ENV_FILE" | cut -d '=' -f2)

if [ -z "$SECRET_KEY" ]; then
    echo "Warning: SECRET_KEY not found in main .env file. Using default."
    SECRET_KEY="changeme_super_secret_jwt_key_32_bytes_long"
fi

# Extract API URL from main .env file (REACT_APP_API_URL)
API_URL=$(grep "^REACT_APP_API_URL=" "$MAIN_ENV_FILE" | cut -d '=' -f2)

if [ -z "$API_URL" ]; then
    echo "Warning: REACT_APP_API_URL not found in main .env file. Using default localhost URL."
    API_URL="http://localhost:8000/api/v1"
fi

# Create frontend .env file from example if it doesn't exist
if [ ! -f "$FRONTEND_ENV_FILE" ] && [ -f "$FRONTEND_EXAMPLE_FILE" ]; then
    echo "Creating frontend .env file from example..."
    cp "$FRONTEND_EXAMPLE_FILE" "$FRONTEND_ENV_FILE"
fi

# If frontend .env file doesn't exist, create a new one
if [ ! -f "$FRONTEND_ENV_FILE" ]; then
    echo "Creating new frontend .env file..."
    touch "$FRONTEND_ENV_FILE"
fi

# Check if VITE_ANON_KEY already exists in frontend .env file
if grep -q "^VITE_ANON_KEY=" "$FRONTEND_ENV_FILE"; then
    # Update existing VITE_ANON_KEY
    echo "Updating VITE_ANON_KEY in frontend .env file..."
    # Cross-platform sed command (works on both macOS and Linux)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS requires an empty string after -i
        sed -i '' "s/^VITE_ANON_KEY=.*/VITE_ANON_KEY=$ANON_KEY/" "$FRONTEND_ENV_FILE"
    else
        # Linux version
        sed -i "s/^VITE_ANON_KEY=.*/VITE_ANON_KEY=$ANON_KEY/" "$FRONTEND_ENV_FILE"
    fi
else
    # Add VITE_ANON_KEY to frontend .env file
    echo "Adding VITE_ANON_KEY to frontend .env file..."
    echo "" >> "$FRONTEND_ENV_FILE"
    echo "# Anonymous API Key" >> "$FRONTEND_ENV_FILE"
    echo "VITE_ANON_KEY=$ANON_KEY" >> "$FRONTEND_ENV_FILE"
fi

# Check if VITE_API_URL already exists in frontend .env file
if grep -q "^VITE_API_URL=" "$FRONTEND_ENV_FILE"; then
    # Update existing VITE_API_URL
    echo "Updating VITE_API_URL in frontend .env file..."
    # Cross-platform sed command (works on both macOS and Linux)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS requires an empty string after -i
        sed -i '' "s|^VITE_API_URL=.*|VITE_API_URL=$API_URL|" "$FRONTEND_ENV_FILE"
    else
        # Linux version
        sed -i "s|^VITE_API_URL=.*|VITE_API_URL=$API_URL|" "$FRONTEND_ENV_FILE"
    fi
else
    # Add VITE_API_URL to frontend .env file
    echo "Adding VITE_API_URL to frontend .env file..."
    echo "" >> "$FRONTEND_ENV_FILE"
    echo "# API URL" >> "$FRONTEND_ENV_FILE"
    echo "VITE_API_URL=$API_URL" >> "$FRONTEND_ENV_FILE"
fi

echo "Frontend .env file synchronized with VITE_ANON_KEY and VITE_API_URL."

# Synchronize environment variables with storage service
echo "Synchronizing environment variables with storage service..."

STORAGE_SERVICE_ENV_FILE="storage_service/.env"

# Extract STORAGE_SERVICE_EXTERNAL_URL from main .env file
STORAGE_EXTERNAL_URL=$(grep "^STORAGE_SERVICE_EXTERNAL_URL=" "$MAIN_ENV_FILE" | cut -d '=' -f2)

if [ -z "$STORAGE_EXTERNAL_URL" ]; then
    echo "Warning: STORAGE_SERVICE_EXTERNAL_URL not found in main .env file. Using default localhost URL."
    STORAGE_EXTERNAL_URL="http://localhost:8001"
fi

# Extract STORAGE_SERVICE_API_KEY from main .env file
STORAGE_API_KEY=$(grep "^STORAGE_SERVICE_API_KEY=" "$MAIN_ENV_FILE" | cut -d '=' -f2)

if [ -z "$STORAGE_API_KEY" ]; then
    echo "Warning: STORAGE_SERVICE_API_KEY not found in main .env file."
fi

# Create storage service .env file if it doesn't exist
if [ ! -f "$STORAGE_SERVICE_ENV_FILE" ]; then
    echo "Creating storage service .env file..."
    touch "$STORAGE_SERVICE_ENV_FILE"
    echo "# Storage Service Configuration" >> "$STORAGE_SERVICE_ENV_FILE"
    echo "SECRET_KEY=$SECRET_KEY" >> "$STORAGE_SERVICE_ENV_FILE"
    echo "ALGORITHM=HS256" >> "$STORAGE_SERVICE_ENV_FILE"
    echo "ANON_KEY=$ANON_KEY" >> "$STORAGE_SERVICE_ENV_FILE"
    echo "STORAGE_SERVICE_PUBLIC_URL=$STORAGE_EXTERNAL_URL" >> "$STORAGE_SERVICE_ENV_FILE"
    if [ ! -z "$STORAGE_API_KEY" ]; then
        echo "STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY" >> "$STORAGE_SERVICE_ENV_FILE"
    fi
    echo "Created storage service .env file"
else
    # Update existing storage service .env file
    
    # Update STORAGE_SERVICE_PUBLIC_URL
    if grep -q "^STORAGE_SERVICE_PUBLIC_URL=" "$STORAGE_SERVICE_ENV_FILE"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^STORAGE_SERVICE_PUBLIC_URL=.*|STORAGE_SERVICE_PUBLIC_URL=$STORAGE_EXTERNAL_URL|" "$STORAGE_SERVICE_ENV_FILE"
        else
            sed -i "s|^STORAGE_SERVICE_PUBLIC_URL=.*|STORAGE_SERVICE_PUBLIC_URL=$STORAGE_EXTERNAL_URL|" "$STORAGE_SERVICE_ENV_FILE"
        fi
        echo "Updated STORAGE_SERVICE_PUBLIC_URL in storage service"
    else
        echo "" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "# Storage Service Public URL" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "STORAGE_SERVICE_PUBLIC_URL=$STORAGE_EXTERNAL_URL" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "Added STORAGE_SERVICE_PUBLIC_URL to storage service"
    fi
    
    # Update ANON_KEY
    if grep -q "^ANON_KEY=" "$STORAGE_SERVICE_ENV_FILE"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^ANON_KEY=.*/ANON_KEY=$ANON_KEY/" "$STORAGE_SERVICE_ENV_FILE"
        else
            sed -i "s/^ANON_KEY=.*/ANON_KEY=$ANON_KEY/" "$STORAGE_SERVICE_ENV_FILE"
        fi
        echo "Updated ANON_KEY in storage service"
    else
        echo "" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "# Anonymous API Key" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "ANON_KEY=$ANON_KEY" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "Added ANON_KEY to storage service"
    fi
    
    # Update SECRET_KEY
    if grep -q "^SECRET_KEY=" "$STORAGE_SERVICE_ENV_FILE"; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$STORAGE_SERVICE_ENV_FILE"
        else
            sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$STORAGE_SERVICE_ENV_FILE"
        fi
        echo "Updated SECRET_KEY in storage service"
    else
        echo "" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "# JWT Secret Key" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "SECRET_KEY=$SECRET_KEY" >> "$STORAGE_SERVICE_ENV_FILE"
        echo "Added SECRET_KEY to storage service"
    fi
    
    # Update STORAGE_SERVICE_API_KEY if it exists
    if [ ! -z "$STORAGE_API_KEY" ]; then
        if grep -q "^STORAGE_SERVICE_API_KEY=" "$STORAGE_SERVICE_ENV_FILE"; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/^STORAGE_SERVICE_API_KEY=.*/STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY/" "$STORAGE_SERVICE_ENV_FILE"
            else
                sed -i "s/^STORAGE_SERVICE_API_KEY=.*/STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY/" "$STORAGE_SERVICE_ENV_FILE"
            fi
            echo "Updated STORAGE_SERVICE_API_KEY in storage service"
        else
            echo "" >> "$STORAGE_SERVICE_ENV_FILE"
            echo "# Storage Service API Key" >> "$STORAGE_SERVICE_ENV_FILE"
            echo "STORAGE_SERVICE_API_KEY=$STORAGE_API_KEY" >> "$STORAGE_SERVICE_ENV_FILE"
            echo "Added STORAGE_SERVICE_API_KEY to storage service"
        fi
    fi
fi

echo "Storage service .env file synchronized."

# Synchronize environment variables with sample apps
echo "Synchronizing environment variables with sample apps..."

# Extract STORAGE_SERVICE_EXTERNAL_URL from main .env file
STORAGE_URL=$(grep "^STORAGE_SERVICE_EXTERNAL_URL=" "$MAIN_ENV_FILE" | cut -d '=' -f2)

if [ -z "$STORAGE_URL" ]; then
    echo "Warning: STORAGE_SERVICE_EXTERNAL_URL not found in main .env file. Using default localhost URL."
    STORAGE_URL="http://localhost:8001"
fi

# Find all sample app directories that contain .env files or need them
SAMPLE_APPS_DIR="sample-apps"

if [ -d "$SAMPLE_APPS_DIR" ]; then
    # Find all subdirectories in sample-apps
    for app_dir in "$SAMPLE_APPS_DIR"/*; do
        if [ -d "$app_dir" ]; then
            APP_NAME=$(basename "$app_dir")
            APP_ENV_FILE="$app_dir/.env"
            
            echo "Processing sample app: $APP_NAME"
            
            # Create .env file if it doesn't exist
            if [ ! -f "$APP_ENV_FILE" ]; then
                echo "Creating .env file for $APP_NAME..."
                touch "$APP_ENV_FILE"
                echo "# SelfDB API URL" >> "$APP_ENV_FILE"
                echo "VITE_API_URL=$API_URL" >> "$APP_ENV_FILE"
                echo "" >> "$APP_ENV_FILE"
                echo "# Anonymous API Key" >> "$APP_ENV_FILE"
                echo "VITE_ANON_KEY=$ANON_KEY" >> "$APP_ENV_FILE"
                echo "" >> "$APP_ENV_FILE"
                echo "# Storage Service URL" >> "$APP_ENV_FILE"
                echo "VITE_STORAGE_URL=$STORAGE_URL" >> "$APP_ENV_FILE"
                echo "Created .env file for $APP_NAME"
                continue
            fi
            
            # Update VITE_API_URL
            if grep -q "^VITE_API_URL=" "$APP_ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^VITE_API_URL=.*|VITE_API_URL=$API_URL|" "$APP_ENV_FILE"
                else
                    sed -i "s|^VITE_API_URL=.*|VITE_API_URL=$API_URL|" "$APP_ENV_FILE"
                fi
                echo "Updated VITE_API_URL in $APP_NAME"
            else
                echo "" >> "$APP_ENV_FILE"
                echo "# SelfDB API URL" >> "$APP_ENV_FILE"
                echo "VITE_API_URL=$API_URL" >> "$APP_ENV_FILE"
                echo "Added VITE_API_URL to $APP_NAME"
            fi
            
            # Update VITE_ANON_KEY
            if grep -q "^VITE_ANON_KEY=" "$APP_ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/^VITE_ANON_KEY=.*/VITE_ANON_KEY=$ANON_KEY/" "$APP_ENV_FILE"
                else
                    sed -i "s/^VITE_ANON_KEY=.*/VITE_ANON_KEY=$ANON_KEY/" "$APP_ENV_FILE"
                fi
                echo "Updated VITE_ANON_KEY in $APP_NAME"
            else
                echo "" >> "$APP_ENV_FILE"
                echo "# Anonymous API Key" >> "$APP_ENV_FILE"
                echo "VITE_ANON_KEY=$ANON_KEY" >> "$APP_ENV_FILE"
                echo "Added VITE_ANON_KEY to $APP_NAME"
            fi
            
            # Update VITE_STORAGE_URL
            if grep -q "^VITE_STORAGE_URL=" "$APP_ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^VITE_STORAGE_URL=.*|VITE_STORAGE_URL=$STORAGE_URL|" "$APP_ENV_FILE"
                else
                    sed -i "s|^VITE_STORAGE_URL=.*|VITE_STORAGE_URL=$STORAGE_URL|" "$APP_ENV_FILE"
                fi
                echo "Updated VITE_STORAGE_URL in $APP_NAME"
            else
                echo "" >> "$APP_ENV_FILE"
                echo "# Storage Service URL" >> "$APP_ENV_FILE"
                echo "VITE_STORAGE_URL=$STORAGE_URL" >> "$APP_ENV_FILE"
                echo "Added VITE_STORAGE_URL to $APP_NAME"
            fi
            
            # Handle legacy variable names (for apps that might still use old naming)
            # Update VITE_SELFDB_URL if it exists (legacy naming)
            if grep -q "^VITE_SELFDB_URL=" "$APP_ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^VITE_SELFDB_URL=.*|VITE_SELFDB_URL=$API_URL|" "$APP_ENV_FILE"
                else
                    sed -i "s|^VITE_SELFDB_URL=.*|VITE_SELFDB_URL=$API_URL|" "$APP_ENV_FILE"
                fi
                echo "Updated legacy VITE_SELFDB_URL in $APP_NAME"
            fi
            
            # Update VITE_SELFDB_STORAGE_URL if it exists (legacy naming)
            if grep -q "^VITE_SELFDB_STORAGE_URL=" "$APP_ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s|^VITE_SELFDB_STORAGE_URL=.*|VITE_SELFDB_STORAGE_URL=$STORAGE_URL|" "$APP_ENV_FILE"
                else
                    sed -i "s|^VITE_SELFDB_STORAGE_URL=.*|VITE_SELFDB_STORAGE_URL=$STORAGE_URL|" "$APP_ENV_FILE"
                fi
                echo "Updated legacy VITE_SELFDB_STORAGE_URL in $APP_NAME"
            fi
            
            # Update VITE_SELFDB_ANON_KEY if it exists (legacy naming)
            if grep -q "^VITE_SELFDB_ANON_KEY=" "$APP_ENV_FILE"; then
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/^VITE_SELFDB_ANON_KEY=.*/VITE_SELFDB_ANON_KEY=$ANON_KEY/" "$APP_ENV_FILE"
                else
                    sed -i "s/^VITE_SELFDB_ANON_KEY=.*/VITE_SELFDB_ANON_KEY=$ANON_KEY/" "$APP_ENV_FILE"
                fi
                echo "Updated legacy VITE_SELFDB_ANON_KEY in $APP_NAME"
            fi
            
            echo "Synchronized $APP_NAME environment variables"
        fi
    done
    
    echo "All sample apps synchronized with environment variables."
else
    echo "Sample apps directory not found. Skipping sample app synchronization."
fi

# Start the services
echo "Starting SelfDB services..."
docker compose up -d --build

# Check if services are running
echo "Checking service status..."
docker compose ps

echo "SelfDB is now running!"
echo "- Frontend: http://localhost:3000"
echo "- API: http://localhost:8000"
echo "- Storage service: http://localhost:8001"
