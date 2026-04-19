from typing import Any


def ok(message: str, **extra: Any) -> dict:
    """Return a success progress entry."""
    return {"level": "ok", "message": message, **extra}


def fail(message: str, **extra: Any) -> dict:
    """Return a failure progress entry."""
    return {"level": "fail", "message": message, **extra}


def info(message: str, **extra: Any) -> dict:
    """Return an informational progress entry."""
    return {"level": "info", "message": message, **extra}


def warn(message: str, **extra: Any) -> dict:
    """Return a warning progress entry."""
    return {"level": "warn", "message": message, **extra}


def undo(message: str, **extra: Any) -> dict:
    """Return an undo progress entry."""
    return {"level": "undo", "message": message, **extra}
