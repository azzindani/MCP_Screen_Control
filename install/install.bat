@echo off
setlocal

echo === MCP Screen Control - Install ===

:: Check Python 3.12
python --version 2>&1 | findstr "3.12" >nul
if errorlevel 1 (
    echo ERROR: Python 3.12 required.
    exit /b 1
)

:: Install uv if missing
where uv >nul 2>&1
if errorlevel 1 (
    echo Installing uv...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)

:: Sync dependencies
echo Syncing Python dependencies...
uv sync

:: Write MCP config
echo Writing MCP config...
uv run python install\mcp_config_writer.py

echo.
echo Installation complete.
echo Start the server: uv run python server.py
