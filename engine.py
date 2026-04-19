"""Thin router — imports from _sc_* sub-modules. Zero MCP imports."""
from _sc_capture import capture_screen as _capture_screen
from _sc_objective import (
    create_workspace,
    read_objective as _read_objective,
    set_last_action,
    validate_workspace,
    write_objective,
)
from _sc_actions import click, double_click, press_key, right_click, scroll, type_text
from _sc_verify import verify_step as _verify_step
from _sc_vision import decompose_prompt, find_element as _find_element
from shared.version_control import snapshot
from _sc_helpers import OBJECTIVE_PATH


def start_task(prompt: str) -> dict:
    """Validate workspace, decompose prompt, write objective.md."""
    if not validate_workspace():
        create_workspace()

    bak = snapshot(OBJECTIVE_PATH)
    data = decompose_prompt(prompt)
    write_objective(data)
    return {
        "success": True,
        "objective": data["objective"],
        "steps": data["steps"],
        "current_step": data["current_step"],
        "backup": bak,
        "progress": ["Workspace ready", "Objective decomposed"],
        "token_estimate": data.get("token_estimate", 50),
    }


def update_objective(new_prompt: str) -> dict:
    """Rewrite objective.md from a new user prompt."""
    if not validate_workspace():
        create_workspace()

    bak = snapshot(OBJECTIVE_PATH)
    data = decompose_prompt(new_prompt)
    write_objective(data)
    return {
        "success": True,
        "objective": data["objective"],
        "current_step": data["current_step"],
        "backup": bak,
        "progress": ["Objective updated", "Steps reset"],
        "token_estimate": data.get("token_estimate", 50),
    }


def read_objective() -> dict:
    """Return current objective.md state."""
    if not validate_workspace():
        create_workspace()
    data = _read_objective()
    return {
        "success": True,
        **data,
        "token_estimate": 60,
    }


def capture_screen_tool() -> dict:
    """Take screenshot, preprocess, return path + metadata."""
    if not validate_workspace():
        create_workspace()
    result = _capture_screen()
    set_last_action("capture_screen")
    return {**result, "progress": ["Screenshot captured"]}


def find_element_tool(instruction: str) -> dict:
    """Ask VLM to locate element; return coords."""
    if not validate_workspace():
        create_workspace()

    from _sc_capture import preprocess_image
    import _sc_helpers as h

    cap = _capture_screen()
    if not cap.get("success"):
        return {"success": False, "error": "Screen capture failed.", "token_estimate": 10}

    image_b64 = preprocess_image(cap["path"])
    data = _read_objective()
    result = _find_element(
        instruction,
        image_b64,
        cap["width"],
        cap["height"],
        data.get("objective", ""),
        data.get("current_step", ""),
    )
    return result


def execute_action(action: str, x: int = 0, y: int = 0, text: str = "", key: str = "", clicks: int = 3) -> dict:
    """Execute click/double_click/right_click/type/key/scroll action."""
    if not validate_workspace():
        create_workspace()

    actions = {
        "click": lambda: click(x, y),
        "double_click": lambda: double_click(x, y),
        "right_click": lambda: right_click(x, y),
        "type": lambda: type_text(text),
        "key": lambda: press_key(key),
        "scroll": lambda: scroll(x, y, clicks),
    }
    fn = actions.get(action)
    if fn is None:
        return {
            "success": False,
            "error": f"Unknown action: {action!r}. Valid: {list(actions)}",
            "hint": "Use one of: click, double_click, right_click, type, key, scroll",
            "token_estimate": 20,
        }
    result = fn()
    return {**result, "progress": [f"Action executed: {action}"]}


def verify_step_tool(instruction: str) -> dict:
    """Take new screenshot, ask VLM if step succeeded."""
    if not validate_workspace():
        create_workspace()
    return _verify_step(instruction)


def get_status() -> dict:
    """Return current Status and progress from objective.md."""
    if not validate_workspace():
        create_workspace()
    data = _read_objective()
    steps = data.get("steps", "")
    total = steps.count("- [")
    done = steps.count("- [x]")
    return {
        "success": True,
        "status": data.get("status", "RUNNING"),
        "current_step": data.get("current_step", "(none)"),
        "objective": data.get("objective", ""),
        "progress_pct": round(done / total * 100) if total else 0,
        "steps_done": done,
        "steps_total": total,
        "clarification": data.get("clarification", ""),
        "token_estimate": 50,
    }
