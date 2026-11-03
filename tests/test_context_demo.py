"""End-to-end synthetic smoke tests for the local context preview demonstration."""

from app.context_demo import demo_report


def test_demo_returns_only_the_authorized_tenant_and_source() -> None:
    report = demo_report()
    assert report["fixture"] == "synthetic-context-v1"
    assert report["abstained"] is False
    assert report["evidence_count"] == 1
    assert report["evidence"][0]["source"] == "crm"
    assert report["evidence"][0]["external_id"] == "synthetic-1"
    assert report["evidence"][0]["fields"] == {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "company": "Analytical Engines",
    }


def test_demo_reports_abstention_and_does_not_publish_private_attributes() -> None:
    report = demo_report()
    assert report["missing_query_abstained"] is True
    assert report["tenant_b_visible"] is False
    assert report["partner_visible"] is False
    assert "secret" not in str(report).lower()
    assert "phone" not in str(report).lower()
    assert "email" not in str(report).lower()
