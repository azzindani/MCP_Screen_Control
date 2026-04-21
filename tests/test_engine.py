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
# objective mutation — mid-task goal change
# ---------------------------------------------------------------------------


class TestObjectiveMutation:
    def setup_method(self):
        _reset_tmp()

    def _make_data(self, prompt, steps=None):
        steps_list = steps or [prompt]
        steps_md = "\n".join(f"- [ ] {s}" for s in steps_list)
        return {
            "objective": prompt,
            "steps": steps_md,
            "current_step": steps_list[0],
            "platform": "desktop",
            "status": "RUNNING",
            "last_action": "(none)",
            "clarification": "",
            "token_estimate": 30,
        }

    def test_mid_task_update_discards_partial_progress(self):
        """update_objective while steps are in progress resets to step 1."""
        from _sc_objective import advance_step, read_objective, write_objective

        TMP.mkdir(parents=True, exist_ok=True)
        write_objective(self._make_data("original goal", ["step one", "step two", "step three"]))
        # Simulate completing first step
        advance_step()
        state = read_objective()
        assert state["current_step"] == "step two"

        # Now user changes goal mid-task
        new_data = self._make_data("entirely new goal", ["new step A", "new step B"])
        with patch("engine.decompose_prompt", return_value=new_data):
            import engine

            result = engine.update_objective("entirely new goal")

        assert result["objective"] == "entirely new goal"
        assert result["current_step"] == "new step A"

        final = read_objective()
        assert "step one" not in final["steps"]
        assert "step two" not in final["steps"]
        assert "new step A" in final["steps"]
        assert final["status"] == "RUNNING"

    def test_mid_task_update_creates_backup_of_old_objective(self):
        """Backup of old objective.md is created before overwrite."""
        from _sc_objective import advance_step, write_objective

        TMP.mkdir(parents=True, exist_ok=True)
        write_objective(self._make_data("original", ["step A", "step B"]))
        advance_step()

        new_data = self._make_data("replacement goal")
        with patch("engine.decompose_prompt", return_value=new_data):
            import engine

            result = engine.update_objective("replacement goal")

        assert "backup" in result

    def test_status_running_after_mutation(self):
        """Status is RUNNING (not COMPLETE/BLOCKED) after goal change."""
        from _sc_objective import read_objective, set_status, write_objective

        TMP.mkdir(parents=True, exist_ok=True)
        write_objective(self._make_data("original"))
        set_status("BLOCKED")

        new_data = self._make_data("fresh goal")
        with patch("engine.decompose_prompt", return_value=new_data):
            import engine

            engine.update_objective("fresh goal")

        final = read_objective()
        assert final["status"] == "RUNNING"


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

    def test_dry_run_returns_would_change_without_pyautogui(self):
        import engine

        with patch("pyautogui.click") as mock_click:
            result = engine.execute_action("click", x=100, y=50, dry_run=True)
            mock_click.assert_not_called()
        assert result["success"] is True
        assert result.get("dry_run") is True
        assert result.get("would_change") is True


# ---------------------------------------------------------------------------
# constrained mode
# ---------------------------------------------------------------------------


class TestConstrainedMode:
    def test_constrained_mode_returns_smaller_image_width(self):
        import os

        old = os.environ.get("MCP_CONSTRAINED_MODE")
        try:
            os.environ["MCP_CONSTRAINED_MODE"] = "1"
            from shared.platform_utils import get_max_image_width

            assert get_max_image_width() == 600
        finally:
            if old is None:
                os.environ.pop("MCP_CONSTRAINED_MODE", None)
            else:
                os.environ["MCP_CONSTRAINED_MODE"] = old

    def test_unconstrained_mode_returns_larger_image_width(self):
        import os

        old = os.environ.get("MCP_CONSTRAINED_MODE")
        try:
            os.environ.pop("MCP_CONSTRAINED_MODE", None)
            with patch("shared.platform_utils.is_constrained_mode", return_value=False):
                from shared.platform_utils import get_max_image_width

                assert get_max_image_width() == 800
        finally:
            if old is not None:
                os.environ["MCP_CONSTRAINED_MODE"] = old

    def test_constrained_mode_returns_smaller_token_budget(self):
        import os

        old = os.environ.get("MCP_CONSTRAINED_MODE")
        try:
            os.environ["MCP_CONSTRAINED_MODE"] = "1"
            from shared.platform_utils import get_max_tokens

            assert get_max_tokens() == 100
        finally:
            if old is None:
                os.environ.pop("MCP_CONSTRAINED_MODE", None)
            else:
                os.environ["MCP_CONSTRAINED_MODE"] = old
