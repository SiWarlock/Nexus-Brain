# DATA_MODEL — Nexus Brain

> `/arch-draft` Phase 5 (data plane). The three stores, their schemas, the versioning/freshness model, and the core state machines. Posture: production-grade. Schemas are rough-draft (Brain-1); `/arch-finalize` hardens them. See `DECISIONS.md` D-11..D-15.

## The three stores (fused at query time, never merged)

### ① Vector / retrieval store — **LanceDB** (one dataset per project)
The semantic+lexical memory. Nexus Brain owns + writes it. One **chunk** record:
```
chunk {
  chunk_id            # stable id
  project_id
  source_path         # repo-relative
  doc_or_code         # 'doc' | 'code'
  producer            # cc-crew-layer-docs | gstack | CE | human | other-generated
  doc_type            # architecture | layer | planning | lesson | api | guide | readme | adr | ...
  ownership           # owned | foreign | supplemental
  register            # 'plain' | 'deep'  (dual-register; see RESEARCH §7)
  text                # the chunk text (hydratable)
  vector              # embedding  (dim stamped at store level)
  # FTS/BM25 index is native to the table (hybrid in one store)
  # --- anchor + provenance (the trust spine) ---
  anchor              # file:line or file:line-range  → see Anchor below
  content_hash        # of the source unit
  last_resolved_sha   # git SHA this chunk was last validated against
  ingested_from_sha
  embedding_model_version
  context_blurb       # Contextual-Retrieval 1–2 sentence prefix (code chunks)
  created_at
}
```
**Store-level version stamp** (one per dataset): `{ embedding_model, dimension, schema_version, index_built_at, source_root_hash, ingested_from_sha }`. **Versioning:** every write is a LanceDB version; ingests are **tagged with the repo git SHA**; `restore(version)` rolls back; blue-green re-embed writes a new generation + atomic swap (D-14).

### ② Code graph — **CodeGraph** per-repo SQLite (`.codegraph/codegraph.db`) — *external, read-only to us*
Structural graph; **CodeGraph** owns/writes it, Nexus Brain reads (read-only WAL / one-shot CLI / MCP). Schema (observed, `schema_versions` v4): `nodes`(id, kind, name, qualified_name, file_path, lines, signature, visibility, …) · `edges`(source→target, kind ∈ {contains, calls, imports, instantiates}, line, col, provenance) · `files`(path PK, content_hash, language, …) · `unresolved_refs`(name + candidates — the **cross-repo resolution seam**) · `nodes_fts` (FTS5 over symbol names). We **never write this**; we gate reads on `schema_versions`.

### ③ Catalog — `.project-brain/manifest.json` (per repo) + `~/.project-brain/` registry (global)
**`.project-brain/manifest.json`** (sibling to the read-only `.scaffolding/manifest.json`; project-brain-owned):
```
{ schemaVersion, project_id, source_repo, ingestedFromSha,
  embedding_model, dimension, chunker_version, doc_format_spec_range,
  artifacts: [{ path, content_hash, doc_type, producer, ownership }],
  staleness_pointer, policy_path, lance_version_tag }
```
**Global registry** (`~/.project-brain/registry`): `project_id → { db_path, schema_version, model_version, codegraph_db_path, last_indexed_sha, policy }` — what the **federation router** reads to fan out.

## Core domain objects (PRD §7, aligned)
- **Anchor** `{ anchor_id, project_id, source_file, source_span, target_path, target_line_start, target_line_end, target_symbol, state: live|stale|moved|unknown, last_resolved_sha, confidence }` — the trust primitive; **continuously revalidated** (D-6).
- **Episode Card** (opt-in session memory; Brain-owned) `{ episode_id, session_id, project_id, tool, model, start/end_ts, branch, worktree_path, user_intents, files_touched, key_decisions, errors_fixed, outcome_summary, linked_commits(confidence), privacy_redacted }`. Raw transcripts **never embedded**; `thinking` excluded.
- **Provenance Packet** (per answer) `{ project_ids, source_ids, file:line[], commit_shas, session_ids, ingested_from_sha, index_freshness, confidence_markers, drift_markers, low_confidence_links }`.
- **Evidence Chip / Reference** — standalone-rich; serializes to NexusOps `EvidenceRef` (11-value `EvidenceType`) at the seam.
- **Implementation Plan / Plan Task / Workflow Pack / Workflow Instance** — per PRD §7.5–7.8 (WorkflowInstance = the 12 frozen R-7 states for NexusOps alignment).

## State machines
- **Index generation** (per project, D-14): `building → active → (reembedding → swapped) | degraded | rebuilding`; old generation retained for rollback; crash → prior generation stays `active`.
- **Anchor** (D-6): `live → stale | moved | unknown`; revalidated on sync + at answer time; never silently trusted when not `live`.
- **Project**: `added → indexing → ready ⇄ syncing → drift_detected → reindexing → archived/removed`; per-project worker `cold → warm (on-demand) → idle-evicted (LRU)`.
- **Doc lifecycle** (ownership-gated, D-4 / Flow 8): owned → regenerate+replace (don't-clobber); foreign → re-ingest-on-change, never overwrite, annotate; supplemental → namespaced brain-generated.

## Federation read model (D-2)
Router opens the **N per-project LanceDB datasets read-only** + queries the **N CodeGraph DBs** (read-only WAL / CLI), **union-ranks** per-project result sets into one global ranking; cross-repo symbol resolution via `unresolved_refs.reference_name` + globally-namespaced `qualified_name` (**`research required`**; fallback = side-by-side, marked). Gate every store on `schema_version`/`model_version`; refuse/flag mismatches. **Never one giant index; never N hot watchers** (on-demand + idle eviction).

## Reproducibility & integrity invariants
1. `source files + embedding-model-version stamp → deterministically reproduce the index` (the index is a derived cache).
2. **No in-place re-embed** — always a new versioned generation + atomic swap (reverse order reproduces the silent-quality-rot failure).
3. **Mixed embedding models/dims in one store is forbidden** (dim mismatch → hard rebuild; same-dim/new-model → re-embed).
4. **Redaction-before-embed has no holes** (D-15); secrets only as keychain refs.
5. Every answer is **grounded at a known SHA**; staleness is always surfaced (D-6).
