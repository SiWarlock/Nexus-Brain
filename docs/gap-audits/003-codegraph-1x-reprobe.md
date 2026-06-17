Both authoritative fetches confirm the decisive point: `codegraph_trace` and `codegraph_context` were **removed entirely in 0.9.9** (folded into `codegraph_explore`), upgrading the probe's [likely] to [VERIFIED]. The fact that this environment's MCP server still advertises those two tool names is a stale local install — not the v1.x surface. I have everything I need.

---

# DECISION MEMO — @colbymchenry/codegraph 1.x → Nexus Brain

**Date:** 2026-06-16 · **Decision lead:** (you) · **Recency of evidence:** npm/GitHub pulled 2026-06-16; latest release v1.0.1 (2026-06-13).
**Bottom line up front:** **Pin to `=1.0.1`, abstract behind a `CodeGraphPort`, keep tree-sitter fallback. KEEP-OUR-ROUTER (HYBRID-lean). The direct-SQLite read path survives intact; the MCP tool surface is the only thing that breaks, and the break is recoverable.**

---

## 1. Current version + exact breaking changes + which Nexus-Brain assumptions break

**Current version: `1.0.1`** (published 2026-06-13; `1.0.0` on 2026-06-12). [VERIFIED] — npm `dist-tags.latest=1.0.1`. Source: `https://registry.npmjs.org/@colbymchenry/codegraph`

### A. Direct-SQLite reads (D-12) — **DO NOT BREAK** [VERIFIED]
All five tables Nexus Brain reads survive 0.9.7→1.0.1: `nodes`, `edges`, `unresolved_refs`, `files`, `schema_versions` (plus `nodes_fts` FTS5 + sync triggers). `schema_versions` is **still version 1** — no migration gate. Source: `https://raw.githubusercontent.com/colbymchenry/codegraph/main/src/db/schema.sql`

Three caveats that DO require action:
- **Table is `nodes`, not `symbols`.** README marketing prose says "symbols"; the physical table is `nodes`. A reader must query `nodes`. [VERIFIED] (`.../main/CLAUDE.md`)
- **`CODEGRAPH_DIR` can move the DB off `.codegraph/`.** A hardcoded `.codegraph/codegraph.db` path breaks if that env var is set. [VERIFIED] (v1.0.0 notes)
- **Edge/node CONTENTS changed even though columns didn't** (v1.0.1): static TS/JS method calls now resolve to the method node not the class; worktrees no longer double-indexed. A direct reader sees different graph results. [VERIFIED] (`.../releases/tag/v1.0.1`)
- **[research-required]:** diff the *exact 0.9.7 column set* of your live DB against today's `schema.sql` to rule out silent column drift before trusting blindly. Cheap, do it once.

### B. The 8→4 MCP tool surface — **THIS is the break** [VERIFIED]
- **Default `tools/list` now returns 4:** `codegraph_explore`, `codegraph_node`, `codegraph_search`, `codegraph_callers`. Auto-discovery that expected 8 breaks. **Fix:** set `CODEGRAPH_MCP_TOOLS`, or call the hidden 4 by exact name.
- The other 4 — `codegraph_callees`, `codegraph_impact`, `codegraph_files`, `codegraph_status` — are **hidden-by-default but fully functional.** Coverage for callers/callees/impact/search/files/status is **intact.**
- **Highest-severity break — `codegraph_trace` and `codegraph_context` are GONE.** Now upgraded from [likely] to **[VERIFIED]**: both removed entirely in **v0.9.9** (folded into `codegraph_explore`), not in 1.0. Changelog: *"The narrower `codegraph_context` and `codegraph_trace` tools were removed in favor of it — explore already surfaces the call flow."* Source: `https://raw.githubusercontent.com/colbymchenry/codegraph/main/CHANGELOG.md`
  - **Trap to flag:** this very workspace's MCP server still advertises `codegraph_trace`/`codegraph_context` in its instructions — that is a **stale local install predating 0.9.9**, not the v1.x surface. Any Nexus-Brain code naming those two tools must migrate onto `codegraph_explore`.
- **Config file:** removed at **0.9.2**, not 1.0 — a 0.9.7 consumer already ran configless. No new break here. [VERIFIED]
- **CLI is fully headless** and *gained* `explore`/`node` non-MCP subcommands in 1.0.0 — a clean shell-out path that sidesteps the whole MCP `tools/list` gating problem. [VERIFIED]

