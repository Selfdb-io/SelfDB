#!/bin/bash

echo "Rebuilding SelfDB containers (development mode)"
echo "This will rebuild all containers while preserving your data in Docker volumes."

# Stop existing containers
echo "Stopping existing containers..."
docker compose down


# Rebuild and start containers
echo "Rebuilding and starting containers..."
docker compose up -d --build

# Check if services are running
echo "Checking service status..."
docker compose ps

echo "Rebuild complete! Your data in Docker volumes has been preserved."
echo "- Frontend: http://localhost:3000"
echo "- API: http://localhost:8000"
echo "- Storage service: http://localhost:8001"
