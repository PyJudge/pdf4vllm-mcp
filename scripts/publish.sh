#!/bin/bash
# PDF MCP for vLLM MCP - Automated Publish Script
# Usage: ./scripts/publish.sh [patch|minor|major]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${GREEN}=== PDF MCP for vLLM MCP Publish Script ===${NC}"

# Get current version from __init__.py
CURRENT_VERSION=$(grep -o '__version__ = "[^"]*"' src/__init__.py | cut -d'"' -f2)
echo -e "Current version: ${YELLOW}$CURRENT_VERSION${NC}"

# Parse version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Determine bump type
BUMP_TYPE=${1:-patch}
case $BUMP_TYPE in
    patch)
        PATCH=$((PATCH + 1))
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    *)
        echo -e "${RED}Invalid bump type: $BUMP_TYPE${NC}"
        echo "Usage: $0 [patch|minor|major]"
        exit 1
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo -e "New version: ${GREEN}$NEW_VERSION${NC}"

# Confirm
read -p "Proceed with version $NEW_VERSION? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Update version in __init__.py
sed -i '' "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" src/__init__.py
echo -e "${GREEN}Updated src/__init__.py${NC}"

# Update version in pyproject.toml
sed -i '' "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
echo -e "${GREEN}Updated pyproject.toml${NC}"

# Git operations
echo -e "\n${YELLOW}Git operations...${NC}"
git add src/__init__.py pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo -e "${GREEN}Created git tag v$NEW_VERSION${NC}"

# Build package
echo -e "\n${YELLOW}Building package...${NC}"
rm -rf dist/ build/ *.egg-info
python -m build

# Upload to PyPI
echo -e "\n${YELLOW}Uploading to PyPI...${NC}"
python -m twine upload dist/*

# Push to GitHub
echo -e "\n${YELLOW}Pushing to GitHub...${NC}"
git push origin master
git push origin "v$NEW_VERSION"

# MCP Registry publish (if mcp-publisher is installed)
if command -v mcp-publisher &> /dev/null; then
    echo -e "\n${YELLOW}Publishing to MCP Registry...${NC}"
    mcp-publisher publish
else
    echo -e "\n${YELLOW}Note: mcp-publisher not found. Install with:${NC}"
    echo "  brew install mcp-publisher"
    echo "Then run: mcp-publisher publish"
fi

echo -e "\n${GREEN}=== Successfully published v$NEW_VERSION ===${NC}"
echo ""
echo "Checklist:"
echo "  [x] Version updated in __init__.py and pyproject.toml"
echo "  [x] Git commit and tag created"
echo "  [x] Package built and uploaded to PyPI"
echo "  [x] Pushed to GitHub with tag"
echo ""
echo "Next steps:"
echo "  - Verify on PyPI: https://pypi.org/project/pdf4vllm-mcp/"
echo "  - Verify on GitHub: https://github.com/PyJudge/PDFmcp/releases"
echo "  - Verify on MCP Registry (after sync)"
