"""Snapshot / restore with UTC ISO timestamps and atomic temp+rename."""

import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def snapshot(path: str | Path) -> str:
    """Copy file to .mcp_versions/ atomically. Returns backup path."""
    src = Path(path)
    if not src.exists():
        return ""
    versions_dir = src.parent / ".mcp_versions"
    versions_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")
    backup_name = f"{src.stem}_{ts}{src.suffix}.bak"
    backup_path = versions_dir / backup_name

    fd, tmp = tempfile.mkstemp(dir=versions_dir)
    try:
        os.close(fd)
        shutil.copy2(str(src), tmp)
        shutil.move(tmp, str(backup_path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    return str(backup_path)


def restore(backup_path: str | Path) -> bool:
    """Restore a file from a snapshot backup. Returns True on success."""
    bak = Path(backup_path)
    if not bak.exists():
        return False
    # backup_name = "{stem}_{ts}{suffix}.bak" → original = parent.parent / f"{stem}{suffix}"
    # Strip the trailing .bak first
    without_bak = bak.stem  # e.g. "objective_2026-01-01T00-00-00-000000Z.md"
    # Find the last occurrence of the suffix pattern (last dot + non-timestamp chars)
    suffix_start = without_bak.rfind(".")
    if suffix_start != -1:
        suffix = without_bak[suffix_start:]  # e.g. ".md"
        stem = without_bak[:suffix_start]  # e.g. "objective_2026-..."
        # Strip timestamp: everything after the last underscore before the UTC suffix
        ts_start = stem.rfind("_")
        original_stem = stem[:ts_start] if ts_start != -1 else stem
        original_name = original_stem + suffix
    else:
        original_name = without_bak

    dest = bak.parent.parent / original_name
    shutil.copy2(str(bak), str(dest))
    return True
