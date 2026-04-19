# MCP Screen Control

A fully local, self-hosted MCP server that gives a language model the ability to see and interact with the desktop — taking screenshots, locating UI elements via a locally-hosted VLM, and executing mouse/keyboard actions.

Zero cloud dependency. Runs on 8 GB VRAM with a 4B–9B quantized VLM in LM Studio.

## Requirements

- Python 3.12
- [uv](https://github.com/astral-sh/uv)
- [LM Studio](https://lmstudio.ai) running a vision-capable model on `localhost:1234`
- Linux: `python3-tk`, `scrot`
- macOS: `pyobjc` (installed automatically)

## Install

**Linux / macOS**
```bash
bash install/install.sh
```

**Windows**
```bat
install\install.bat
```

## Usage

Start the server:
```bash
uv run python server.py
```

Add to your MCP client config (written automatically by install script):

```json
{
  "mcpServers": {
    "screen-control": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/server.py"]
    }
  }
}
```

## Tools

| Tool | Type | Purpose |
|------|------|---------|
| `start_task` | Write | Decompose prompt → `objective.md` |
| `update_objective` | Write | Rewrite objective from new prompt |
| `read_objective` | Read | Return current `objective.md` state |
| `capture_screen` | Read | Screenshot → path + metadata |
| `find_element` | Read | VLM locates element → coords |
| `execute_action` | Write | Click / type / scroll / key |
| `verify_step` | Read | VLM confirms step success |
| `get_status` | Read | Status + progress percentage |

## The Execution Loop

```
start_task(prompt)
  → find_element(instruction)   # VLM locates element
  → execute_action(coords)      # click / type / scroll
  → verify_step(instruction)    # confirm success, advance step
  → repeat until COMPLETE or BLOCKED
```

## Development

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

## Architecture

See [CLAUDE.md](CLAUDE.md) for full architecture, module responsibilities, and the `objective.md` protocol.
