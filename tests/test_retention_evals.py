"""Regression gates for the synthetic retention evaluation corpus."""

from dataclasses import replace

from evals.retention import SCENARIOS, Scenario, run_suite


def test_retention_suite_has_at_least_twenty_distinct_scenarios():
    assert len(SCENARIOS) >= 20
    assert len({scenario.name for scenario in SCENARIOS}) == len(SCENARIOS)


def test_retention_suite_has_positive_and_negative_outcomes():
    expected = {scenario.expected for scenario in SCENARIOS}
    assert expected == {"applied", "rejected"}
    assert sum(s.expected == "rejected" for s in SCENARIOS) >= 15


def test_retention_suite_has_security_and_boundary_coverage():
    names = {s.name for s in SCENARIOS}
    assert {
        "cross-tenant",
        "no-account-access",
        "no-confirmation",
        "nan-credit",
        "nan-monthly",
        "above-cap",
        "infinite-dispute",
    } <= names


def test_retention_suite_passes_all_expected_actions():
    result = run_suite()
    assert result["scenario_count"] == len(SCENARIOS)
    assert result["passed"] == len(SCENARIOS)
    assert result["failures"] == []


def test_scenario_contract_is_immutable():
    scenario = Scenario("example", "10", "5", True, True, True, "5", True, "applied")
    modified = replace(scenario, amount="6")
    assert scenario.amount == "5"
    assert modified.amount == "6"
