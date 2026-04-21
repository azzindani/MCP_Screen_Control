#!/usr/bin/env bash
set -euo pipefail

echo "=== MCP Screen Control — Install ==="

# Check Python 3.12
if ! python3 --version 2>&1 | grep -q "3.12"; then
    echo "ERROR: Python 3.12 required. Found: $(python3 --version 2>&1)"
    exit 1
fi

# Install uv if missing
if ! command -v uv &>/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install Linux system deps
if [[ "$(uname)" == "Linux" ]]; then
    echo "Installing python3-tk and scrot..."
    sudo apt-get install -y python3-tk scrot 2>/dev/null || true
fi

# Sync dependencies
echo "Syncing Python dependencies..."
uv sync

# Write MCP config
echo "Writing MCP config..."
uv run python install/mcp_config_writer.py

echo ""
echo "Installation complete."
echo "Start the server: uv run python server.py"
