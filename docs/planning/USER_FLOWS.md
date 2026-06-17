# USER_FLOWS — Nexus Brain

> `/arch-draft` Phase 4. Every in-scope requirement (Phase 6) maps to a flow here. Posture: production-grade → failure/recovery paths are first-class. Tags: `locked` / `proposed` / `deferred`.

## Cross-cutting locked behaviors
- **F-LCR `[locked]` Long-context-vs-RAG routing:** per-project relevant corpus **< ~200K tokens → cached long-context** (stuff into context behind prompt caching); larger scope / many projects → **agentic RAG** (rewrite → fan-out `search` → retrieve-then-read whole files → graph-trace → synthesize); **graph tools always-on** either way. Latency-sensitive lookups prefer retrieval even if they'd fit.
- **F-GG `[locked — owner 2026-06-15]` Grounding gate = answer-but-flag:** never present an ungrounded claim as cited; **post-validate every cited span exists** in current source; separate and mark "couldn't ground: X" at low confidence; **opt-in strict mode refuses** under insufficient grounding. The 3-layer grounding stack (Contextual Retrieval at index time · native Citations API · the post-validation grounding contract) backs this.

---

### Flow 1 — `setup` (machine bootstrap)
**Actor:** owner. **Trigger:** `nexus setup` (once/machine). **Preconditions:** none.
**Steps:** 1. Detect **CodeGraph** → install via its real channel (brew/cargo/pipx/download) → verify on PATH. 2. Register the Nexus Brain **MCP server** into host configs (`~/.claude.json`, Codex `~/.codex/config.toml`) — **idempotent, reversible, consented**. 3. Register doc **skills** (`layer-docs`, `learn-site`) into `~/.claude/skills` (and `~/.codex/skills` if probe-confirmed). 4. Create central store `~/.project-brain/` + the project **registry**. 5. Prompt for + store API keys (Claude/Voyage) in the **OS keychain**; choose default **privacy posture** + **embedding model**.
**System responsibilities:** every host mutation idempotent + reversible (`setup --uninstall`) + consented; never write secrets to disk.
**Success:** `setup` reports all parts green. **Failure:** missing CodeGraph channel → degraded (code-only-less) + clear remediation; keychain denied → prompt, don't store in plaintext.
**Data:** `~/.project-brain/` registry; keychain refs; host config entries (tracked for reversal).

### Flow 2 — `add <repo>`
**Actor:** owner. **Trigger:** `nexus add <path>`. **Preconditions:** `setup` done.
**Steps:** 1. Init/attach **CodeGraph** index for the repo. 2. **Discover docs** broadly (`**/*.{md,mdx,rst,adoc}`, README/ARCHITECTURE/etc., `.github/**`, OpenAPI/schemas, code-embedded) honoring `.gitignore` + `.brainignore`. 3. **Classify** producer (cc-crew/gstack/CE/human/other) + `doc_type` + owned/foreign/supplemental. 4. **Anchor-aware chunk** (docs: heading-split + late chunking; code: AST via `CodeHierarchyNodeParser` + Contextual Retrieval). 5. **Redact → embed** into the per-project store; stamp `{embedding_model, dim, schema_version, index_built_at, source_root_hash}`. 6. Write **`.project-brain/manifest.json`** (sibling; never edit `.scaffolding/manifest.json`). 7. **Enroll sync** (watcher + git-hook). 8. Register `project_id → db_path + schema_version + model_version` in the router.
**System responsibilities:** **R-PARTIAL** — ingest whatever exists now; never hard-require complete docs; nudge `/layer-docs` but don't block. Surface a "doc completeness" signal.
**Success:** project queryable immediately (code-only if docs thin). **Failure:** partial ingest → temp generation, no half-swapped index; corrupt file → skip + log, don't abort.
**Data:** per-project vector store; manifest; registry row; anchors.

### Flow 3 — `ask` (standalone embedded agent) — THE core flow
**Actor:** owner via standalone chat UI/CLI. **Trigger:** a question (+ optional scope: project/portfolio/file/...).
**Steps:** 1. Resolve scope → estimate corpus size → **F-LCR route**. 2. Retrieve: **hybrid (dense + BM25) → rerank (~30–50→~10) → whole-file hydration**; **graph tools** (`callers/callees/impact/trace`) as needed. 3. **Embedded agent** (Claude API) synthesizes via the retrieval **tools** (same internal core the MCP server exposes). 4. **Grounding gate (F-GG):** validate cited spans; flag unsupported. 5. Attach **provenance packet** (project id, source ids, `file:line`, commit SHAs, session ids, ingested-from SHA, index freshness, confidence, drift markers). 6. Render answer + **evidence chips** + **freshness/staleness banner**.
**Success:** correct, cited, fresh answer. **Failure:** model/API down → degrade to retrieval-only "here's the evidence, no synthesis"; stale anchors → answer marked stale, never silently trusted.
**Data:** read-only over stores + CodeGraph; writes a query/provenance log (local).

### Flow 4 — `ask` (external agent over MCP)
**Actor:** Claude Code / Codex / CI. **Trigger:** MCP tool call (`search`/`get_file`/`graph`/`list_projects`/`status`).
**Steps:** identical retrieval core to Flow 3, but the **MCP server is the trust boundary**: results are **redacted + policy-filtered** before leaving; structured results carry stable IDs + `file:line`; large `search`/`graph` stream. The external model drives its own loop.
**Constraints:** per-project `policy.yaml` honored by `list_projects()`; transport = stdio (default) or loopback-HTTP + token (opt-in).
**Failure:** policy denies a project → omitted from results with a marker, not a hard error.

