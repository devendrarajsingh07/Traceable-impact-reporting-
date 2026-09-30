# Traceable

Traceable turns messy nonprofit program files into defensible, source-linked reports. Raw uploads remain immutable, mappings and duplicate decisions require human confirmation, and every reported number stores the source record IDs that produced it.

![Traceable source-linked report with an interactive metric sunburst](docs/sunburst-desktop.png)

## Why it matters

Small nonprofits often report from disconnected spreadsheets, attendance files, donor records, and survey exports. Traceable reconciles those sources without hiding uncertainty or rewriting history.

- Every reported number links to the exact source records that produced it.
- Raw uploads remain immutable and every decision is recorded in an append-only audit trail.
- Column mappings, duplicate matches, and AI-assisted metric formulas require explicit human confirmation.
- Beneficiary identities are pseudonymized outside the protected raw-record layer.
- Data gaps and unresolved ambiguity remain visible in the final report.

## Core capabilities

- CSV, XLSX, XLS, and JSON ingestion with background processing.
- Human-confirmed fuzzy column reconciliation against a canonical schema.
- Multi-field duplicate detection with explainable similarity evidence.
- Natural-language metric drafting with strict server-side validation and a manual fallback.
- Interactive metric sunburst showing metrics and their contributing source files.
- Source-linked HTML/PDF reports with pseudonymized record drill-downs.
- FastAPI, React, PostgreSQL, and Redis services runnable with one Docker Compose command.

## Run the complete stack

Copy `.env.example` to `.env`, replace the demo secrets, and optionally add an Anthropic API key. Then run:

```powershell
docker compose up --build
```

Open `http://localhost:8080`. The compose stack starts the React frontend, FastAPI backend, and PostgreSQL database. API health is available at `http://localhost:8000/api/health`.

## Demo access

The local defaults are `admin` / `admin-demo` and `viewer` / `viewer-demo`. Change both passwords and `JWT_SECRET` outside a local judging environment. Only the `org_admin` role can access raw identities or create public report snapshots.

## Local development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[test]"
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8010
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Run verification with:

```powershell
pytest
cd frontend
npm run lint
npm run build
```

## Demonstration flow

1. Upload the deliberately inconsistent files in `samples`.
2. Confirm proposed column mappings.
3. Run probabilistic duplicate detection and inspect the field-level evidence.
4. Describe a metric in plain language or use the manual builder, then explicitly confirm it.
5. Select a metric in Evidence lineage to highlight its path from files to source rows.
6. Open the report and export HTML or PDF.

AI assistance is optional. If the provider is unavailable, the manual metric builder keeps working. See [ARCHITECTURE.md](ARCHITECTURE.md) for trust boundaries and scaling decisions.
