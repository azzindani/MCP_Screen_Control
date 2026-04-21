"""Operation receipt log — append_receipt never raises."""

import json
from datetime import datetime, timezone
from pathlib import Path


def _receipt_path(file_path: str | Path) -> Path:
    p = Path(file_path)
    return p.parent / f"{p.stem}.receipt.json"


def append_receipt(
    file_path: str | Path,
    tool: str,
    args: dict,
    result: str,
    backup: str | None = None,
) -> None:
    """Append one record to the receipt log alongside file_path. Never raises."""
    try:
        rpath = _receipt_path(file_path)
        records: list = []
        if rpath.exists():
            try:
                records = json.loads(rpath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                records = []
        records.append(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool,
                "args": args,
                "result": result,
                "backup": backup or "",
            }
        )
        rpath.write_text(json.dumps(records, indent=2), encoding="utf-8")
    except Exception:
        pass


def read_receipt_log(file_path: str | Path) -> list[dict]:
    """Read full receipt log for a file. Returns empty list if none exists."""
    try:
        rpath = _receipt_path(file_path)
        if not rpath.exists():
            return []
        return json.loads(rpath.read_text(encoding="utf-8"))
    except Exception:
        return []
