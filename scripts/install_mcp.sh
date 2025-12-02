#!/bin/bash
# PDF MCP for vLLM - Auto Install Script for Claude Desktop
# Usage: ./scripts/install_mcp.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== PDF MCP for vLLM Auto Installer ===${NC}"
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVER_PATH="$PROJECT_ROOT/src/server.py"

# Find Python
PYTHON_PATH=$(which python3 2>/dev/null || which python 2>/dev/null)
if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

# Get absolute Python path
PYTHON_PATH=$(cd "$(dirname "$PYTHON_PATH")" && pwd)/$(basename "$PYTHON_PATH")

echo -e "Python: ${GREEN}$PYTHON_PATH${NC}"
echo -e "Server: ${GREEN}$SERVER_PATH${NC}"

# Claude Desktop config path
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

# Create config directory if needed
mkdir -p "$CONFIG_DIR"

# Check if config exists
if [ -f "$CONFIG_FILE" ]; then
    echo ""
    echo -e "${YELLOW}Existing config found. Backing up...${NC}"
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"

    # Check if pdf4vllm already exists
    if grep -q '"pdf4vllm"' "$CONFIG_FILE"; then
        echo -e "${YELLOW}pdf4vllm already configured. Updating...${NC}"
        # Use Python to update JSON properly
        python3 << EOF
import json
with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)

config['mcpServers']['pdf4vllm'] = {
    'command': '$PYTHON_PATH',
    'args': ['$SERVER_PATH']
}

with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
EOF
    else
        # Add pdf4vllm to existing config
        python3 << EOF
import json
with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['pdf4vllm'] = {
    'command': '$PYTHON_PATH',
    'args': ['$SERVER_PATH']
}

with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
EOF
    fi
else
    # Create new config
    echo ""
    echo -e "${YELLOW}Creating new config...${NC}"
    cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "pdf4vllm": {
      "command": "$PYTHON_PATH",
      "args": ["$SERVER_PATH"]
    }
  }
}
EOF
fi

echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo "Config saved to: $CONFIG_FILE"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Completely quit Claude Desktop (Cmd+Q)"
echo "2. Restart Claude Desktop"
echo "3. Try: \"list_pdfs in ~/Documents\""
echo ""
echo -e "${BLUE}Troubleshooting:${NC}"
echo "Logs: ~/Library/Logs/Claude/mcp-server-pdf4vllm.log"