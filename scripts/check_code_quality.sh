#!/bin/bash
# Code quality checking script
# Run all code quality tools: ruff, mypy, isort

set -e

echo "🔍 Running code quality checks..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if tools are installed
check_tool() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        echo "   Install with: pip install -r requirements-dev.txt"
        return 1
    fi
    return 0
}

# Run ruff linting
echo -e "${YELLOW}1. Running ruff linter...${NC}"
if check_tool ruff; then
    ruff check . --exclude "_backup_*" --exclude "NEW_KC_LIVER" --exclude "__pycache__" || {
        echo -e "${RED}❌ Ruff found issues${NC}"
        echo "   Fix with: ruff check --fix ."
        exit 1
    }
    echo -e "${GREEN}✅ Ruff checks passed${NC}"
fi
echo ""

# Run ruff formatting check
echo -e "${YELLOW}2. Checking code formatting...${NC}"
if check_tool ruff; then
    ruff format --check . --exclude "_backup_*" --exclude "NEW_KC_LIVER" --exclude "__pycache__" || {
        echo -e "${RED}❌ Code formatting issues found${NC}"
        echo "   Fix with: ruff format ."
        exit 1
    }
    echo -e "${GREEN}✅ Code formatting is correct${NC}"
fi
echo ""

# Run mypy type checking
echo -e "${YELLOW}3. Running mypy type checker...${NC}"
if check_tool mypy; then
    mypy . --exclude "_backup_|NEW_KC_LIVER|scripts" --ignore-missing-imports || {
        echo -e "${YELLOW}⚠️  Mypy found type issues (non-blocking)${NC}"
        echo "   Review type hints and fix as needed"
    }
    echo -e "${GREEN}✅ Mypy checks completed${NC}"
fi
echo ""

# Run isort check (optional, ruff can handle this too)
echo -e "${YELLOW}4. Checking import organization...${NC}"
if check_tool isort; then
    isort . --check-only --skip "_backup_*" --skip "NEW_KC_LIVER" --skip "__pycache__" || {
        echo -e "${RED}❌ Import organization issues found${NC}"
        echo "   Fix with: isort ."
        exit 1
    }
    echo -e "${GREEN}✅ Import organization is correct${NC}"
fi
echo ""

echo -e "${GREEN}✅ All code quality checks passed!${NC}"
