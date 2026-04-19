import shutil
import time
from pathlib import Path

_VERSIONS_DIR = Path(".mcp_versions")


def snapshot(path: str | Path) -> str:
    """Copy file to .mcp_versions/ before mutation. Returns backup path."""
    src = Path(path)
    if not src.exists():
        return ""
    _VERSIONS_DIR.mkdir(exist_ok=True)
    ts = int(time.time() * 1000)
    dest = _VERSIONS_DIR / f"{src.name}.{ts}.bak"
    shutil.copy2(src, dest)
    return str(dest)


def restore(backup_path: str | Path) -> bool:
    """Restore a file from a snapshot backup. Returns True on success."""
    bak = Path(backup_path)
    if not bak.exists():
        return False
    # Reconstruct original name: strip trailing .<timestamp>.bak
    stem = bak.stem  # e.g. "objective.md.1713000000000"
    parts = stem.rsplit(".", 1)
    original_name = parts[0] if len(parts) == 2 else stem
    dest = Path("tmp") / original_name
    shutil.copy2(bak, dest)
    return True
