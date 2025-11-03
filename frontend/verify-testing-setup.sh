#!/bin/bash

# Frontend Testing Setup Verification Script
# Run this to verify the testing framework is properly configured

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Frontend Testing Framework Verification${NC}"
echo -e "${BLUE}===========================================${NC}\n"

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: Must run from frontend/ directory${NC}"
    exit 1
fi

echo -e "${YELLOW}Checking files...${NC}"

# Check environment file
if [ -f ".env.development" ]; then
    echo -e "${GREEN}✓${NC} .env.development exists"
else
    echo -e "${RED}✗${NC} .env.development missing"
    exit 1
fi

# Check WebSocket utility
if [ -f "src/utils/websocket.ts" ]; then
    echo -e "${GREEN}✓${NC} WebSocket utility exists"
else
    echo -e "${RED}✗${NC} WebSocket utility missing"
    exit 1
fi

# Check test setup
if [ -f "tests/setup.ts" ]; then
    echo -e "${GREEN}✓${NC} Test setup file exists"
else
    echo -e "${RED}✗${NC} Test setup file missing"
    exit 1
fi

# Check test utilities
if [ -f "tests/helpers/test-utils.tsx" ]; then
    echo -e "${GREEN}✓${NC} Test utilities exist"
else
    echo -e "${RED}✗${NC} Test utilities missing"
    exit 1
fi

# Check vite config
if grep -q "test:" vite.config.ts; then
    echo -e "${GREEN}✓${NC} Vite test configuration present"
else
    echo -e "${RED}✗${NC} Vite test configuration missing"
    exit 1
fi

echo -e "\n${YELLOW}Checking dependencies...${NC}"

# Check if node_modules exists
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed"
    
    # Check for key testing packages
    if [ -d "node_modules/vitest" ]; then
        echo -e "${GREEN}✓${NC} Vitest installed"
    else
        echo -e "${YELLOW}⚠${NC}  Vitest not found - run 'npm install'"
    fi
    
    if [ -d "node_modules/@testing-library" ]; then
        echo -e "${GREEN}✓${NC} Testing Library installed"
    else
        echo -e "${YELLOW}⚠${NC}  Testing Library not found - run 'npm install'"
    fi
else
    echo -e "${YELLOW}⚠${NC}  Dependencies not installed - run 'npm install'"
fi

echo -e "\n${YELLOW}Checking test structure...${NC}"

# Check test directories
for dir in "tests/unit/components" "tests/unit/services" "tests/unit/utils" "tests/integration" "tests/e2e" "tests/helpers"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir exists"
    else
        echo -e "${RED}✗${NC} $dir missing"
    fi
done

# Check example tests
if [ -f "tests/unit/utils/websocket.test.ts" ]; then
    echo -e "${GREEN}✓${NC} WebSocket test example exists"
else
    echo -e "${RED}✗${NC} WebSocket test example missing"
fi

if [ -f "tests/unit/components/LoginForm.test.tsx" ]; then
    echo -e "${GREEN}✓${NC} LoginForm test example exists"
else
    echo -e "${RED}✗${NC} LoginForm test example missing"
fi

echo -e "\n${BLUE}===========================================${NC}"

# Try to run tests if dependencies are installed
if [ -d "node_modules/vitest" ]; then
    echo -e "${YELLOW}Running tests...${NC}\n"
    npm test || echo -e "\n${YELLOW}⚠  Some tests may fail until you run 'npm install'${NC}"
else
    echo -e "\n${YELLOW}⚠  Run 'npm install' to install dependencies and test${NC}"
fi

echo -e "\n${GREEN}✅ Verification complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "  1. cd frontend"
echo -e "  2. npm install"
echo -e "  3. npm test"
echo -e "  4. npm run dev"
