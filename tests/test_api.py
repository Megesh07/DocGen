"""Smoke tests for the fully hardened FastAPI API (versioned /api/v1/).

Route changes (Phase 5): all endpoints now live under /api/v1/.
Old routes return 410 Gone.

New tests:
- Phase 4: expanded health fields (project_root, uptime_seconds, version)
- Phase 5: old routes return 410
- Phase 3: file conflict detection returns 409

All file paths use tests/fixtures/api_tmp/ inside the project root (sandbox).
"""
import os
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Override PROJECT_ROOT before importing app so sandbox allows the fixture dir
_PROJECT_ROOT_FOR_TESTS = Path(__file__).parent.parent.resolve()
os.environ["_AUTODOC_TEST_ROOT"] = str(_PROJECT_ROOT_FOR_TESTS)

from autodocstring.api import app as _app_module  # noqa: E402
_app_module.PROJECT_ROOT = _PROJECT_ROOT_FOR_TESTS

from autodocstring.api.app import app  # noqa: E402

client = TestClient(app)

_FIXTURE_DIR = _PROJECT_ROOT_FOR_TESTS / "tests" / "fixtures" / "api_tmp"
_V1 = "/api/v1"  # version prefix


@pytest.fixture(autouse=True)
def clean_fixture_dir():
    """Create and clean up the test fixture directory for each test."""
    _FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(str(_FIXTURE_DIR), ignore_errors=True)


def _make_file(content: str, filename: str = "example.py") -> Path:
    p = _FIXTURE_DIR / filename
    p.write_text(content, encoding="utf-8")
    return p


def _scan(extra_files: dict = None) -> str:
    """Create files and return a session_id via POST /api/v1/scan."""
    if extra_files:
        for fname, content in extra_files.items():
            _make_file(content, fname)
    else:
        _make_file("def hello(name: str) -> str:\n    return name\n")
    r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
    assert r.status_code == 200, f"Scan failed: {r.json()}"
    return r.json()["session_id"]


# ---------------------------------------------------------------------------
# Phase 4: Expanded health endpoint
# ---------------------------------------------------------------------------

