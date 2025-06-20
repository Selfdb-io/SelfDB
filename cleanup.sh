#!/bin/bash

echo "This script will stop all containers, remove Docker volumes, and clean up Docker images and build history."
echo "WARNING: This will delete all your data and related Docker resources! Make sure you have backups if needed."
read -p "Are you sure you want to continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Operation cancelled."
    exit 1
fi

# Stop and remove containers
echo "Stopping and removing containers..."
docker compose down -v

# Remove Docker volumes
echo "Removing Docker volumes..."
docker volume rm selfdb_postgres_data selfdb_functions_data selfdb_selfdb_files || true

# Remove Docker images related to the project
echo "Removing Docker images related to the project..."
docker images | grep selfdb | awk '{print $3}' | xargs -r docker rmi -f

# Clean up dangling images (images with <none> tag)
echo "Cleaning up dangling images..."
docker image prune -f

# Clean up build cache
echo "Cleaning up Docker build cache..."
docker builder prune -f

echo "Cleanup complete. You can now run ./start.sh to start fresh."
