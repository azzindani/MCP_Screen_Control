# CLAUDE.md — MCP Screen Control Server

> Standards reference: [STANDARDS.md v5.1](https://github.com/azzindani/Standards/blob/main/local_mcp/STANDARDS.md)
> This project's CLAUDE.md takes precedence over STANDARDS.md where they conflict.

---

## Project Overview

**MCP Screen Control** is a fully local, self-hosted MCP server that gives a language
model the ability to see and interact with the desktop screen — taking screenshots,
locating UI elements via a locally-hosted vision-language model (VLM), and executing
mouse/keyboard actions. It is the local-first equivalent of Anthropic's computer-use
demo and OpenAI's Operator, with zero cloud dependency.

The server is designed to work with **small VLMs (2B–9B parameters)** running in
LM Studio. It compensates for their limited goal-persistence by externalizing all
state to a file-based protocol (`tmp/objective.md`), so the model only ever needs
to answer one micro-question per tool call.

**Key constraints:**
- All execution is local. No screenshot, pixel data, or instruction leaves the machine.
- LM Studio is the only inference backend (OpenAI-compatible API at `localhost:1234`).
- Target hardware: 8 GB VRAM, running a 4B–9B quantized VLM.
- No cloud APIs. No OAuth. No subscriptions.

---

## Goals

1. Enable natural-language desktop automation using small local VLMs.
2. Compensate for small-model context/goal limitations via the objective.md protocol.
3. Keep the tool count minimal so the VLM can reliably select the right tool.
4. Be debuggable — every step logged, every action reversible or inspectable.
5. Follow STANDARDS.md v5.1 in full: surgical reads, snapshot-before-write, CPU-only
   tool execution, self-hosted execution principle.

---

## Repository Structure

```
mcp-screen-control/
│
├── server.py                    # FastMCP wrapper — thin, one-liner tools only
├── engine.py                    # Pure domain logic, zero MCP imports
│
├── _sc_helpers.py               # Shared imports, constants, utility functions
├── _sc_capture.py               # Screenshot capture and image preprocessing
├── _sc_vision.py                # LM Studio VLM calls for coordinate extraction
├── _sc_actions.py               # pyautogui mouse/keyboard execution
├── _sc_objective.py             # objective.md protocol: read, write, validate
├── _sc_verify.py                # Post-action verification loop
│
├── shared/
│   ├── __init__.py
│   ├── version_control.py       # snapshot / restore
│   ├── file_utils.py            # resolve_path, atomic writes
│   ├── platform_utils.py        # is_constrained_mode, get_max_* helpers
│   ├── progress.py              # ok / fail / info / warn / undo helpers
│   └── receipt.py               # operation receipt log
│
├── tests/
│   ├── fixtures/                # static screenshots for deterministic tests
│   └── test_engine.py
│
├── install/
│   ├── install.sh
│   ├── install.bat
│   └── mcp_config_writer.py
│
├── tmp/                         # runtime only — gitignored
│   ├── objective.md             # current session objective and step state
│   ├── screen_current.png       # latest screenshot
│   └── screen_prev.png          # pre-action screenshot for diff/verify
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
│
├── pyproject.toml
├── uv.lock
├── .python-version              # 3.12
├── .gitignore                   # must include tmp/
├── CLAUDE.md                    # this file
├── STANDARDS.md                 # linked reference
└── README.md
```

---

## Architecture Principles

### 1. Engine / Server Split (STANDARDS §14)

`server.py` contains only `@mcp.tool()` decorators. Every tool body is a single
`return engine.func(params)` call. Zero domain logic in `server.py`.

`engine.py` is the thin router importing from `_sc_*.py` sub-modules. Zero MCP
imports in `engine.py` or any `_sc_*.py` file.

### 2. CPU-Only Tool Execution (STANDARDS §21)

All MCP tools run on CPU. The GPU is used exclusively by LM Studio for VLM
inference. Tools never call `torch.cuda.is_available()`. All libraries
(`mss`, `Pillow`, `pyautogui`) use CPU-only builds.

### 3. Self-Hosted Execution Principle (STANDARDS §4)

Every tool must complete its primary operation with the machine disconnected from the
internet. LM Studio runs locally. No external APIs. Permitted network: one-time
`pip install` / `uv sync` on first run.

### 4. Surgical Read Protocol (STANDARDS §10)

Tools never return raw pixel arrays, full screenshots as bytes, or large data blobs.
Screenshots are written to `tmp/` and the path is returned. The VLM receives a
base64-encoded, pre-resized image (max 800px wide) injected by the engine — never
returned through the MCP channel.

### 5. Snapshot Before Write (STANDARDS §19)

Any tool that modifies system state (mouse click, keyboard input, file write) calls
`snapshot()` on the current `tmp/objective.md` before modifying it. Screenshots are
preserved as `tmp/screen_prev.png` before each new capture.

### 6. Token Budget Discipline (STANDARDS §20)

Tool schemas: ≤ 80-char docstrings. Response payloads: under 300 tokens. Never
return image data through the MCP channel. All responses include `token_estimate`.

---

---

## The Objective.md Protocol

This is the core innovation of this project. It replaces system-prompt-based goal
tracking with a persistent, file-based protocol that every tool reads and writes.
Small VLMs cannot hold multi-step goals in context — `objective.md` externalizes
that memory to disk.

### File Location

```
tmp/objective.md
```

`tmp/` is created at runtime and is gitignored. It persists across tool calls within
a session. The user may edit `objective.md` directly at any time to change or
clarify the objective.

### objective.md Schema

```markdown
# Objective
{The final goal, as decomposed from the user's original prompt}

# Steps
- [ ] {step 1 — atomic, actionable, single UI interaction}
- [ ] {step 2}
- [x] {step 3 — completed}
- [ ] {step 4}

# Current Step
{Exact text of the next uncompleted step}

# Platform
{browser | desktop | terminal | unknown}

# Status
{RUNNING | BLOCKED | NEEDS_CLARIFICATION | COMPLETE}

# Last Action
{What was done in the last tool call and whether it succeeded}

# Clarification Needed
{Optional — populated when Status = NEEDS_CLARIFICATION}
```

### Protocol Rules

1. **Every tool call validates workspace first.** If `tmp/` or `objective.md` does
   not exist, the tool creates both and calls `decompose_objective` before proceeding.
2. **Every tool reads `objective.md` before acting.** It uses `Current Step` to
   know what to do — never relies on the LLM's memory of the conversation.
3. **Every tool writes back to `objective.md` after acting.** It marks the step
   done, advances `Current Step`, updates `Last Action`, and updates `Status`.
4. **The user may edit `objective.md` at any time.** On next tool call, the updated
   objective is picked up automatically.
5. **When `Status = COMPLETE`, tools return without acting** and surface the result.
6. **When `Status = NEEDS_CLARIFICATION`, tools pause** and surface the question in
   `Clarification Needed` until the user responds.

### Objective Mutation

When the user changes the goal mid-session, they either:
- Edit `tmp/objective.md` directly, or
- Call `update_objective(new_prompt)` which re-decomposes and rewrites the file.

The execution loop resumes from the new `Current Step` on the next tool call.

---

## Tool Design

### Tier: Basic (single-tier server)

Target: 8 GB VRAM, 4B–9B quantized VLM. Tool count hard limit: **8 tools**.

### Tool List

| # | Tool | Type | Purpose |
|---|------|------|---------|
| 1 | `start_task` | Write | Validate workspace, decompose prompt → objective.md |
| 2 | `update_objective` | Write | Rewrite objective.md from new user prompt |
| 3 | `read_objective` | Read | Return current objective.md state |
| 4 | `capture_screen` | Read | Take screenshot, preprocess, return path + metadata |
| 5 | `find_element` | Read | Ask VLM to locate element, return coords |
| 6 | `execute_action` | Write | Click, type, scroll, or key at given coords |
| 7 | `verify_step` | Read | Take new screenshot, ask VLM if step succeeded |
| 8 | `get_status` | Read | Return current Status and progress from objective.md |

**Total: 8 tools. Do not add more without removing one.**

### The Execution Loop (Four-Tool Pattern — STANDARDS §9)

```
LOCATE   → find_element(instruction)        # VLM locates element, returns coords
PATCH    → execute_action(coords, action)   # click/type at located coords
VERIFY   → verify_step()                    # confirm step succeeded, advance step
REPEAT   → loop until Status = COMPLETE or BLOCKED
```

---

## Sub-Module Responsibilities

### `_sc_helpers.py`
Shared imports, constants, `__all__`. Key constants:
- `LMSTUDIO_BASE_URL = "http://localhost:1234/v1"`
- `TMP_DIR`, `OBJECTIVE_PATH`, `SCREEN_CURRENT`, `SCREEN_PREV`
- `MAX_IMAGE_WIDTH = 800` — resize before VLM call
- `CONFIDENCE_THRESHOLD = 0.6`
- `MAX_RETRIES = 3`

### `_sc_capture.py`
- `capture_screen() -> dict` — mss grab → saves `tmp/screen_current.png` → returns path + dimensions
- `preprocess_image(path, max_width) -> str` — Pillow resize → base64 PNG string
- `save_prev_screen()` — copy current → `tmp/screen_prev.png`
- Never returns raw pixel arrays. Always saves to disk, returns path.

### `_sc_vision.py`
- `find_element(instruction, image_b64, screen_w, screen_h, objective, current_step) -> dict`
  - Calls LM Studio `/v1/chat/completions` with image + objective-injected prompt
  - Forces JSON: `{"x": int, "y": int, "confidence": float, "description": str}`
  - On `confidence < CONFIDENCE_THRESHOLD`: retry with cropped region
  - On second failure: returns error dict with `NEEDS_CLARIFICATION` hint
- `verify_element(instruction, image_b64, objective, current_step) -> dict`
  - Binary VLM call: did step succeed? Returns `{"success": bool, "reason": str}`
- `decompose_prompt(user_prompt) -> dict`
  - Text-only LM Studio call: decompose → structured objective.md content
  - Forces JSON matching objective.md schema fields

### `_sc_actions.py`
- `click(x, y) -> dict`
- `double_click(x, y) -> dict`
- `right_click(x, y) -> dict`
- `type_text(text) -> dict`
- `press_key(key) -> dict`
- `scroll(x, y, clicks) -> dict`
- All actions: snapshot `objective.md` before → append receipt after

### `_sc_objective.py`
- `validate_workspace() -> bool`
- `create_workspace()`
- `read_objective() -> dict`
- `write_objective(data: dict)` — atomic write
- `advance_step()` — mark `[x]`, advance `Current Step`
- `set_status(status: str)`
- `set_last_action(description: str)`
- `set_clarification(question: str)` — sets `Status = NEEDS_CLARIFICATION`

### `_sc_verify.py`
- `verify_step(instruction) -> dict`
  - Capture new screenshot
  - Call `verify_element` (binary success question)
  - Success → `advance_step()`
  - Failure → increment retry counter
  - 3 consecutive failures → `set_status("BLOCKED")`

---

## LM Studio Integration

### Vision Call Pattern

Every VLM call injects the full objective context, so the model only answers
one micro-question per call:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {
                "type": "text",
                "text": (
                    f"FINAL OBJECTIVE: {objective}\n"
                    f"CURRENT STEP: {current_step}\n"
                    f"TASK: Locate the UI element needed for CURRENT STEP.\n"
                    f"Screen size: {screen_w}x{screen_h} pixels.\n"
                    f"Return only JSON: "
                    f'{{\"x\": int, \"y\": int, \"confidence\": float, \"description\": str}}'
                )
            }
        ]
    }
]
```

API params: `max_tokens=150`, `temperature=0.1`, `response_format={{"type":"json_object"}}`.

### Image Preprocessing Rules

1. Resize to max 800px wide (preserve aspect ratio)
2. Convert to PNG
3. Base64-encode
4. Never send raw 1080p/4K — too many tokens, worse accuracy on small models
5. On low confidence: crop to relevant quadrant, retry at higher effective resolution

### Confidence Retry Strategy

- `confidence >= 0.6` → proceed
- `confidence < 0.6` → crop to most likely quadrant, retry once
- Second failure → `set_clarification("Cannot locate element. Please describe it more precisely or bring it into view.")`

---

## What the AI Must Never Do

1. **Print to stdout** in any engine or sub-module file. Stdout is the MCP channel.
2. **Return raw image bytes or pixel arrays** through MCP. Always return paths.
3. **Return a plain string, list, None, or bool** from a tool. Always a dict.
4. **Skip `validate_workspace()`** at the start of any tool call.
5. **Skip `read_objective()`** before executing any action — the model's memory is
   unreliable; always read from file.
6. **Skip `snapshot()`** before any write to `objective.md` or system state change.
7. **Add more than 8 tools** without explicit approval and removing an existing tool.
8. **Put domain logic in `server.py`**. Tool bodies are one-liners.
9. **Call `eval()` or `exec()`** on any user-provided input.
10. **Use `shell=True`** in any subprocess call.
11. **Send the full unresized screenshot** to the VLM. Always preprocess first.
12. **Rely on the LLM's context memory** for the objective or current step. Always
    read from `objective.md`.
13. **Hardcode size or limit constants**. Always use `get_max_*()` from `platform_utils.py`.
14. **Require a GPU** for any tool operation. CPU-only tools. GPU = LM Studio only.
15. **Attempt to click** when `confidence < CONFIDENCE_THRESHOLD` without retrying.
16. **Silently swallow exceptions**. All exceptions → error dict with `"hint"`.
17. **Use cloud APIs** as fallback or primary execution. Self-hosted only.
18. **Write generated files into the repo directory or system temp**. Write to `tmp/`.

---

## Testing Standards (STANDARDS §27)

Tests import `engine.py` directly. No MCP server process spun up.

### Fixtures

`tests/fixtures/` must contain:
- `simple_ui.png` — clean, sparse desktop screenshot
- `dense_ui.png` — busy screenshot with many small elements
- `browser_ui.png` — browser with web page loaded
- `objective_simple.md` — completed objective.md for a simple task
- `objective_partial.md` — objective.md with steps partially done

### Required Tests Per Tool

For every write tool:
1. Success — returns `{"success": True}`
2. Workspace missing → auto-created
3. Snapshot created in `.mcp_versions/`
4. `"backup"` key in response
5. `"progress"` array in response
6. `"token_estimate"` in response

For `find_element`:
1. High-confidence element found → valid x, y returned
2. Low-confidence first attempt → retry with crop
3. Second failure → `NEEDS_CLARIFICATION` status set

For `verify_step`:
1. Success → step marked `[x]`, next step set
2. Failure × 3 → `Status = BLOCKED`

For `update_objective`:
1. New objective replaces old — `Current Step` resets to step 1
2. Old steps discarded
3. `"backup"` of previous objective.md in response

---

## Progress Tracker

### Phase 1 — Foundation

- [x] Repository scaffolded with correct structure
- [x] `shared/` modules implemented (version_control, file_utils, platform_utils, progress, receipt)
- [x] `_sc_helpers.py` — constants and shared imports
- [x] `_sc_objective.py` — objective.md read/write/validate/advance
- [x] `_sc_capture.py` — mss screenshot + Pillow preprocess
- [x] `_sc_vision.py` — LM Studio vision + decompose calls
- [x] `_sc_actions.py` — pyautogui click/type/scroll/key
- [x] `_sc_verify.py` — post-action verification loop
- [x] `engine.py` — thin router importing from sub-modules
- [x] `server.py` — 8 tools, all one-liners

### Phase 2 — Testing

- [x] `tests/fixtures/` — 5 fixture files
- [x] `tests/test_engine.py` — all tools tested per §27 requirements
- [x] `uv run pytest` — all pass (22 tests)
- [x] `uv run ruff check .` — no errors
- [x] `uv run ruff format --check .` — clean
- [x] Tool docstring length — all ≤ 80 chars verified

### Phase 3 — Distribution

- [x] `install/install.sh` and `install.bat`
- [x] `install/mcp_config_writer.py`
- [x] mcp.json entries (Windows + macOS/Linux) in README
- [x] `.github/workflows/ci.yml` — 3-platform matrix
- [x] `.github/workflows/release.yml`
- [ ] Manual test in LM Studio with Qwen3.5-4B or Gemma 4 E4B
- [ ] 5-step task test — full loop works end to end

### Phase 4 — Hardening

- [ ] Confidence retry logic tested on real dense UI screenshots
- [x] `BLOCKED` state surfaces helpful message to user
- [x] `NEEDS_CLARIFICATION` state pauses loop and asks user
- [x] Objective mutation tested (mid-task goal change)
- [x] README follows STANDARDS §37 section order

---

## Dependencies

```toml
[project]
requires-python = "==3.12.*"
dependencies = [
    "fastmcp>=2.0,<3.0",
    "mss>=9.0",
    "Pillow>=10.0",
    "pyautogui>=0.9.54",
    "httpx>=0.27",
    "psutil>=5.9",
]

[dependency-groups]
dev = [
    "pytest>=9.0",
    "ruff>=0.9",
    "pyright>=1.1",
]
```

All dependencies are MIT or Apache 2.0 licensed. No cloud SDKs. No GPU requirements.
`pyautogui` requires `python3-tk` on Linux and `pyobjc` on macOS — documented in README.

---

*CLAUDE.md version: 1.0*
*Project: MCP Screen Control*
*Standards: STANDARDS.md v5.1*
*Last updated: 2026-04-15*
