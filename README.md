# MCP Screen Control

Local MCP server that gives a language model the ability to see and interact with the desktop using a locally-hosted vision model — no cloud, no subscriptions.

## Features

- Take screenshots and locate UI elements by natural language description
- Execute mouse clicks, keyboard input, and scroll actions
- Persist multi-step goals across tool calls via `objective.md` protocol
- Compensates for small-model context limits — goal state is on disk, not in context
- Works with 4B–9B quantized vision models in LM Studio (8 GB VRAM)
- All execution is local — no pixel data or instructions leave the machine

## Quick Install (LM Studio)

1. Install [LM Studio](https://lmstudio.ai) and load a vision-capable model (e.g. Qwen2.5-VL-7B-Instruct or Gemma-3-4B-IT)
2. Start the local server in LM Studio on port `1234`
3. Run the install script (see Install below)
4. Add the MCP config entry to your client (see Configuration below)

> **LM Studio timeout note:** On first load, the model may take 30–60 seconds to initialise. If a tool call times out, click **Restart** in the LM Studio server panel and retry.

## Requirements

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — fast Python package manager
- [LM Studio](https://lmstudio.ai) running a vision-capable model on `localhost:1234`
- Linux: `python3-tk`, `scrot`, `python3-xlib`
- macOS: `pyobjc` (installed automatically by pyautogui)
- Windows: no additional system deps required

## Platform Support

| Platform | Status |
|----------|--------|
| Windows 11 | Tested |
| macOS | CI only |
| Linux | CI only |

## First Run

**Before running the server**, install dependencies:

**Windows (PowerShell):**
```powershell
irm https://docs.astral.sh/uv/getting-started/installation/ | iex
cd MCP_Screen_Control
uv sync
```

**Linux / macOS (bash):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
cd MCP_Screen_Control
bash install/install.sh
```

> Running `uv sync` before first use avoids a timeout on the first tool call while packages download.

## Steps

1. Clone the repository
2. Run the install script for your platform (above)
3. Start LM Studio and load a vision model on port `1234`
4. Add the MCP config entry (see Configuration)
5. Start a session and call `start_task("your goal here")`

## Available Tools

| # | Tool | Type | Purpose |
|---|------|------|---------|
| 1 | `start_task` | Write | Decompose prompt → `objective.md` |
| 2 | `update_objective` | Write | Rewrite objective mid-task from new prompt |
| 3 | `read_objective` | Read | Return current `objective.md` state |
| 4 | `capture_screen` | Read | Screenshot → path + dimensions |
| 5 | `find_element` | Read | VLM locates element → x, y, confidence |
| 6 | `execute_action` | Write | Click / double-click / type / key / scroll |
| 7 | `verify_step` | Read | VLM confirms step success, advances state |
| 8 | `get_status` | Read | Status + progress percentage |

**Execution loop:**
```
start_task(prompt)
  → find_element(instruction)   # VLM locates the element
  → execute_action(coords)      # click / type / scroll
  → verify_step(instruction)    # confirm success, advance step
  → repeat until Status = COMPLETE or BLOCKED
```

## Configuration

The install script writes the MCP config automatically. To add it manually:

**Linux / macOS** (`~/.config/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "screen-control": {
      "command": "/path/to/MCP_Screen_Control/.venv/bin/python",
      "args": ["/path/to/MCP_Screen_Control/server.py"]
    }
  }
}
```

**Windows** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "screen-control": {
      "command": "C:\\path\\to\\MCP_Screen_Control\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\MCP_Screen_Control\\server.py"]
    }
  }
}
```

## Uninstall

```bash
# Remove the virtual environment and runtime files
rm -rf .venv tmp/ .mcp_versions/

# Remove the MCP config entry from your client's config file
```

## Architecture

The server is split into two layers:

- **`server.py`** — FastMCP wrapper, one-liner tool bodies only
- **`engine.py`** — thin router, imports from `_sc_*.py` sub-modules
- **`_sc_*.py`** — domain modules: capture, vision, actions, objective, verify
- **`shared/`** — version control, atomic writes, platform utils, receipts

The `objective.md` protocol externalises goal state to disk so small VLMs (which cannot hold multi-step goals in context) only need to answer one micro-question per tool call.

See [CLAUDE.md](CLAUDE.md) for full architecture details and module responsibilities.

## Development

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

## License

MIT