### Flow 5 — Portfolio / federated query
**Actor:** any ask surface with portfolio scope. **Trigger:** cross-project question.
**Steps:** 1. Router selects target projects (registry). 2. **Fan out, not multiplex** — per-project retrieve + per-repo CodeGraph structural query (read-only WAL or one-shot CLI). 3. **Union + merged global ranking** across per-project result sets. 4. **Cross-repo symbol resolution** via `unresolved_refs.reference_name` + globally-namespaced `qualified_name` — **`research required`**; **fallback:** "N graphs side-by-side" (per-project answers union-ranked) with a clear "cross-repo edges unresolved" marker. 5. Gate on each store's `schema_version`/`model_version`; refuse/flag mismatches.
**Success:** one coherent cross-portfolio answer. **Failure/degrade:** a project's worker cold/evicted → cheap re-attach or skip-with-marker; schema mismatch → exclude + flag.

### Flow 6 — Sync / freshness (background)
**Actor:** sync watcher + git-hooks (non-human). **Trigger:** file change / commit / merge / checkout.
**Steps:** 1. **Watcher** (Watchman "since `<clock-id>`", settles before notifying; fswatch fallback) → **debounce** burst. 2. **git-hooks** (`post-commit/merge/checkout`) = correctness backstop for branch switches/merges. 3. Compute **content-hash delta** (file-hash → which files; chunk-hash → which chunks). 4. Re-embed changed chunks → **tombstone + replace** keyed on `source_path`. 5. CodeGraph self-syncs (~1 s lag). 6. Update freshness stamps.
**System responsibilities:** *watcher = freshness; hooks = guaranteed convergence.* On-demand worker activation + **idle eviction (LRU)** — never N hot watchers.
**Failure:** missed event → next git-hook/`sync` converges; worker crash → idempotent resume from the content-hash manifest.

### Flow 7 — Session ingestion (opt-in)
**Actor:** owner (consent) → ingestion worker. **Trigger:** `sync --sessions` / opt-in per project.
**Steps:** 1. **Consent gate** (per project, stricter than docs/code). 2. Read Claude Code transcripts (Codex after schema validation, `deferred`). 3. **Redact** (secrets/PII) + **exclude `thinking` blocks**; **raw transcripts never embedded**. 4. Summarize → **episode card** (Brain-owned). 5. Embed the card (local model default); **commit-link with confidence**.
**Failure/safety:** redaction high-confidence-unsafe → quarantine the span, don't embed. No consent → skip entirely.

### Flow 8 — Drift detection + owned-doc refresh
**Actor:** drift radar → (allowlisted) owned-doc refresh. **Trigger:** code changed but docs didn't (anchor mismatch) / `status`.
**Steps:** 1. Revalidate anchors vs current code → mark `live|stale|moved|unknown`. 2. Rank by source authority × recency × code-agreement. 3. **Owned** docs → propose `layer-docs` refresh → **preview + consent** → regenerate **with don't-clobber / 3-way-merge** (preserve human edits) → re-embed. 4. **Foreign** docs → flag + offer a "what changed" supplement, **never overwrite**. 5. **Supplemental** → namespaced, marked brain-generated.
**Constraint:** D-USR-1 allowlist. **Integrated:** propose-only via Gateway (no MVP gateway doc-refresh action).
**Failure:** merge conflict → leave doc untouched, surface conflict.

### Flow 9 — Re-embed / model change (blue-green)
**Actor:** index worker. **Trigger:** embedding model/dim change, or schema bump.
**Steps:** 1. Detect via the store stamp: **dim mismatch → hard rebuild**; same-dim/new-model → re-embed (silent quality rot otherwise). 2. **Never update in place** — re-embed to a **new versioned generation** → atomic swap query path → keep old for rollback. 3. Content-hash manifest resumes only missing deltas (idempotent; crash leaves prior generation live).
**Failure:** crash mid-reindex → prior generation still serves; resume deltas.

### Flow 10 — Recovery
**Actor:** workers/router. **Triggers + behavior:** crash mid-reindex → atomic-swap means prior generation live, resume deltas · corrupt store → rebuild from source (the only non-reproducible asset is source files) · CodeGraph daemon down → 300 s idle is normal; reconnect does catch-up sync; one-shot CLI fallback · model API down → retrieval-only degraded answers.

### Flow 11 — *(later, integrated)* Action plan → NexusOps Gateway `[deferred — P2]`
**Actor:** Brain action planner → NexusOps. **Trigger:** a "do X" request when integrated.
**Steps:** retrieve context → emit a frozen **`ActionPlan`** via `submit_action_plan` (`requester_type=project_brain`), each step a catalog `ActionRequest` → platform previews + risk-classifies (0–4) → user approves → platform executes + emits events → Brain indexes resulting evidence. **Brain never executes.** (See `MAIN_PLATFORM_INTERFACE.md` v0.2 §7.)

### Flow 12 — `uninstall` / reset
**Actor:** owner. **Trigger:** `setup --uninstall`. **Steps:** unregister MCP + skills from host configs (reverse Flow 1); optionally purge `~/.project-brain/` + keychain refs, with a "preserve local data" option. **Constraint:** fully reversible; the inverse of every Flow-1 host mutation.

---

## Requirement → Flow coverage check (Phase-4 stop condition)
PB-1 → F2 · PB-2 → F2 · PB-3 → F2/F8 · PB-4 → F3/F4/F5 · PB-5 → F7 · PB-6 → F2/F3 · PB-7 → F2/F8 · PB-8 → F11 · PB-9 → F11 (integrated) · PB-10 → F3/F4 · PB-11 → F1/F7/F8/F12 + cross-cutting. Install/sync/freshness/recovery implied-reqs → F1/F6/F9/F10. **No in-scope requirement is without a flow.**
