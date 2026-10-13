# Search-quality hardening

The lexical baseline now handles several ordinary lookup failures without introducing a model or index: Unicode accent folding, canonical phone suffix lookup (seven or more digits), a small exact-field ranking boost, and matched-field explanations. Search also collapses repeated source identities using the last supplied record, validates query complexity, and supports stable offset-based pagination. These are deliberately deterministic rules; each can be tested without an LLM.

The authorization boundary is unchanged: `allowed_sources` must be derived from trusted permissions, and source scoping is **not** tenant isolation or record-level access control. The function is internal; no public search endpoint has been added.

Important limits: the last-record-wins rule assumes input order reflects ingestion order, which a future persistent store must define explicitly. Phone suffix matching can be ambiguous and should not be used for identity resolution. Accent folding can merge distinct spellings, so it is a search convenience, not a canonical data rewrite. Offset pagination is stable only for an unchanged snapshot; a database-backed cursor should replace it if concurrent updates cause inconsistent pages. Query bounds limit work per query but this remains a linear scan. Matched-field explanations are ranking diagnostics, not evidence of entity identity.

The regression suite covers each behavior using synthetic records. It does not establish search relevance on real user queries or production latency. Next: build a judged query set, add tenant/record authorization, and benchmark Postgres full-text search before introducing vector retrieval.
