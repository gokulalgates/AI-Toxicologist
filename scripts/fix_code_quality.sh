#!/bin/bash
# Auto-fix code quality issues
# Runs ruff and isort with --fix to automatically fix issues

set -e

echo "🔧 Auto-fixing code quality issues..."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Run ruff with auto-fix
echo -e "${YELLOW}1. Running ruff with auto-fix...${NC}"
if command -v ruff &> /dev/null; then
    ruff check --fix . --exclude "_backup_*" --exclude "NEW_KC_LIVER" --exclude "__pycache__"
    echo -e "${GREEN}✅ Ruff fixes applied${NC}"
else
    echo "⚠️  Ruff not installed, skipping..."
fi
echo ""

# Run ruff format
echo -e "${YELLOW}2. Formatting code with ruff...${NC}"
if command -v ruff &> /dev/null; then
    ruff format . --exclude "_backup_*" --exclude "NEW_KC_LIVER" --exclude "__pycache__"
    echo -e "${GREEN}✅ Code formatted${NC}"
else
    echo "⚠️  Ruff not installed, skipping..."
fi
echo ""

# Run isort with auto-fix
echo -e "${YELLOW}3. Organizing imports with isort...${NC}"
if command -v isort &> /dev/null; then
    isort . --skip "_backup_*" --skip "NEW_KC_LIVER" --skip "__pycache__"
    echo -e "${GREEN}✅ Imports organized${NC}"
else
    echo "⚠️  isort not installed, skipping..."
fi
echo ""

echo -e "${GREEN}✅ Code quality fixes applied!${NC}"
echo "Run 'scripts/check_code_quality.sh' to verify all checks pass."
