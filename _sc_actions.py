"""pyautogui mouse/keyboard execution."""
import pyautogui

from _sc_helpers import OBJECTIVE_PATH
from _sc_objective import set_last_action
from shared.receipt import log_receipt
from shared.version_control import snapshot

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1


def _snap_and_act(tool: str, action: str, fn, *args, **kwargs) -> dict:
    bak = snapshot(OBJECTIVE_PATH)
    try:
        fn(*args, **kwargs)
        set_last_action(f"{tool}: {action}")
        result = {"success": True, "action": action, "backup": bak, "token_estimate": 20}
        log_receipt(tool, action, result)
        return result
    except Exception as exc:
        result = {
            "success": False,
            "error": str(exc),
            "hint": "Check coordinates or system permissions.",
            "backup": bak,
            "token_estimate": 20,
        }
        log_receipt(tool, action, result)
        return result


def click(x: int, y: int) -> dict:
    return _snap_and_act("click", f"click({x},{y})", pyautogui.click, x, y)


def double_click(x: int, y: int) -> dict:
    return _snap_and_act("double_click", f"double_click({x},{y})", pyautogui.doubleClick, x, y)


def right_click(x: int, y: int) -> dict:
    return _snap_and_act("right_click", f"right_click({x},{y})", pyautogui.rightClick, x, y)


def type_text(text: str) -> dict:
    return _snap_and_act("type_text", f"type({text!r})", pyautogui.write, text, interval=0.02)


def press_key(key: str) -> dict:
    return _snap_and_act("press_key", f"press({key!r})", pyautogui.press, key)


def scroll(x: int, y: int, clicks: int) -> dict:
    def _scroll():
        pyautogui.moveTo(x, y)
        pyautogui.scroll(clicks)

    return _snap_and_act("scroll", f"scroll({x},{y},{clicks})", _scroll)
