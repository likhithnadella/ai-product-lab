import pytest

from app.models import IntakeRecord
from app.search import search_records


def row(key: str, **fields: str) -> IntakeRecord:
    return IntakeRecord(source="crm", external_id=key, **fields)


SCOPE = frozenset({"crm"})


def test_accent_insensitive_name_matching() -> None:
    hits = search_records([row("1", first_name="José")], "Jose", allowed_sources=SCOPE)
    assert [h.record.external_id for h in hits] == ["1"]


def test_normalized_company_matching() -> None:
    hits = search_records([row("1", company="Café")], "cafe", allowed_sources=SCOPE)
    assert [h.record.external_id for h in hits] == ["1"]


def test_phone_last_seven_digits_match() -> None:
    hits = search_records([row("1", phone="(214) 555-1212")], "5551212", allowed_sources=SCOPE)
    assert [h.record.external_id for h in hits] == ["1"]
    assert "phone" in hits[0].matched_fields


def test_short_phone_fragment_does_not_match() -> None:
    assert search_records([row("1", phone="2145551212")], "1212", allowed_sources=SCOPE) == []


def test_exact_field_boost_breaks_lexical_tie() -> None:
    hits = search_records(
        [row("a", first_name="Asha", company="Asha North"), row("b", first_name="Asha", company="Asha North")],
        "Asha",
        allowed_sources=SCOPE,
    )
    assert [h.record.external_id for h in hits] == ["a", "b"]
    assert hits[0].score == hits[1].score


def test_match_explanation_names_matched_fields() -> None:
    hits = search_records(
        [row("1", first_name="Asha", company="Northstar")],
        "asha northstar",
        allowed_sources=SCOPE,
    )
    assert hits[0].matched_fields == ("first_name", "company")


def test_replayed_identity_appears_only_once() -> None:
    hits = search_records(
        [row("1", first_name="Old"), row("1", first_name="New")],
        "new",
        allowed_sources=SCOPE,
    )
    assert [h.record.first_name for h in hits] == ["New"]


def test_latest_replay_replaces_old_search_terms() -> None:
    hits = search_records(
        [row("1", first_name="Old"), row("1", first_name="New")],
        "old",
        allowed_sources=SCOPE,
    )
    assert hits == []


def test_query_length_is_bounded() -> None:
    with pytest.raises(ValueError, match="256"):
        search_records([], "a" * 257, allowed_sources=SCOPE)


def test_distinct_query_terms_are_bounded() -> None:
    query = " ".join(f"term{i}" for i in range(17))
    with pytest.raises(ValueError, match="16"):
        search_records([], query, allowed_sources=SCOPE)


def test_pagination_has_stable_nonoverlapping_pages() -> None:
    rows = [row(str(i), first_name="Asha") for i in range(5)]
    first = search_records(rows, "asha", allowed_sources=SCOPE, limit=2)
    second = search_records(rows, "asha", allowed_sources=SCOPE, limit=2, offset=2)
    assert [h.record.external_id for h in first + second] == ["0", "1", "2", "3"]


def test_invalid_pagination_offset_is_rejected() -> None:
    with pytest.raises(ValueError, match="offset"):
        search_records([], "asha", allowed_sources=SCOPE, offset=-1)
    with pytest.raises(ValueError, match="offset"):
        search_records([], "asha", allowed_sources=SCOPE, offset=10001)


def test_disallowed_source_cannot_appear_in_results() -> None:
    records = [row("1", first_name="Asha"), IntakeRecord(source="secret", external_id="2", first_name="Asha")]
    hits = search_records(records, "asha", allowed_sources=SCOPE)
    assert [h.record.source for h in hits] == ["crm"]
