# Supabase – Configuration & Status Guide

_Last updated: 2025-04-26_

This document distills everything we currently know about the **Psychic-Source** Supabase setup
as pulled via the MCP Supabase tools.  It also shows the exact calls you can run to keep the
snapshot fresh.

---

## 1. Organisations

| Org ID | Name |
|--------|------|
| `uwepbiebgoemadvkikil` | AI-Augmented-Organization |
| `htsxylhbauhgjozuexuq` | PowerShift® Intelligence |

The production project lives in the **PowerShift® Intelligence** organisation.

---

## 2. Projects

| Project | Project ID | Org | Region | Status | DB Host |
|---------|------------|-----|--------|--------|---------|
| Psychic Source Agent (prod) | `elrjsmvfkiyvzbspwxxf` | htsxyl… | `ca-central-1` | **ACTIVE_HEALTHY** | `db.elrjsmvfkiyvzbspwxxf.supabase.co` |
| PowerShift® Intelligence Services (staging) | `fltpxjluzcmwcmgsornr` | htsxyl… | `us-east-2` | ACTIVE_HEALTHY | `db.fltpxjluzcmwcmgsornr.supabase.co` |
| n8n Automation (internal) | `itxyzlxfzxhubaqpnmch` | uwepbi… | `us-east-1` | ACTIVE_HEALTHY | `db.itxyzlxfzxhubaqpnmch.supabase.co` |
| … | … | … | … | … | … |

⚠️  All application code in this repo points at **`elrjsmvfkiyvzbspwxxf`** unless overridden by
env vars.

---

## 3. Key Schemas & Tables (Psychic Source Agent)

Pulled via `mcp_supabase_list_tables(project_id="elrjsmvfkiyvzbspwxxf")`.

| Table | Row Estimate | Purpose |
|-------|--------------|---------|
| `conversations` | 1 950 | One row per call; cost + summary + embedding columns included |
| `messages` | 16 684 | All individual turns linked to `conversation_id` |
| `agents` | 2 | Registry of Lilly agent configs (`agent_id`, `voice_id`, `status`) |
| `conversation_embeddings` | 1 285 | Vector store for RAG search; `embedding` (`vector`) + metadata |
| `alembic_version` | 1 | Tracks Alembic migration head |

Schema notes:
* **RLS disabled** on all core tables – API keys grant full access.
* `conversations.embedding` and `conversation_embeddings.embedding` use the `vector` extension.
* `cost_credits` is integer; `duration_seconds` nullable but populated by sync task.

---

## 4. Extensions Enabled

From `mcp_supabase_list_extensions` (only installed ones shown):

`vector`, `pgjwt`, `pg_graphql`, `pg_stat_monitor`, `pgcrypto`, `pg_stat_statements`,
`pg_cron`, `timescaledb`, `pgsodium`, `pgmq`, … (full list in raw output).

Key highlights:
* **`vector` 0.8.0** – IVFFlat + HNSW; used for semantic search.
* **`pgjwt` 0.2.0** – signed JWT creation for vault-less auth.
* **`pg_graphql` 1.5.11** – GraphQL endpoint auto-generated over public schema.
* **`pg_stat_monitor`** – advanced query stats; handy for slow-query analysis.

---

## 5. Migrations & Functions

* Alembic manages schema – head stored in `alembic_version`.
* Supabase system table `supabase_migrations.schema_migrations` does **not** exist (tooling quirk).
* Custom RPC functions we rely on:
  * `get_message_activity_in_range(start_date, end_date, agent_id)` – dashboard analytics.
  * `execute_sql(sql text)` – ad-hoc query runner (called by `/api/sql-query`).

---

## 6. How to Re-Query This Snapshot

```python
orgs    = mcp_supabase_list_organizations()
projs   = mcp_supabase_list_projects()
# Pick project_id for Psychic Source Agent
schema  = mcp_supabase_list_tables(project_id="elrjsmvfkiyvzbspwxxf")
exts    = mcp_supabase_list_extensions(project_id="elrjsmvfkiyvzbspwxxf")
```

Add helper wrappers in `tools/supabase_client.py` to fetch:
* `get_table_row_counts()` → quick health metric
* `get_extension_versions()` → monitor upgrades

---

## 7. Automation Checklist

- [ ] Create `/api/supabase-status` route that returns org → projects → schema summary as JSON.
- [ ] Show DB row counts & creds usage on Admin Panel.
- [ ] Alert (Slack/Webhook) if project status ≠ `ACTIVE_HEALTHY`.
- [ ] Nightly job: store snapshot in `docs/history/` for audit trail.

---

### Related Code Paths
* `app/services/supabase_conversation_service.py` – primary data access.
* `scripts/bulk_import.py` – initial loader via supabase-py.
* `supabase/functions/get_message_activity_in_range.sql` – analytics RPC. 