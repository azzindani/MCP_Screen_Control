"""objective.md protocol: read, write, validate, advance."""
import re
from pathlib import Path

from _sc_helpers import OBJECTIVE_PATH, TMP_DIR
from shared.file_utils import atomic_write
from shared.version_control import snapshot

_TEMPLATE = """\
# Objective
{objective}

# Steps
{steps}

# Current Step
{current_step}

# Platform
{platform}

# Status
{status}

# Last Action
{last_action}

# Clarification Needed
{clarification}
"""

_DEFAULT_DATA = {
    "objective": "(not set)",
    "steps": "- [ ] (no steps)",
    "current_step": "(none)",
    "platform": "unknown",
    "status": "RUNNING",
    "last_action": "(none)",
    "clarification": "",
}


def validate_workspace() -> bool:
    """Return True if tmp/ and objective.md exist and are well-formed."""
    return TMP_DIR.exists() and OBJECTIVE_PATH.exists() and OBJECTIVE_PATH.stat().st_size > 0


def create_workspace() -> None:
    """Create tmp/ and a blank objective.md."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    if not OBJECTIVE_PATH.exists():
        write_objective(_DEFAULT_DATA)


def read_objective() -> dict:
    """Parse objective.md into a dict. Returns defaults if missing."""
    if not OBJECTIVE_PATH.exists():
        return dict(_DEFAULT_DATA)
    text = OBJECTIVE_PATH.read_text(encoding="utf-8")
    return _parse(text)


def write_objective(data: dict) -> None:
    """Atomically write objective.md from a dict."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    content = _TEMPLATE.format(
        objective=data.get("objective", _DEFAULT_DATA["objective"]),
        steps=data.get("steps", _DEFAULT_DATA["steps"]),
        current_step=data.get("current_step", _DEFAULT_DATA["current_step"]),
        platform=data.get("platform", _DEFAULT_DATA["platform"]),
        status=data.get("status", _DEFAULT_DATA["status"]),
        last_action=data.get("last_action", _DEFAULT_DATA["last_action"]),
        clarification=data.get("clarification", _DEFAULT_DATA["clarification"]),
    )
    atomic_write(OBJECTIVE_PATH, content)


def advance_step() -> None:
    """Mark current step [x], advance Current Step to next uncompleted step."""
    data = read_objective()
    steps_text = data.get("steps", "")
    current = data.get("current_step", "")

    lines = steps_text.splitlines()
    marked = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not marked and stripped.startswith("- [ ]"):
            step_text = stripped[5:].strip()
            if step_text == current or not current or current == "(none)":
                lines[i] = line.replace("- [ ]", "- [x]", 1)
                marked = True
                break

    new_steps = "\n".join(lines)
    next_step = "(none)"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            next_step = stripped[5:].strip()
            break

    if next_step == "(none)":
        data["status"] = "COMPLETE"

    data["steps"] = new_steps
    data["current_step"] = next_step
    write_objective(data)


def set_status(status: str) -> None:
    """Set the Status field in objective.md."""
    bak = snapshot(OBJECTIVE_PATH)
    data = read_objective()
    data["status"] = status
    write_objective(data)


def set_last_action(description: str) -> None:
    """Update the Last Action field in objective.md."""
    data = read_objective()
    data["last_action"] = description
    write_objective(data)


def set_clarification(question: str) -> None:
    """Populate Clarification Needed and set Status = NEEDS_CLARIFICATION."""
    bak = snapshot(OBJECTIVE_PATH)
    data = read_objective()
    data["clarification"] = question
    data["status"] = "NEEDS_CLARIFICATION"
    write_objective(data)


# ---------------------------------------------------------------------------
# Internal parser
# ---------------------------------------------------------------------------

def _parse(text: str) -> dict:
    sections = {
        "objective": "(not set)",
        "steps": "- [ ] (no steps)",
        "current_step": "(none)",
        "platform": "unknown",
        "status": "RUNNING",
        "last_action": "(none)",
        "clarification": "",
    }
    _extract(text, "Objective", "Steps", sections, "objective")
    _extract(text, "Steps", "Current Step", sections, "steps")
    _extract(text, "Current Step", "Platform", sections, "current_step")
    _extract(text, "Platform", "Status", sections, "platform")
    _extract(text, "Status", "Last Action", sections, "status")
    _extract(text, "Last Action", "Clarification Needed", sections, "last_action")
    _extract(text, "Clarification Needed", None, sections, "clarification")

    for key in ("objective", "current_step", "platform", "status", "last_action", "clarification"):
        sections[key] = sections[key].strip()

    return sections


def _extract(text: str, start_header: str, end_header: str | None, out: dict, key: str) -> None:
    pattern = rf"#\s+{re.escape(start_header)}\s*\n(.*?)"
    if end_header:
        pattern += rf"(?=#\s+{re.escape(end_header)})"
    else:
        pattern += r"$"
    m = re.search(pattern, text, re.DOTALL)
    if m:
        out[key] = m.group(1)
