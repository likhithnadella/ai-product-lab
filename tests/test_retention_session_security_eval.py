"""Regression tests for the synthetic session security scenario runner."""

import json
import subprocess
import sys

import pytest

from evals.retention_session_security import CASES, run_case, run_suite


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_session_boundary_scenario(case):
    result = run_case(case)
    assert result["passed"], result
    assert result["observed_applied"] == case.expected_applied


def test_suite_is_complete_and_independent():
    names = [case.name for case in CASES]
    assert len(names) == len(set(names))
    assert len(names) >= 9
    report = run_suite()
    assert report["cases"] == len(CASES)
    assert report["passed"] + report["failed"] == len(CASES)
    assert report["failed"] == 0


def test_cli_emits_machine_readable_evidence_without_offer_handles():
    completed = subprocess.run(
        [sys.executable, "-m", "evals.retention_session_security"],
        check=True, capture_output=True, text=True,
    )
    report = json.loads(completed.stdout)
    assert report["cases"] == len(CASES)
    assert report["failed"] == 0
    assert "offer_handle" not in completed.stdout
    assert "session-a" not in completed.stdout