### Assumptions that break
| Nexus-Brain assumption | Status |
|---|---|
| Direct reads of the 5 tables work | **HOLDS** [VERIFIED] |
| MCP exposes 8 tools incl. `trace`/`context` | **BREAKS** [VERIFIED] — 4 default; trace/context deleted since 0.9.9 |
| `.codegraph/codegraph.db` path is fixed | **WEAKENS** [VERIFIED] — `CODEGRAPH_DIR` overrides |
| "No native cross-repo" premise | **PARTIALLY OBSOLETE** [VERIFIED] — see §2 |

---

## 2. Does native multi-repo SUBSUME our federation router? → **KEEP-OUR-ROUTER (HYBRID-lean)**

**Decision: KEEP-OUR-ROUTER.** Native workspace indexing does **not** subsume the federation router. Adopt it tactically as a same-root co-indexing convenience (the HYBRID lean), but build the router.

**Why — what v1.0 workspace indexing actually is** [VERIFIED]: `codegraph init` at a parent dir indexes all nested repos **into ONE graph / ONE `.codegraph/codegraph.db`** at the root, file_path-disambiguated, no `repo_id` partition column. It is an **index-time scope change over a fixed nested physical layout**, not a query-time federation API.

**Why it does NOT subsume the router** [VERIFIED + likely]:
1. **No query-time fan-out** over already-separate per-repo indexes in arbitrary locations. Combination happens only if you physically nest repos under one root and re-init. [VERIFIED]
2. **No cross-repo UNION + ranking/fusion** operator — no repo-aware scoping arg, no cross-repo ranking knob. [VERIFIED]
3. **No reliable precise cross-repo resolution.** Cross-repo links rest on heuristic **name-matching**, not import-accurate edges — precise import resolution depends on per-toolchain config (tsconfig aliases / cargo workspace members) that does **not** span independent git repos. Release notes never claim cross-repo import-edge resolution. [likely] (`.../core-concepts/resolution.md`)
4. **No new cross-repo MCP/CLI command** was added — the surface was *cut* 8→4. [VERIFIED]

**Why not LEAN-NATIVE:** it would force a single physical nesting of every repo, give you one monolithic DB with no per-repo scoping, and rest cross-repo answers on name-matching — losing exactly the ranking/fusion and trustworthy cross-repo edges the router exists to provide.

**The HYBRID lean:** where repos *already* live under one root, let native workspace co-indexing produce a combined graph and have the router treat it as one source — cheaper than N indexes. Everywhere else, the router fans out over independent `.codegraph` DBs and does the union/ranking. **The premise wording must change** from "no native cross-repo" to *"naive single-graph co-indexing exists for same-root nesting; no federation, no precise cross-repo resolution."*

---

## 3. Coupling posture + the exact pin

**Posture: PIN HARD + ABSTRACT behind `CodeGraphPort` + TREE-SITTER FALLBACK. DEFER vendoring.** This is driven by maintenance risk, not license — it's **MIT** (all versions, [VERIFIED]), so vendor/fork/wrap is legally free. The risk is **bus-factor 1** (colbymchenry 438 commits, next human 16; no SECURITY/GOVERNANCE/CODEOWNERS/funding) and **two consumer-surface breaks in ~10 days** (0.9.9 killed trace/context; 1.0.0 cut tools 8→4 + removed config). 100+ commits/month, code changing the day of this probe. [VERIFIED]

1. **Pin exactly:** set `"@colbymchenry/codegraph": "1.0.1"` — **exact, not `^1.0.1` and not `~1.0.1`.** Gate any bump behind an integration test. A caret range would have silently pulled the 0.9.9 trace/context removal.
2. **`CodeGraphPort` adapter** — route **every** access (the 5-table SQLite reads AND all MCP/CLI calls) through one interface. Both coupling points already broke; the adapter localizes the next break to one file. **Check `schema_versions` at startup, fail fast on unexpected version. Read the DB path from `CODEGRAPH_DIR` (default `.codegraph`), never hardcode.** Prefer the **CLI shell-out** (`codegraph explore/node/callers/...`) over MCP inside the adapter to dodge `tools/list` gating entirely.
3. **Tree-sitter fallback behind the same port** — non-negotiable at bus-factor 1; the disaster-recovery path that degrades gracefully instead of hard-failing Nexus Brain.
4. **Defer full vendoring** — MIT allows it, but a 100-commits/month fork is a maintenance tax with no payoff today. Trigger vendoring only on abandonment or a needed divergent fix.

**Exact pin to set:** `=1.0.1`.

