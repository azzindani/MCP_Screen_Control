import json
import time
from pathlib import Path

_RECEIPT_PATH = Path("tmp") / "receipt.jsonl"


def log_receipt(tool: str, action: str, result: dict) -> None:
    """Append one JSONL line to tmp/receipt.jsonl."""
    _RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": int(time.time() * 1000),
        "tool": tool,
        "action": action,
        "success": result.get("success", False),
    }
    with open(_RECEIPT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
