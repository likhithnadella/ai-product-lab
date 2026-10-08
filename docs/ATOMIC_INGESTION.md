# Atomic ingestion within one process

A source record is identified by `(source, external_id)`. Retried delivery must not report a second creation, even when requests arrive simultaneously. The first in-memory implementation classified a record with `get` and wrote it with `put`, leaving a gap where two threads could both observe a missing key.

`InMemoryRecordStore.upsert` now classifies and applies one record while holding a single `threading.Lock`. The ingestion service calls this operation instead of composing separate reads and writes. This keeps the domain-level `created`, `updated`, and `unchanged` outcomes consistent with the store's state for concurrent requests in **one Python process**.

The regression tests synchronize concurrent callers with a barrier. For identical replayed input, exactly one caller should report `created`; the others report `unchanged`. A separate test verifies that equal external IDs from different sources remain independent.

This is not a database transaction. Batches still apply one item at a time; they can partially succeed. A process restart loses the records, and two worker processes do not share a lock or state. Concurrent updates with *different* payloads are serialized but follow last-writer-wins semantics, not optimistic version checking. The lock also does not establish a throughput or latency benchmark.

The next durable repository should enforce `(source, external_id)` uniqueness in Postgres and classify upserts transactionally, with tests that exercise actual concurrent database connections. Measure contention and p95 latency before introducing queues, partitioning, or other infrastructure.
