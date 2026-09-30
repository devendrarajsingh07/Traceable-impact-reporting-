# Impact Ledger architecture

## Request and data layers

The backend follows a one-way dependency flow:

```text
FastAPI routers → domain services → repositories → SQLAlchemy models → PostgreSQL
```

Routers validate HTTP input and translate domain errors into status codes. Services own ingestion, reconciliation, record linkage, metric computation, anonymization, report assembly, and audit decisions. Repositories contain queries and persistence operations. Models define storage and enforce immutability for `raw_uploads`, `raw_records`, and `transform_log` with SQLAlchemy event guards.

Uploads and record-linkage scans return `202 Accepted` with a persisted job ID. FastAPI `BackgroundTasks` runs the work for a low-operations deployment, and `/api/jobs/{id}` exposes progress. The service boundary allows a Celery/RQ worker to replace this adapter without changing the API or domain logic. PostgreSQL is used by Docker Compose; a separate local SQLite file remains available for lightweight development.

## Trust and lineage model

Every source row receives an immutable UUID and retains its original JSON. A confirmed mapping is a separate record, never an edit. Duplicate candidates contain a model probability, per-field similarities, model version, and threshold. Reviewer outcomes remain separate labeled feedback records and append an audit event; no candidate is auto-merged.

Metric definitions store a human-readable formula specification. A computation stores its value, exact source-record UUID list, caveats, and timestamp. The lineage endpoint joins four node classes:

```text
raw upload → confirmed mapping → reviewed record set → computed metric
```

Selecting a metric in the UI highlights its upstream evidence path. Reports expose pseudonyms and non-sensitive canonical fields only. Raw identities are encrypted in a separate table and require an `org_admin` JWT. Program-and-location segments below the configured k-anonymity threshold are suppressed.

## AI assistance boundary

The Anthropic call receives only the current confirmed canonical schema, allowed operations, and the user's metric description. It must return strict JSON. The server validates the operation and every referenced field against the live schema before returning a suggestion.

An AI suggestion is never a metric definition. It remains a draft until the user selects Confirm, which calls the normal metric-definition endpoint. Edited and unchanged confirmations are identified separately in `transform_log`. Provider errors return a structured manual-fallback response, and the manual builder has no dependency on AI availability.

## Reporting and sharing

HTML and PDF exporters use the same report object as the UI, including metrics, source drill-downs, caveats, data gaps, and lineage. A public link is a random-token lookup for an immutable, pseudonymized report snapshot. The database stores only a SHA-256 digest of the token. Creating a link requires `org_admin`; reading the frozen shared report requires only the unguessable link.

## Scaling path

PostgreSQL removes SQLite's single-writer limitation. Candidate generation uses sorted-neighborhood blocking before probabilistic Fellegi–Sunter classification instead of comparing every pair. For sustained high-volume deployments, the existing background-job adapter can move to Redis-backed workers, file bytes can move to object storage, and blocking keys can be partitioned without changing record IDs or report lineage.
