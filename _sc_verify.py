"""Post-action verification loop."""

from _sc_capture import capture_screen, preprocess_image
from _sc_objective import advance_step, read_objective, set_status
from _sc_vision import verify_element
from shared.platform_utils import get_max_retries

_retry_counter: dict[str, int] = {}


def verify_step(instruction: str) -> dict:
    """Capture screen, ask VLM if step succeeded; advance or block."""
    cap = capture_screen()
    if not cap.get("success"):
        return {
            "success": False,
            "error": "Screen capture failed.",
            "token_estimate": 10,
        }

    image_b64 = preprocess_image(cap["path"])
    data = read_objective()
    objective = data.get("objective", "")
    current_step = data.get("current_step", "")

    result = verify_element(instruction, image_b64, objective, current_step)

    if result.get("success"):
        _retry_counter.pop(current_step, None)
        advance_step()
        updated = read_objective()
        return {
            "success": True,
            "reason": result.get("reason", ""),
            "status": updated.get("status", "RUNNING"),
            "next_step": updated.get("current_step", "(none)"),
            "progress": [f"Step completed: {current_step}"],
            "token_estimate": 40,
        }

    # Count consecutive failures
    _retry_counter[current_step] = _retry_counter.get(current_step, 0) + 1
    if _retry_counter[current_step] >= get_max_retries():
        set_status("BLOCKED")
        _retry_counter.pop(current_step, None)
        return {
            "success": False,
            "reason": result.get("reason", ""),
            "status": "BLOCKED",
            "hint": "Three consecutive failures. Objective status set to BLOCKED.",
            "token_estimate": 30,
        }

    return {
        "success": False,
        "reason": result.get("reason", ""),
        "retries_remaining": get_max_retries() - _retry_counter[current_step],
        "token_estimate": 25,
    }
