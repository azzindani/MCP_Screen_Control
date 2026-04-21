"""Validate operation arrays before applying — prevents orphaned snapshots."""

_VALID_ACTIONS = frozenset({"click", "double_click", "right_click", "type", "key", "scroll"})


def validate_ops(ops: list[dict]) -> list[str]:
    """Return list of unknown op names. Empty list means all valid."""
    unknown = []
    for op in ops:
        name = op.get("op") if isinstance(op, dict) else None
        if name not in _VALID_ACTIONS:
            unknown.append(str(name))
    return unknown
