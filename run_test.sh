#!/bin/bash

# PDF MCP for vLLM Test Server Launcher
# Universal script for running the interactive testing interface

# Kill any existing uvicorn processes on port 8000
pkill -f "uvicorn.*8000" 2>/dev/null || true

# Wait a moment for port to be released
sleep 1

# Run the test server
python test_server.py