---

## 4. Concrete doc edits

> Anchors (D-2, D-12, D-24, A-5) are referenced from the brief; I could not open the live DECISIONS/ASSUMPTIONS/ARCHITECTURE_DRAFT files (not provided in this task). Apply the edits to whichever lines carry these IDs. [research-required: confirm anchor line numbers in the live docs.]

**DECISIONS**
- **D-12 (direct-SQLite reads):** Update — "Reads 5 tables `nodes`/`edges`/`unresolved_refs`/`files`/`schema_versions` from per-repo `.codegraph/codegraph.db`. **[VERIFIED 2026-06-16] schema survives 0.9.7→1.0.1, `schema_versions`=1, no migration. MUST: query `nodes` (not `symbols`); resolve DB path via `CODEGRAPH_DIR` (default `.codegraph`); assert `schema_versions` at startup and fail fast. [research-required] diff exact 0.9.7 column set vs current `schema.sql`.**"
- **D-2 (CodeGraph dependency / pin):** Change the pin from `0.9.7` → **`=1.0.1` (exact)**. Add: *"Coupling = PIN + `CodeGraphPort` adapter + tree-sitter fallback; vendoring deferred; license MIT [VERIFIED]; bus-factor 1, gate every bump behind integration test."*
- **D-24 (federation router):** Reaffirm **KEEP-OUR-ROUTER (HYBRID-lean)**. Add: *"Native v1.0 workspace indexing is single-DB, same-root, index-time, name-match only — no query-time fan-out, no union/ranking, no precise cross-repo edges; does NOT subsume the router. [VERIFIED 2026-06-16]. Tactically reuse native co-indexing for already-nested repos."*
- **NEW decision (tool surface):** *"Migrate all `codegraph_trace`/`codegraph_context` calls onto `codegraph_explore` (removed in 0.9.9 [VERIFIED]); access `callees`/`impact`/`files`/`status` via `CODEGRAPH_MCP_TOOLS` or exact-name/CLI; prefer CLI shell-out over MCP `tools/list`."*

**ASSUMPTIONS**
- **A-5 ("no native cross-repo" [VERIFIED] premise):** **Downgrade/rewrite.** Old wording is now false. New: *"[VERIFIED 2026-06-16] Native single-graph co-indexing exists for same-root nested repos (v1.0.0); there is NO native federation across separately-initialized `.codegraph` DBs and NO precise cross-repo resolution (heuristic name-matching only). Router still required."*
- Add **A-new:** *"CodeGraph MCP default surface = 4 tools; trace/context deleted; DB path overridable via `CODEGRAPH_DIR`. [VERIFIED]"*

**ARCHITECTURE_DRAFT**
- Insert the **`CodeGraphPort`** abstraction (single adapter; SQLite reads + CLI/MCP calls; startup `schema_versions` assertion; `CODEGRAPH_DIR`-aware path) and the **tree-sitter fallback** behind it.
- Update the federation-router section to the **HYBRID** model: native co-indexing as one source for same-root repos; router fan-out + union/ranking for independent DBs.
- Replace any `codegraph_trace`/`codegraph_context` references in dataflow diagrams with `codegraph_explore`.

---

### Sources
- npm registry / dist-tags / downloads: `https://registry.npmjs.org/@colbymchenry/codegraph` [VERIFIED]
- Schema: `https://raw.githubusercontent.com/colbymchenry/codegraph/main/src/db/schema.sql` [VERIFIED]
- CHANGELOG (trace/context removed 0.9.9; 8→4; config removed; workspace indexing): `https://raw.githubusercontent.com/colbymchenry/codegraph/main/CHANGELOG.md` [VERIFIED — fetched 2026-06-16]
- Releases v1.0.0 / v1.0.1: `https://github.com/colbymchenry/codegraph/releases/tag/v1.0.0`, `.../v1.0.1` [VERIFIED]
- Multi-repo issue #514: `https://github.com/colbymchenry/codegraph/issues/514` [VERIFIED]
- Resolution semantics (name-match vs import): `https://raw.githubusercontent.com/colbymchenry/codegraph/main/site/src/content/docs/core-concepts/resolution.md` [likely]
- License/maintenance: `https://api.github.com/repos/colbymchenry/codegraph/contributors`, `.../package.json` [VERIFIED]
- Stale doc lag: `https://deepwiki.com/colbymchenry/codegraph` + Context7 still show pre-1.0 per-project model — **do not rely on them.** [VERIFIED stale]