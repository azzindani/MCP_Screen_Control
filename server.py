"""FastMCP server — thin wrappers only. All logic lives in engine.py."""

import argparse

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

import engine

mcp = FastMCP("screen-control")

_read_only = ToolAnnotations(readOnlyHint=True, destructiveHint=False)
_write = ToolAnnotations(readOnlyHint=False, destructiveHint=True)
_write_safe = ToolAnnotations(readOnlyHint=False, destructiveHint=False)


@mcp.tool(annotations=_write_safe)
def start_task(prompt: str) -> dict:
    """Validate workspace, decompose prompt, write objective.md."""
    return engine.start_task(prompt)


@mcp.tool(annotations=_write_safe)
def update_objective(new_prompt: str) -> dict:
    """Rewrite objective.md from new user prompt; reset steps."""
    return engine.update_objective(new_prompt)


@mcp.tool(annotations=_read_only)
def read_objective() -> dict:
    """Return current objective.md state as structured dict."""
    return engine.read_objective()


@mcp.tool(annotations=_read_only)
def capture_screen() -> dict:
    """Take screenshot, save to tmp/, return path and dimensions."""
    return engine.capture_screen_tool()


@mcp.tool(annotations=_read_only)
def find_element(instruction: str) -> dict:
    """Ask VLM to locate a UI element; return x, y, confidence."""
    return engine.find_element_tool(instruction)


@mcp.tool(annotations=_write)
def execute_action(
    action: str,
    x: int = 0,
    y: int = 0,
    text: str = "",
    key: str = "",
    clicks: int = 3,
    dry_run: bool = False,
) -> dict:
    """Execute click/double_click/right_click/type/key/scroll at coords."""
    return engine.execute_action(action, x, y, text, key, clicks, dry_run)


@mcp.tool(annotations=_read_only)
def verify_step(instruction: str) -> dict:
    """Capture screen, ask VLM if current step succeeded or failed."""
    return engine.verify_step_tool(instruction)


@mcp.tool(annotations=_read_only)
def get_status() -> dict:
    """Return Status, current step, and progress percentage."""
    return engine.get_status()


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Screen Control server")
    parser.add_argument(
        "--transport", default="stdio", choices=["stdio", "sse"], help="Transport mode"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE transport")
    args = parser.parse_args()
    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
