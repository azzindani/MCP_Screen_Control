"""FastMCP server — thin wrappers only. All logic lives in engine.py."""
import engine
from fastmcp import FastMCP

mcp = FastMCP("screen-control")


@mcp.tool()
def start_task(prompt: str) -> dict:
    """Validate workspace, decompose prompt, write objective.md."""
    return engine.start_task(prompt)


@mcp.tool()
def update_objective(new_prompt: str) -> dict:
    """Rewrite objective.md from new user prompt; reset steps."""
    return engine.update_objective(new_prompt)


@mcp.tool()
def read_objective() -> dict:
    """Return current objective.md state as structured dict."""
    return engine.read_objective()


@mcp.tool()
def capture_screen() -> dict:
    """Take screenshot, save to tmp/, return path and dimensions."""
    return engine.capture_screen_tool()


@mcp.tool()
def find_element(instruction: str) -> dict:
    """Ask VLM to locate a UI element; return x, y, confidence."""
    return engine.find_element_tool(instruction)


@mcp.tool()
def execute_action(
    action: str,
    x: int = 0,
    y: int = 0,
    text: str = "",
    key: str = "",
    clicks: int = 3,
) -> dict:
    """Execute click/double_click/right_click/type/key/scroll at coords."""
    return engine.execute_action(action, x, y, text, key, clicks)


@mcp.tool()
def verify_step(instruction: str) -> dict:
    """Capture screen, ask VLM if current step succeeded or failed."""
    return engine.verify_step_tool(instruction)


@mcp.tool()
def get_status() -> dict:
    """Return Status, current step, and progress percentage."""
    return engine.get_status()


if __name__ == "__main__":
    mcp.run()
