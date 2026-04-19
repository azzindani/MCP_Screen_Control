"""LM Studio VLM calls for coordinate extraction and verification."""
import json

import httpx

from _sc_helpers import CONFIDENCE_THRESHOLD, LMSTUDIO_BASE_URL, SCREEN_CURRENT
from _sc_capture import preprocess_crop, preprocess_image
from _sc_objective import set_clarification
from shared.platform_utils import get_max_image_width, get_max_retries, get_max_tokens


def find_element(
    instruction: str,
    image_b64: str,
    screen_w: int,
    screen_h: int,
    objective: str,
    current_step: str,
) -> dict:
    """Ask VLM to locate a UI element. Returns {x, y, confidence, description}."""
    result = _call_locate(instruction, image_b64, screen_w, screen_h, objective, current_step)

    if result.get("error"):
        return result

    confidence = result.get("confidence", 0.0)
    if confidence >= CONFIDENCE_THRESHOLD:
        return result

    # Retry with each quadrant crop at higher effective resolution
    for quadrant in range(4):
        crop_b64 = preprocess_crop(SCREEN_CURRENT, quadrant)
        retry = _call_locate(instruction, crop_b64, screen_w // 2, screen_h // 2, objective, current_step)
        if retry.get("confidence", 0.0) >= CONFIDENCE_THRESHOLD:
            # Map quadrant-local coords back to screen coords
            x_off = (quadrant % 2) * (screen_w // 2)
            y_off = (quadrant // 2) * (screen_h // 2)
            retry["x"] = retry.get("x", 0) + x_off
            retry["y"] = retry.get("y", 0) + y_off
            return retry

    set_clarification(
        "Cannot locate element. Please describe it more precisely or bring it into view."
    )
    return {
        "success": False,
        "error": "Element not found with sufficient confidence.",
        "hint": "Status set to NEEDS_CLARIFICATION",
        "token_estimate": 30,
    }


def verify_element(instruction: str, image_b64: str, objective: str, current_step: str) -> dict:
    """Binary VLM call: did the step succeed? Returns {success, reason}."""
    prompt = (
        f"FINAL OBJECTIVE: {objective}\n"
        f"CURRENT STEP: {current_step}\n"
        f"TASK: Did the action for CURRENT STEP succeed? Answer only JSON: "
        '{"success": bool, "reason": str}'
    )
    raw = _llm_call(image_b64, prompt, get_max_tokens())
    try:
        data = json.loads(raw)
        return {
            "success": bool(data.get("success", False)),
            "reason": str(data.get("reason", "")),
            "token_estimate": 30,
        }
    except (json.JSONDecodeError, KeyError):
        return {"success": False, "reason": "VLM response unparseable", "token_estimate": 10}


def decompose_prompt(user_prompt: str) -> dict:
    """Text-only LM Studio call: decompose prompt → structured objective dict."""
    schema = (
        '{"objective": str, "steps": ["step1", ...], "platform": str}'
    )
    prompt = (
        f"Decompose the following user instruction into an ordered list of atomic UI steps.\n"
        f"Instruction: {user_prompt}\n"
        f"Return only JSON matching: {schema}\n"
        "Each step must be a single, atomic UI interaction (one click, one keystroke, etc.)."
    )
    raw = _text_call(prompt, max_tokens=300)
    try:
        data = json.loads(raw)
        steps_list = data.get("steps", [])
        steps_md = "\n".join(f"- [ ] {s}" for s in steps_list)
        return {
            "objective": data.get("objective", user_prompt),
            "steps": steps_md if steps_md else "- [ ] " + user_prompt,
            "current_step": steps_list[0] if steps_list else user_prompt,
            "platform": data.get("platform", "unknown"),
            "status": "RUNNING",
            "last_action": "(none)",
            "clarification": "",
            "token_estimate": 50,
        }
    except (json.JSONDecodeError, KeyError, IndexError):
        return {
            "objective": user_prompt,
            "steps": f"- [ ] {user_prompt}",
            "current_step": user_prompt,
            "platform": "unknown",
            "status": "RUNNING",
            "last_action": "(none)",
            "clarification": "",
            "token_estimate": 20,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _call_locate(
    instruction: str,
    image_b64: str,
    screen_w: int,
    screen_h: int,
    objective: str,
    current_step: str,
) -> dict:
    prompt = (
        f"FINAL OBJECTIVE: {objective}\n"
        f"CURRENT STEP: {current_step}\n"
        f"TASK: Locate the UI element needed for CURRENT STEP.\n"
        f"Screen size: {screen_w}x{screen_h} pixels.\n"
        'Return only JSON: {"x": int, "y": int, "confidence": float, "description": str}'
    )
    raw = _llm_call(image_b64, prompt, get_max_tokens())
    try:
        data = json.loads(raw)
        return {
            "success": True,
            "x": int(data["x"]),
            "y": int(data["y"]),
            "confidence": float(data.get("confidence", 0.0)),
            "description": str(data.get("description", "")),
            "token_estimate": 30,
        }
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return {"success": False, "error": str(exc), "token_estimate": 10}


def _llm_call(image_b64: str, prompt: str, max_tokens: int) -> str:
    """POST to LM Studio vision endpoint, return raw string."""
    payload = {
        "model": "local-model",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = httpx.post(
            f"{LMSTUDIO_BASE_URL}/chat/completions",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        return json.dumps({"error": str(exc)})


def _text_call(prompt: str, max_tokens: int = 300) -> str:
    """POST text-only call to LM Studio."""
    payload = {
        "model": "local-model",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = httpx.post(
            f"{LMSTUDIO_BASE_URL}/chat/completions",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        return json.dumps({"error": str(exc)})
