"""CI helper — verify all @mcp.tool() docstrings are <= 80 characters."""

import ast
import sys
from pathlib import Path


def check(server_file: str = "server.py") -> bool:
    src = Path(server_file).read_text(encoding="utf-8")
    tree = ast.parse(src)
    failures: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            doc = ast.get_docstring(node)
            if doc and len(doc) > 80:
                failures.append((node.name, len(doc)))
    if failures:
        for name, length in failures:
            print(f"FAIL  {name!r}: docstring is {length} chars (max 80)")
        return False
    total = sum(
        1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and ast.get_docstring(n)
    )
    print(f"OK  {total} tool docstrings verified (<= 80 chars each)")
    return True


if __name__ == "__main__":
    ok = check()
    sys.exit(0 if ok else 1)
