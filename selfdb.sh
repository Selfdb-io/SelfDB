#!/bin/bash

# SelfDB Services Test Script
# This script helps test all services are working together across multiple environments

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SelfDB Services Integration Test${NC}"
echo -e "${BLUE}====================================${NC}"

# Function to check if env file exists
check_env_file() {
    local env=$1
    if [ ! -f ".env.${env}" ]; then
        echo -e "${RED}❌ .env.${env} file not found!${NC}"
        exit 1
    fi
}

# Function to display service URLs for an environment
display_urls() {
    local env=$1
    source .env.${env}
    echo -e "\n${GREEN}📌 $(echo $env | tr '[:lower:]' '[:upper:]') Service URLs:${NC}"
    echo -e "  Frontend:  http://localhost:${FRONTEND_PORT}"
    echo -e "  Backend:   http://localhost:${API_PORT}/health"
    echo -e "  Storage:   http://localhost:${STORAGE_PORT}/health"
    echo -e "  Functions: http://localhost:${DENO_PORT}/health"
    echo -e "  Database:  localhost:${POSTGRES_PORT}"
    echo -e "  PgBouncer: localhost:${PGBOUNCER_PORT}"
}

# Function to start a specific environment
start_env() {
    local env=$1
    echo -e "${BLUE}Starting ${env} environment...${NC}"
    check_env_file ${env}

    docker compose -f docker-compose.template.yml --env-file .env.${env} -p selfdb-${env} up -d --build
    echo -e "${GREEN}✅ ${env} environment started${NC}"
    display_urls ${env}
}

# Function to stop a specific environment
stop_env() {
    local env=$1
    echo -e "${BLUE}Stopping ${env} environment...${NC}"
    docker compose -f docker-compose.template.yml --env-file .env.${env} -p selfdb-${env} down
    echo -e "${GREEN}✅ ${env} environment stopped${NC}"
}

# Function to test health endpoints for an environment
test_env() {
    local env=$1
    source .env.${env}
    
    echo -e "\n${CYAN}Testing $(echo $env | tr '[:lower:]' '[:upper:]') environment...${NC}"
    echo -e "${CYAN}--------------------------------${NC}"
    local project="selfdb-${env}"
    local storage_container="${project}-storage-1"
    
    # Test Backend
    echo -n "Backend API: "
    if curl -s http://localhost:${API_PORT}/health | grep -q "ready"; then
        echo -e "${GREEN}✅ Ready${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
    fi
    
    # Test Storage
    echo -n "Storage Service: "
    storage_status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' "${storage_container}" 2>/dev/null || echo "missing")
    if [ "${storage_status}" = "healthy" ]; then
        echo -e "${GREEN}✅ Ready${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
    fi
    
    # Test Functions
    echo -n "Functions Runtime: "
    if curl -s http://localhost:${DENO_PORT}/health | grep -q "ok"; then
        echo -e "${GREEN}✅ Ready${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
    fi
    
    # Test Frontend
    echo -n "Frontend Proxy: "
    if curl -s http://localhost:${FRONTEND_PORT}/frontend/health | grep -q "ready"; then
        echo -e "${GREEN}✅ Ready${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
    fi
}

# Function to show logs for a specific environment
show_logs() {
    local env=$1
    docker compose -f docker-compose.template.yml --env-file .env.${env} -p selfdb-${env} logs -f
}

# Function to show status for a specific environment
show_status() {
    local env=$1
    docker compose -f docker-compose.template.yml --env-file .env.${env} -p selfdb-${env} ps
}

# Main script
case "$1" in
    up)
        # Start specific environment or all
        if [ -z "$2" ]; then
            echo -e "${YELLOW}Starting all environments...${NC}"
            start_env dev
            start_env staging
            start_env prod
            echo -e "\n${GREEN}✅ All environments started!${NC}"
            echo -e "${YELLOW}Access dashboards at:${NC}"
            echo -e "  Dev:        http://localhost:3000"
            echo -e "  Staging:    http://localhost:3001"
            echo -e "  Production: http://localhost:3002"
        else
            start_env $2
        fi
        ;;
    
    down)
        # Stop specific environment or all
        if [ -z "$2" ]; then
            echo -e "${YELLOW}Stopping all environments...${NC}"
            stop_env dev
            stop_env staging
            stop_env prod
            echo -e "${GREEN}✅ All environments stopped${NC}"
        else
            stop_env $2
        fi
        ;;
    
    restart)
        # Restart specific environment or all
        if [ -z "$2" ]; then
            $0 down
            $0 up
        else
            stop_env $2
            start_env $2
        fi
        ;;
    
    logs)
        # Show logs for specific environment
        if [ -z "$2" ]; then
            echo -e "${RED}Please specify environment: dev, staging, or prod${NC}"
            exit 1
        fi
        show_logs $2
        ;;
    
    ps)
        # Show status for specific environment or all
        if [ -z "$2" ]; then
            echo -e "${CYAN}=== DEV Environment ===${NC}"
            show_status dev
            echo -e "\n${CYAN}=== STAGING Environment ===${NC}"
            show_status staging
            echo -e "\n${CYAN}=== PRODUCTION Environment ===${NC}"
            show_status prod
        else
            show_status $2
        fi
        ;;
    
    test)
        # Test specific environment or all
        if [ -z "$2" ]; then
            echo -e "${BLUE}Testing all environments...${NC}"
            test_env dev
            test_env staging
            test_env prod
            echo -e "\n${GREEN}✅ All tests complete!${NC}"
        else
            test_env $2
        fi
        ;;
    
    quick)
        # Quick start dev environment for testing
        echo -e "${YELLOW}Quick start: Dev environment${NC}"
        start_env dev
        echo -e "\n${YELLOW}Waiting for services...${NC}"
        sleep 5
        test_env dev
        echo -e "\n${GREEN}✅ Dev environment ready at http://localhost:3000${NC}"
        ;;
    
    clean)
        # Clean all environments and volumes
        echo -e "${RED}⚠️  This will remove all containers and volumes!${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Cleaning all environments...${NC}"
            docker compose -f docker-compose.template.yml --env-file .env.dev -p selfdb-dev down -v
            docker compose -f docker-compose.template.yml --env-file .env.staging -p selfdb-staging down -v
            docker compose -f docker-compose.template.yml --env-file .env.prod -p selfdb-prod down -v
            echo -e "${GREEN}✅ All environments cleaned${NC}"
        fi
        ;;
    
    *)
        echo "Usage: $0 {up|down|restart|logs|ps|test|quick|clean} [environment]"
        echo ""
        echo "Commands:"
        echo "  up [env]      - Start all or specific environment (dev/staging/prod)"
        echo "  down [env]    - Stop all or specific environment"
        echo "  restart [env] - Restart all or specific environment"
        echo "  logs <env>    - Show logs for specific environment"
        echo "  ps [env]      - Show status of all or specific environment"
        echo "  test [env]    - Test health endpoints for all or specific environment"
        echo "  quick         - Quick start dev environment with health check"
        echo "  clean         - Remove all containers and volumes (WARNING: data loss)"
        echo ""
        echo "Environments: dev, staging, prod"
        echo ""
        echo "Examples:"
        echo "  $0 up            # Start all environments"
        echo "  $0 up dev        # Start only dev environment"
        echo "  $0 test staging  # Test staging environment"
        echo "  $0 down          # Stop all environments"
        echo "  $0 quick         # Quick start and test dev"
        exit 1
        ;;
esac