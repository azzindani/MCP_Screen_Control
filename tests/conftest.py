"""Mock pyautogui before engine imports it — allows tests without X display."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

_pyautogui = ModuleType("pyautogui")
_pyautogui.FAILSAFE = True
_pyautogui.PAUSE = 0.1
_pyautogui.click = MagicMock()
_pyautogui.doubleClick = MagicMock()
_pyautogui.rightClick = MagicMock()
_pyautogui.write = MagicMock()
_pyautogui.press = MagicMock()
_pyautogui.scroll = MagicMock()
_pyautogui.moveTo = MagicMock()
sys.modules.setdefault("pyautogui", _pyautogui)
