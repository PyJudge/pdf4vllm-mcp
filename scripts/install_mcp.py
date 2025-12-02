#!/usr/bin/env python3
"""
PDF MCP for vLLM MCP - Cross-platform Auto Installer for Claude Desktop
Usage: python scripts/install_mcp.py
"""

import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Colors for terminal
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

    @classmethod
    def disable(cls):
        """Disable colors for Windows without ANSI support"""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.NC = ''

# Disable colors on Windows if needed
if platform.system() == 'Windows' and not os.environ.get('TERM'):
    Colors.disable()

def get_config_path() -> Path:
    """Get Claude Desktop config path based on OS"""
    system = platform.system()

    if system == 'Darwin':  # macOS
        return Path.home() / 'Library' / 'Application Support' / 'Claude' / 'claude_desktop_config.json'
    elif system == 'Windows':
        return Path(os.environ.get('APPDATA', '')) / 'Claude' / 'claude_desktop_config.json'
    else:  # Linux
        return Path.home() / '.config' / 'Claude' / 'claude_desktop_config.json'

def find_python() -> str:
    """Find Python executable path"""
    # Use current Python
    python_path = sys.executable
    return str(Path(python_path).resolve())

def main():
    print(f"{Colors.BLUE}=== PDF MCP for vLLM Auto Installer ==={Colors.NC}")
    print(f"Platform: {platform.system()}")
    print()

    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    server_path = project_root / 'src' / 'server.py'

    if not server_path.exists():
        print(f"{Colors.RED}Error: server.py not found at {server_path}{Colors.NC}")
        sys.exit(1)

    # Find Python
    python_path = find_python()
    print(f"Python: {Colors.GREEN}{python_path}{Colors.NC}")
    print(f"Server: {Colors.GREEN}{server_path}{Colors.NC}")

    # Get config path
    config_path = get_config_path()
    config_dir = config_path.parent

    # Create config directory
    config_dir.mkdir(parents=True, exist_ok=True)

    # Build pdf4vllm config (no external dependencies needed!)
    pdf4vllm_config = {
        'command': python_path,
        'args': [str(server_path)]
    }

    # Load or create config
    if config_path.exists():
        print()
        print(f"{Colors.YELLOW}Existing config found. Backing up...{Colors.NC}")

        # Backup
        backup_name = f"{config_path.stem}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}{config_path.suffix}"
        backup_path = config_path.parent / backup_name
        shutil.copy(config_path, backup_path)

        # Load existing config
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        if 'pdf4vllm' in config.get('mcpServers', {}):
            print(f"{Colors.YELLOW}pdf4vllm already configured. Updating...{Colors.NC}")
    else:
        print()
        print(f"{Colors.YELLOW}Creating new config...{Colors.NC}")
        config = {}

    # Update config
    if 'mcpServers' not in config:
        config['mcpServers'] = {}

    config['mcpServers']['pdf4vllm'] = pdf4vllm_config

    # Save config
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print()
    print(f"{Colors.GREEN}=== Installation Complete ==={Colors.NC}")
    print()
    print(f"Config saved to: {config_path}")
    print()
    print(f"{Colors.YELLOW}Next steps:{Colors.NC}")
    print("1. Completely quit Claude Desktop")
    if platform.system() == 'Darwin':
        print("   (Cmd+Q)")
    elif platform.system() == 'Windows':
        print("   (Right-click tray icon → Quit)")
    print("2. Restart Claude Desktop")
    print("3. Try: \"list_pdfs in ~/Documents\"")
    print()
    print(f"{Colors.BLUE}Troubleshooting:{Colors.NC}")

    system = platform.system()
    if system == 'Darwin':
        print("Logs: ~/Library/Logs/Claude/mcp-server-pdf4vllm.log")
    elif system == 'Windows':
        print("Logs: %APPDATA%\\Claude\\logs\\mcp-server-pdf4vllm.log")
    else:
        print("Logs: ~/.config/Claude/logs/mcp-server-pdf4vllm.log")

    # Claude Code instructions
    print()
    print(f"{Colors.BLUE}For Claude Code (CLI):{Colors.NC}")
    print("Create .mcp.json in your project:")
    print(f'''{{
  "mcpServers": {{
    "pdf4vllm": {{
      "command": "{python_path}",
      "args": ["{server_path}"]
    }}
  }}
}}''')

if __name__ == '__main__':
    main()