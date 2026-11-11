"""Versioned, entirely synthetic retrieval relevance judgments (issue #9).

Judgments reflect exact intended record identities, not implementation scores.
All names, organizations, phone numbers and example.test addresses are fabricated.
"""

from app.models import IntakeRecord
from evals.retrieval import RetrievalCase

VERSION = "2026-11-11-v1"

RECORDS = [
    IntakeRecord(source="crm", external_id="c01", first_name="Mira", last_name="Sen", company="Northstar Demo", email="mira@northstar.example.test", phone="2025550101"),
    IntakeRecord(source="crm", external_id="c02", first_name="Jon", last_name="Vale", company="Northstar Demo", email="jon@northstar.example.test", phone="2025550102"),
    IntakeRecord(source="crm", external_id="c03", first_name="Mira", last_name="Lee", company="Bluebird Demo", email="mira@bluebird.example.test", phone="2025550103"),
    IntakeRecord(source="erp", external_id="e01", first_name="Mira", last_name="Sen", company="Northstar Demo", email="mira@northstar.example.test", phone="2025550101"),
    IntakeRecord(source="erp", external_id="e02", first_name="Asha", last_name="Rao", company="Bluebird Demo", email="asha@bluebird.example.test", phone="2025550104"),
    IntakeRecord(source="support", external_id="s01", first_name="Jon", last_name="Vale", company="Northstar Demo", phone="2025550102"),
    IntakeRecord(source="support", external_id="s02", first_name="Tariq", last_name="Omar", company="Cedar Demo", email="tariq@cedar.example.test"),
    IntakeRecord(source="crm", external_id="c04", first_name="Tariq", last_name="Omar", company="Cedar Demo"),
]

ALL = frozenset({"crm", "erp", "support"})
CRM = frozenset({"crm"})
ERP = frozenset({"erp"})
SUPPORT = frozenset({"support"})


def case(query: str, scope: frozenset[str], *keys: tuple[str, str]) -> RetrievalCase:
    return RetrievalCase(query=query, allowed_sources=scope, relevant_keys=frozenset(keys))


CASES = [
    case("mira@northstar.example.test", ALL, ("crm", "c01"), ("erp", "e01")),
    case("mira@northstar.example.test", CRM, ("crm", "c01")),
    case("mira@northstar.example.test", ERP, ("erp", "e01")),
    case("Mira Sen", ALL, ("crm", "c01"), ("erp", "e01")),
    case("Mira Lee", CRM, ("crm", "c03")),
    case("Jon Vale", ALL, ("crm", "c02"), ("support", "s01")),
    case("Jon Vale", SUPPORT, ("support", "s01")),
    case("Asha Rao", ERP, ("erp", "e02")),
    case("Tariq Omar", ALL, ("crm", "c04"), ("support", "s02")),
    case("Tariq Omar", CRM, ("crm", "c04")),
    case("tariq@cedar.example.test", SUPPORT, ("support", "s02")),
    case("2025550101", ALL, ("crm", "c01"), ("erp", "e01")),
    case("2025550102", CRM, ("crm", "c02")),
    case("2025550104", ERP, ("erp", "e02")),
    case("Northstar Demo", ALL, ("crm", "c01"), ("crm", "c02"), ("erp", "e01"), ("support", "s01")),
    case("Bluebird Demo", ALL, ("crm", "c03"), ("erp", "e02")),
    case("Cedar Demo", SUPPORT, ("support", "s02")),
    case("nonexistent person", ALL),
    case("nobody@missing.example.test", ALL),
    case("9999999999", ALL),
    case("Mira Sen", SUPPORT),
    case("Asha Rao", CRM),
    case("Jon Vale", ERP),
    case("tariq@cedar.example.test", CRM),
    case("Northstar Demo", frozenset()),
]