class TestExpandedHealth:
    """Tests for GET /api/v1/health (Phase 4)."""

    def test_health_returns_ok(self):
        r = client.get(f"{_V1}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_has_all_fields(self):
        data = client.get(f"{_V1}/health").json()
        for key in ("status", "llm_available", "active_sessions",
                    "project_root", "uptime_seconds", "version"):
            assert key in data, f"Missing health field: {key}"

    def test_health_version_is_string(self):
        data = client.get(f"{_V1}/health").json()
        assert isinstance(data["version"], str) and len(data["version"]) > 0

    def test_health_uptime_is_non_negative_int(self):
        data = client.get(f"{_V1}/health").json()
        assert isinstance(data["uptime_seconds"], int)
        assert data["uptime_seconds"] >= 0

    def test_health_project_root_is_string(self):
        data = client.get(f"{_V1}/health").json()
        assert isinstance(data["project_root"], str)
        assert len(data["project_root"]) > 0

    def test_health_active_sessions_is_int(self):
        data = client.get(f"{_V1}/health").json()
        assert isinstance(data["active_sessions"], int)
        assert data["active_sessions"] >= 0


# ---------------------------------------------------------------------------
# Phase 5: 410 Gone on old unversioned routes
# ---------------------------------------------------------------------------

class TestDeprecatedRoutes:
    """Tests for 410 Gone on old /scan, /generate, etc. (Phase 5)."""

    @pytest.mark.parametrize("path", [
        "/scan", "/generate", "/review", "/apply", "/diff", "/coverage", "/health"
    ])
    def test_old_route_returns_410(self, path):
        r = client.get(path)
        if r.status_code != 410:
            r = client.post(path, json={})
        assert r.status_code == 410, f"Expected 410 for {path}, got {r.status_code}"


# ---------------------------------------------------------------------------
# Phase 2: Sandbox under /api/v1/
# ---------------------------------------------------------------------------

class TestSandbox:
    """Tests for PROJECT_ROOT sandbox."""

    def test_scan_outside_root_returns_403(self):
        outside = "C:\\Windows" if os.name == "nt" else "/tmp"
        r = client.post(f"{_V1}/scan", json={"path": outside})
        assert r.status_code in (403, 404)

    def test_scan_within_root_returns_200(self):
        _make_file("def foo(x: int) -> int:\n    return x\n")
        r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/scan
# ---------------------------------------------------------------------------

class TestScanEndpoint:
    def test_scan_invalid_path_returns_404(self):
        nonexistent = str(_FIXTURE_DIR / "nonexistent_xyz")
        _FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        r = client.post(f"{_V1}/scan", json={"path": nonexistent})
        assert r.status_code == 404

    def test_scan_returns_session_id(self):
        _make_file("def foo(x: int) -> int:\n    return x\n")
        r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data and len(data["session_id"]) > 0

    def test_scan_returns_functions_list(self):
        _make_file("def foo(x: int) -> int:\n    return x\n")
        r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200
        assert isinstance(r.json()["functions"], list)

    def test_scan_result_has_required_fields(self):
        _make_file("def foo(x: int) -> int:\n    return x\n")
        r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200
        for item in r.json()["functions"]:
            for key in ("file", "function", "lineno", "confidence", "risk"):
                assert key in item

    def test_scan_results_sorted_deterministically(self):
        _make_file(
            "def second(b: int) -> int:\n    return b\n\n"
            "def first(a: int) -> int:\n    return a\n"
        )
        r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200
        linenos = [f["lineno"] for f in r.json()["functions"]]
        assert linenos == sorted(linenos)


# ---------------------------------------------------------------------------
# Phase 3: File conflict detection (409)
# ---------------------------------------------------------------------------

class TestConflictDetection:
    """Tests for file-change conflict detection (Phase 3)."""

    def test_conflict_returns_409_on_file_change(self):
        """Scanning a file, modifying it, then applying should return 409."""
        pyfile = _make_file("def greet(name: str) -> str:\n    return name\n", "conflict_test.py")

        # Scan: hash stored
        scan_r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert scan_r.status_code == 200
        session_id = scan_r.json()["session_id"]

        # Record an approval in the session
        funcs = scan_r.json()["functions"]
        if funcs:
            approval = {
                "session_id": session_id,
                "decisions": [{"file": funcs[0]["file"], "function": funcs[0]["function"],
                                "lineno": funcs[0]["lineno"], "approved": True}],
            }
            client.post(f"{_V1}/review", json=approval)

        # Modify the file AFTER scan (triggers conflict)
        pyfile.write_text(
            "def greet(name: str) -> str:\n    # modified\n    return f'Hello {name}'\n",
            encoding="utf-8",
        )

        # Apply: should detect conflict
        apply_r = client.post(f"{_V1}/apply", json={"session_id": session_id, "dry_run": False})
        # 409 conflict expected
        assert apply_r.status_code == 409
        detail = apply_r.json().get("detail", {})
        assert detail.get("error") == "file_modified_since_review"
        assert detail.get("action") == "please rescan"

    def test_no_conflict_if_file_unchanged(self):
        """No conflict should be raised if the file hasn't changed."""
        _make_file("def greet(name: str) -> str:\n    return name\n", "nochange.py")

        scan_r = client.post(f"{_V1}/scan", json={"path": str(_FIXTURE_DIR)})
        assert scan_r.status_code == 200
        session_id = scan_r.json()["session_id"]

        # Record approvals
        funcs = scan_r.json()["functions"]
        if funcs:
            client.post(f"{_V1}/review", json={
                "session_id": session_id,
                "decisions": [{"file": funcs[0]["file"], "function": funcs[0]["function"],
                                "lineno": funcs[0]["lineno"], "approved": True}],
            })

        # Apply immediately (no modification) — should NOT return 409
        apply_r = client.post(f"{_V1}/apply", json={"session_id": session_id, "dry_run": True})
        assert apply_r.status_code != 409


# ---------------------------------------------------------------------------
# POST /api/v1/generate
# ---------------------------------------------------------------------------

class TestGenerateEndpoint:
    def test_generate_invalid_session_returns_404(self):
        r = client.post(f"{_V1}/generate", json={"session_id": "nonexistent"})
        assert r.status_code == 404

    def test_generate_returns_list(self):
        session_id = _scan()
        r = client.post(f"{_V1}/generate", json={"session_id": session_id})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# GET /api/v1/coverage
# ---------------------------------------------------------------------------

class TestCoverageEndpoint:
    def test_coverage_invalid_path_returns_error(self):
        r = client.get(f"{_V1}/coverage", params={"path": "/nonexistent_xyz"})
        assert r.status_code in (403, 404)

    def test_coverage_returns_all_fields(self):
        _make_file('def f(x: int) -> int:\n    """Documented."""\n    return x\n')
        r = client.get(f"{_V1}/coverage", params={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200
        data = r.json()
        for key in ("documentation_coverage_before", "documentation_coverage_after",
                    "automation_safe_percent", "requires_review_percent",
                    "unsafe_skipped_percent", "total_functions", "total_files",
                    "estimated_new_docstrings", "unchanged_existing", "skipped_existing"):
            assert key in data, f"Missing: {key}"

    def test_coverage_percentages_sum_to_100(self):
        _make_file("def a(x: int) -> int:\n    return x\ndef b():\n    pass\n")
        r = client.get(f"{_V1}/coverage", params={"path": str(_FIXTURE_DIR)})
        assert r.status_code == 200
        data = r.json()
        total = (data["automation_safe_percent"] + data["requires_review_percent"]
                 + data["unsafe_skipped_percent"])
        assert abs(total - 100.0) < 1.0


# ---------------------------------------------------------------------------
# GET /api/v1/diff
# ---------------------------------------------------------------------------

class TestDiffEndpoint:
    def test_diff_invalid_session_returns_404(self):
        r = client.get(f"{_V1}/diff", params={"session_id": "nonexistent"})
        assert r.status_code == 404

    def test_diff_returns_required_keys(self):
        session_id = _scan()
        r = client.get(f"{_V1}/diff", params={"session_id": session_id})
        assert r.status_code == 200
        data = r.json()
        assert "diff" in data and "files" in data and "session_id" in data


# ---------------------------------------------------------------------------
# POST /api/v1/review
# ---------------------------------------------------------------------------

class TestReviewEndpoint:
    def test_review_invalid_session_returns_404(self):
        r = client.post(f"{_V1}/review", json={
            "session_id": "nonexistent",
            "decisions": [{"file": "x.py", "function": "foo", "lineno": 1, "approved": True}]
        })
        assert r.status_code == 404

    def test_review_returns_decision_summary(self):
        session_id = _scan()
        r = client.post(f"{_V1}/review", json={
            "session_id": session_id,
            "decisions": [
                {"file": "x.py", "function": "foo", "lineno": 1, "approved": True},
                {"file": "x.py", "function": "bar", "lineno": 5, "approved": False},
            ]
        })
        assert r.status_code == 200
        data = r.json()
        assert data["approved"] == 1
        assert data["rejected"] == 1
        assert data["total"] == 2
        assert "session_id" in data
