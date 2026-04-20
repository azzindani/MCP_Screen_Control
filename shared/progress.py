"""Progress output helpers — ok/fail/info/warn/undo — never print to stdout."""


def ok(msg: str, detail: str = "") -> dict:
    """Return a success progress entry."""
    return {"icon": "\u2714", "msg": msg, "detail": detail}


def fail(msg: str, detail: str = "") -> dict:
    """Return a failure progress entry."""
    return {"icon": "\u2718", "msg": msg, "detail": detail}


def info(msg: str, detail: str = "") -> dict:
    """Return an informational progress entry."""
    return {"icon": "\u2139", "msg": msg, "detail": detail}


def warn(msg: str, detail: str = "") -> dict:
    """Return a warning progress entry."""
    return {"icon": "\u26a0", "msg": msg, "detail": detail}


def undo(msg: str, detail: str = "") -> dict:
    """Return an undo progress entry."""
    return {"icon": "\u21a9", "msg": msg, "detail": detail}
