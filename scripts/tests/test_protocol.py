"""测试 protocol.py 和 fsm.py"""

import json
import io
import sys
import pytest

from utils.protocol import emit, emit_progress, emit_fatal
from utils.fsm import detect_state, JobState


class TestEmit:
    def test_emit_minimal(self):
        buf = io.StringIO()
        emit("test.step", "test message", stream=buf)
        data = json.loads(buf.getvalue())
        assert data["step"] == "test.step"
        assert data["status"] == "ok"
        assert data["message"] == "test message"

    def test_emit_with_data(self):
        buf = io.StringIO()
        emit("test.data", "with payload", data={"count": 5, "items": ["a", "b"]}, stream=buf)
        data = json.loads(buf.getvalue())
        assert data["data"]["count"] == 5
        assert data["data"]["items"] == ["a", "b"]

    def test_emit_with_warnings(self):
        buf = io.StringIO()
        emit("test.warn", "warning message", status="warn", warnings=["something off"], stream=buf)
        data = json.loads(buf.getvalue())
        assert data["status"] == "warn"
        assert data["warnings"] == ["something off"]

    def test_emit_error(self):
        buf = io.StringIO()
        emit("test.error", "error message", status="error",
             error={"code": "ERR_TEST", "traceback": ""}, stream=buf)
        data = json.loads(buf.getvalue())
        assert data["status"] == "error"
        assert data["error"]["code"] == "ERR_TEST"

    def test_emit_ensure_ascii_false(self):
        buf = io.StringIO()
        emit("test.cn", "中文消息", data={"key": "值"}, stream=buf)
        raw = buf.getvalue()
        assert "中文" in raw
        assert "\\u" not in raw

    def test_emit_default_stream_stdout(self):
        # emit defaults to stdout; just verify no crash
        emit("test.default", "default stream check")

    def test_emit_progress(self):
        buf = io.StringIO()
        emit_progress("test.progress", 3, 10, "3 of 10", stream=buf)
        data = json.loads(buf.getvalue())
        assert data["step"] == "test.progress"
        assert data["progress"]["current"] == 3
        assert data["progress"]["total"] == 10
        assert data["progress"]["pct"] == 30.0

    def test_emit_progress_zero_total(self):
        buf = io.StringIO()
        emit_progress("test.zero", 0, 0, "zero", stream=buf)
        data = json.loads(buf.getvalue())
        assert data["progress"]["pct"] == 0

    def test_emit_fatal_exits(self):
        with pytest.raises(SystemExit) as exc:
            emit_fatal("FATAL_TEST", "fatal error")
        assert exc.value.code == 1


class TestDetectState:
    def test_no_state_empty(self):
        assert detect_state({}) == JobState.NO_STATE

    def test_no_state_none(self):
        assert detect_state(None) == JobState.NO_STATE

    def test_no_state_no_profile(self):
        assert detect_state({"job_search": {}}) == JobState.NO_STATE

    def test_profile_done(self):
        data = {"profile": {"tech_stack": ["Python"]}, "job_search": {"status": "not_started"}}
        assert detect_state(data) == JobState.PROFILE_DONE

    def test_scan_done(self):
        data = {
            "profile": {"tech_stack": ["Python"]},
            "job_search": {"status": "done"},
            "analysis": {"report_file": ""},
        }
        assert detect_state(data) == JobState.SCAN_DONE

    def test_analyze_done(self):
        data = {
            "profile": {"tech_stack": ["Python"]},
            "job_search": {"status": "done"},
            "analysis": {"report_file": "report.md"},
            "learning_plan": {"target_role": ""},
        }
        assert detect_state(data) == JobState.ANALYZE_DONE

    def test_plan_done(self):
        data = {
            "profile": {"tech_stack": ["Python"]},
            "job_search": {"status": "done"},
            "analysis": {"report_file": "report.md"},
            "learning_plan": {"target_role": "AI Engineer", "plan_file": "plan.md"},
        }
        assert detect_state(data) == JobState.PLAN_DONE


class TestStateToSkillMap:
    def test_all_states_mapped(self):
        from utils.fsm import STATE_TO_SKILL
        for state in JobState:
            assert state in STATE_TO_SKILL, f"{state} missing from STATE_TO_SKILL"
