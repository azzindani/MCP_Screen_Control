"""Write mcp.json entry for this server into the user's MCP client config."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
PYTHON = subprocess.check_output(["uv", "run", "which", "python"], text=True).strip()

ENTRY = {
    "screen-control": {
        "command": PYTHON,
        "args": [str(REPO_ROOT / "server.py")],
        "env": {},
    }
}

# Claude Desktop config locations
_LOCATIONS = {
    "darwin": Path.home() / "Library/Application Support/Claude/claude_desktop_config.json",
    "win32": Path(os.environ.get("APPDATA", "")) / "Claude/claude_desktop_config.json",
    "linux": Path.home() / ".config/Claude/claude_desktop_config.json",
}

dest = _LOCATIONS.get(sys.platform, _LOCATIONS["linux"])
dest.parent.mkdir(parents=True, exist_ok=True)

config: dict = {}
if dest.exists():
    try:
        config = json.loads(dest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        pass

config.setdefault("mcpServers", {}).update(ENTRY)
dest.write_text(json.dumps(config, indent=2), encoding="utf-8")
print(f"MCP config written to: {dest}")
