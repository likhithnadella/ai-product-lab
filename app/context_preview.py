"""Structured evidence for an offline, tenant-scoped context preview.

This is NOT a prompt, an LLM response, an authentication layer, or a public API.
Only a trusted caller may supply a server-derived TenantPrincipal.
"""

from dataclasses import dataclass

from app.tenant_store import TenantPrincipal, TenantRecordStore

_DISPLAY_FIELDS = ("first_name", "last_name", "company")
_MAX_CONTEXT_HITS = 20


@dataclass(frozen=True)
class ContextEvidence:
    """Provenance plus a deliberately narrow, untrusted data projection."""

    source: str
    external_id: str
    score: int
    matched_fields: tuple[str, ...]
    fields: dict[str, str]


@dataclass(frozen=True)
class ContextPreview:
    """No generated answer: empty evidence means explicit abstention."""

    abstained: bool
    evidence: tuple[ContextEvidence, ...]


def assemble_context(
    store: TenantRecordStore,
    principal: TenantPrincipal,
    query: str,
    *,
    max_hits: int = 5,
) -> ContextPreview:
    """Collect read-authorized lexical hits without invoking a model.

    TenantRecordStore.search enforces tenant and source filtering before
    ranking. Never pass an untrusted or request-body-created principal here.
    The returned field values are untrusted data, NOT safe prompt instructions.
    """
    if (
        isinstance(max_hits, bool)
        or not isinstance(max_hits, int)
        or not 1 <= max_hits <= _MAX_CONTEXT_HITS
    ):
        raise ValueError("max_hits must be an integer between 1 and 20")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a nonblank string")
    if not isinstance(principal, TenantPrincipal):
        raise PermissionError("trusted tenant principal required")

    hits = store.search(principal, query, limit=max_hits)
    evidence = tuple(
        ContextEvidence(
            source=hit.record.source,
            external_id=hit.record.external_id,
            score=hit.score,
            matched_fields=hit.matched_fields,
            fields={
                name: value
                for name in _DISPLAY_FIELDS
                if (value := getattr(hit.record, name)) is not None and value.strip()
            },
        )
        for hit in hits
    )
    return ContextPreview(abstained=not evidence, evidence=evidence)
