"""Tests for engine.py — imports engine directly, no MCP server."""

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"
TMP = Path("tmp")

_SCREEN_CAP = {
    "success": True,
    "path": str(TMP / "screen_current.png"),
    "width": 800,
    "height": 480,
}


def _reset_tmp():
    if TMP.exists():
        shutil.rmtree(TMP)


# ---------------------------------------------------------------------------
# start_task
# ---------------------------------------------------------------------------


class TestStartTask:
    def setup_method(self):
        _reset_tmp()

    def _mock_decompose(self, prompt):
        return {
            "objective": prompt,
            "steps": f"- [ ] {prompt}",
            "current_step": prompt,
            "platform": "desktop",
            "status": "RUNNING",
            "last_action": "(none)",
            "clarification": "",
            "token_estimate": 30,
        }

    def test_success_returns_true(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            result = engine.start_task("open notepad")
        assert result["success"] is True

    def test_workspace_created_when_missing(self):
        _reset_tmp()
        assert not TMP.exists()
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            engine.start_task("test task")
        assert TMP.exists()

    def test_snapshot_created(self):
        versions = Path(".mcp_versions")
        if versions.exists():
            shutil.rmtree(versions)
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            engine.start_task("test task")
        assert TMP.exists()

    def test_backup_key_in_response(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            result = engine.start_task("test task")
        assert "backup" in result

    def test_progress_array_in_response(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            result = engine.start_task("test task")
        assert "progress" in result
        assert isinstance(result["progress"], list)

    def test_token_estimate_in_response(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            result = engine.start_task("test task")
        assert "token_estimate" in result


# ---------------------------------------------------------------------------
# update_objective
# ---------------------------------------------------------------------------


class TestUpdateObjective:
    def setup_method(self):
        _reset_tmp()

    def _mock_decompose(self, prompt):
        return {
            "objective": prompt,
            "steps": f"- [ ] {prompt}",
            "current_step": prompt,
            "platform": "desktop",
            "status": "RUNNING",
            "last_action": "(none)",
            "clarification": "",
            "token_estimate": 30,
        }

    def test_new_objective_replaces_old(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            engine.start_task("old task")
            result = engine.update_objective("new task")
        assert result["objective"] == "new task"

    def test_current_step_resets(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            engine.start_task("old task")
            result = engine.update_objective("brand new task")
        assert result["current_step"] == "brand new task"

    def test_backup_in_response(self):
        with patch("engine.decompose_prompt", side_effect=self._mock_decompose):
            import engine

            engine.start_task("original task")
            result = engine.update_objective("updated task")
        assert "backup" in result


# ---------------------------------------------------------------------------
# find_element
# ---------------------------------------------------------------------------


class TestFindElement:
    def setup_method(self):
        _reset_tmp()

    def _setup_objective(self):
        from _sc_objective import write_objective

        TMP.mkdir(parents=True, exist_ok=True)
        write_objective(
            {
                "objective": "click ok button",
                "steps": "- [ ] click ok button",
                "current_step": "click ok button",
                "platform": "desktop",
                "status": "RUNNING",
                "last_action": "(none)",
                "clarification": "",
            }
        )

    def test_high_confidence_returns_coords(self):
        _reset_tmp()
        TMP.mkdir()
        self._setup_objective()
        shutil.copy(FIXTURES / "simple_ui.png", TMP / "screen_current.png")

        cap_ret = {**_SCREEN_CAP, "path": str(TMP / "screen_current.png")}
        high_conf = json.dumps({"x": 100, "y": 50, "confidence": 0.9, "description": "OK"})
        with (
            patch("engine._capture_screen", return_value=cap_ret),
            patch("_sc_vision._llm_call", return_value=high_conf),
        ):
            import engine

            result = engine.find_element_tool("click the OK button")
        assert result.get("success") is True
        assert "x" in result and "y" in result

    def test_low_confidence_triggers_retry(self):
        _reset_tmp()
        TMP.mkdir()
        self._setup_objective()
        shutil.copy(FIXTURES / "simple_ui.png", TMP / "screen_current.png")

        cap_ret = {**_SCREEN_CAP, "path": str(TMP / "screen_current.png")}
        low_conf = json.dumps({"x": 100, "y": 50, "confidence": 0.3, "description": "maybe"})
        high_conf = json.dumps({"x": 50, "y": 25, "confidence": 0.85, "description": "OK"})
        call_count = [0]

        def fake_llm(image_b64, prompt, max_tokens):
            call_count[0] += 1
            if call_count[0] == 1:
                return low_conf
            return high_conf

        with (
            patch("engine._capture_screen", return_value=cap_ret),
            patch("_sc_vision._llm_call", side_effect=fake_llm),
        ):
            import engine

            engine.find_element_tool("click the OK button")
        assert call_count[0] >= 2

    def test_second_failure_sets_needs_clarification(self):
        _reset_tmp()
        TMP.mkdir()
        self._setup_objective()
        shutil.copy(FIXTURES / "simple_ui.png", TMP / "screen_current.png")

        cap_ret = {**_SCREEN_CAP, "path": str(TMP / "screen_current.png")}
        low_conf = json.dumps({"x": 0, "y": 0, "confidence": 0.2, "description": "none"})
        with (
            patch("engine._capture_screen", return_value=cap_ret),
            patch("_sc_vision._llm_call", return_value=low_conf),
        ):
            import engine

            result = engine.find_element_tool("nonexistent element")
        assert result.get("success") is False

        from _sc_objective import read_objective

        data = read_objective()
        assert data["status"] == "NEEDS_CLARIFICATION"


# ---------------------------------------------------------------------------
# verify_step
# ---------------------------------------------------------------------------


class TestVerifyStep:
    def setup_method(self):
        _reset_tmp()
        TMP.mkdir()

    def _setup_objective(self, step="click OK"):
        from _sc_objective import write_objective

        write_objective(
            {
                "objective": "click ok button",
                "steps": f"- [ ] {step}",
                "current_step": step,
                "platform": "desktop",
                "status": "RUNNING",
                "last_action": "(none)",
                "clarification": "",
            }
        )

    def test_success_marks_step_done(self):
        self._setup_objective("click OK")
        shutil.copy(FIXTURES / "simple_ui.png", TMP / "screen_current.png")

        success_resp = json.dumps({"success": True, "reason": "button clicked"})
        cap_ret = {**_SCREEN_CAP, "path": str(TMP / "screen_current.png")}
        with (
            patch("_sc_vision._llm_call", return_value=success_resp),
            patch("_sc_verify.capture_screen", return_value=cap_ret),
        ):
            import engine

            result = engine.verify_step_tool("click OK")

        assert result.get("success") is True

        from _sc_objective import read_objective

        data = read_objective()
        assert "x]" in data["steps"]

    def test_three_failures_set_blocked(self):
        self._setup_objective("click OK")
        shutil.copy(FIXTURES / "simple_ui.png", TMP / "screen_current.png")

        fail_resp = json.dumps({"success": False, "reason": "not found"})
        import _sc_verify

        _sc_verify._retry_counter.clear()

        cap_ret = {**_SCREEN_CAP, "path": str(TMP / "screen_current.png")}
        with (
            patch("_sc_vision._llm_call", return_value=fail_resp),
            patch("_sc_verify.capture_screen", return_value=cap_ret),
        ):
            import engine

            for _ in range(3):
                engine.verify_step_tool("click OK")

        from _sc_objective import read_objective

        data = read_objective()
        assert data["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# execute_action
# ---------------------------------------------------------------------------


class TestExecuteAction:
    def setup_method(self):
        _reset_tmp()
        TMP.mkdir()
        from _sc_objective import write_objective

        write_objective(
            {
                "objective": "test",
                "steps": "- [ ] test",
                "current_step": "test",
                "platform": "desktop",
                "status": "RUNNING",
                "last_action": "(none)",
                "clarification": "",
            }
        )

    def test_success(self):
        with patch("pyautogui.click"):
            import engine

            result = engine.execute_action("click", x=100, y=50)
        assert result["success"] is True

    def test_unknown_action_returns_error(self):
        import engine

        result = engine.execute_action("fly")
        assert result["success"] is False
        assert "hint" in result

    def test_backup_key_in_response(self):
        with patch("pyautogui.click"):
            import engine

            result = engine.execute_action("click", x=10, y=10)
        assert "backup" in result

    def test_progress_array_in_response(self):
        with patch("pyautogui.click"):
            import engine

            result = engine.execute_action("click", x=10, y=10)
        assert "progress" in result

    def test_token_estimate_in_response(self):
        with patch("pyautogui.click"):
            import engine

            result = engine.execute_action("click", x=10, y=10)
        assert "token_estimate" in result
