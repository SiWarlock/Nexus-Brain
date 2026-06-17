# CodeGraph Cold-Diff Probe — Phase-0 Spike 0.2 (O-CG-COLDIFF)

**Date:** 2026-06-17  
**Investigator:** orchestrator spike agent  
**Scope:** Retire unknowns about `@colbymchenry/codegraph@1.0.1` before Phase-1.4 `CodeGraphPort` contract freeze.

---

## Verdict

**Pinning `@colbymchenry/codegraph@1.0.1` is SAFE with one caveat:** the live store was written by daemon v0.9.7 but already has schema_version 5 applied (v5 is the only 1.0.1-exclusive migration). The schema is fully forward-compatible. The installed CLI (0.9.7) must be upgraded to 1.0.1 to expose the `explore` and `node` commands that the `CodeGraphPort` contract requires. The "search" kind maps to the CLI `query` command (not a `search` command) and to the MCP tool `codegraph_search`.

---

## 1. Live Store Schema

**Location:** `.codegraph/codegraph.db` in project root  
**Daemon version:** 0.9.7 (running, PID 60386)  
**DB backend:** node:sqlite WAL mode  
**CODEGRAPH_DIR:** default `.codegraph` (env var not set)

### Tables (4 core + 1 metadata + 1 versioning + FTS virtual tables)

| Table | Purpose |
|---|---|
| `nodes` | Symbol nodes (21 columns) |
| `edges` | Directed relationships between nodes |
| `files` | Tracked file records |
| `unresolved_refs` | Unresolved cross-file references |
| `project_metadata` | Key-value store (key, value, updated_at) |
| `schema_versions` | Migration history (version, applied_at, description) |
| `nodes_fts` | FTS5 virtual table over nodes |
| `nodes_fts_data/idx/docsize/config` | FTS5 backing tables |

### `nodes` columns (21 total, including v5 addition)

```
id TEXT PK, kind TEXT NOT NULL, name TEXT NOT NULL, qualified_name TEXT NOT NULL,
file_path TEXT NOT NULL, language TEXT NOT NULL, start_line INTEGER NOT NULL,
end_line INTEGER NOT NULL, start_column INTEGER NOT NULL, end_column INTEGER NOT NULL,
docstring TEXT, signature TEXT, visibility TEXT,
is_exported INTEGER DEFAULT 0, is_async INTEGER DEFAULT 0,
is_static INTEGER DEFAULT 0, is_abstract INTEGER DEFAULT 0,
decorators TEXT (JSON array), type_parameters TEXT (JSON array),
updated_at INTEGER NOT NULL,
return_type TEXT  ← added in schema_version 5
```

### `edges` columns (8)

```
id INTEGER PK AUTOINCREMENT, source TEXT NOT NULL, target TEXT NOT NULL,
kind TEXT NOT NULL, metadata TEXT (JSON), line INTEGER, col INTEGER,
provenance TEXT DEFAULT NULL
```

### `files` columns (8)

```
path TEXT PK, content_hash TEXT NOT NULL, language TEXT NOT NULL,
size INTEGER NOT NULL, modified_at INTEGER NOT NULL, indexed_at INTEGER NOT NULL,
node_count INTEGER DEFAULT 0, errors TEXT (JSON array)
```

### `unresolved_refs` columns (9)

```
id INTEGER PK AUTOINCREMENT, from_node_id TEXT NOT NULL,
reference_name TEXT NOT NULL, reference_kind TEXT NOT NULL,
line INTEGER NOT NULL, col INTEGER NOT NULL,
candidates TEXT (JSON array),
file_path TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT 'unknown'
```

### `schema_versions` rows in live DB

| version | description | applied_at |
|---|---|---|
| 1 | Initial schema | 2026-06-17 02:47:47 |
| 4 | Initial schema includes all migrations | 2026-06-17 02:47:47 |
| 5 | Add nodes.return_type — normalized return/result type for receiver-type inference (C++ singletons/factories, #645) | 2026-06-17 15:39:01 |

> Note: The daemon is running v0.9.7, yet schema_version 5 is present. This means 1.0.1's migration was applied to the live DB by the MCP server at some point today (15:39), possibly from a prior install attempt. The live schema IS the 1.0.1 schema.

### Index state

```
Files: 0, Nodes: 0, Edges: 0 (daemon started but indexing not yet complete for this repo)
```

---

## 2. Target Schema (1.0.1)

**Obtained via:** `npm pack @colbymchenry/codegraph@1.0.1` + TypeScript `.d.ts` inspection  
**CURRENT_SCHEMA_VERSION:** `5` (confirmed in `dist/db/migrations.d.ts`)  
**Migrations in 1.0.1:** versions 1 through 5 (applied atomically at init as "Initial schema includes all migrations" for new DBs, then v5 individually if upgrading)

The 1.0.1 schema is **identical** to the live store schema described above — the live DB has already had v5 applied.

**Note:** The binary distributes as a per-platform self-contained bundle downloaded from GitHub Releases. The npm package itself only ships `.d.ts` files and a thin JS shim (`npm-shim.js`). No raw `schema.sql` file is bundled — schema is embedded in the compiled binary. Schema was reconstructed from type definitions + live DB PRAGMA.

---

## 3. Column Diff (0.9.7 vs 1.0.1)

| Table | Column | Change |
|---|---|---|
| `nodes` | `return_type TEXT` | **ADDED** in schema_version 5 (1.0.1 only) |

All other columns are identical between 0.9.7 (schema_version 4) and 1.0.1 (schema_version 5).

**Expectation vs reality:**  
The IMPLEMENTATION_PLAN states "5-table schema + schema_versions=1". The actual schema has:
- **5 core user tables** (nodes, edges, files, unresolved_refs, project_metadata) ✓
- **1 versioning table** (schema_versions) — max version is **5**, not 1
- **5 FTS auxiliary tables** (nodes_fts + 4 backing tables)
- `schema_versions` has 3 rows (versions 1, 4, 5), not a single row with value 1

The "schema_versions=1" expectation in the plan is incorrect. The `CodeGraphPort` must assert `MAX(version) >= 5` (or `version = 5`), not `version = 1`.

---

## 4. CLI Smoke Results

**Installed 1.0.1 binary:** `/tmp/cg101test/node_modules/.bin/codegraph`  
**Test project:** `project-brain/` (live `.codegraph/` store, 0 nodes indexed)

All four operations return exit code 0 and handle empty-index gracefully.

### `explore` (replaces `context` from 0.9.7)

```bash
codegraph explore "database schema" -p <project>
# Output: "No relevant code found for ..."
# Exit: 0
# Flags: -p <path>, --max-files <number>
```

**Status:** CLI command confirmed present and callable. Returns empty result on unindexed store — correct behavior.

### `node`

```bash
codegraph node "SymbolName" -p <project>
# Output: "Symbol "..." not found in the codebase"
# Exit: 0
# Flags: -p <path>, -f <file>, --offset <number>, --limit <number>, --symbols-only
```

**Status:** Confirmed present and callable.

### `callers`

```bash
codegraph callers "SymbolName" -p <project>
# Output: "ℹ Symbol "..." not found"
# Exit: 0
# Flags: -p <path>, -l <limit>, -j (JSON output)
```

**Status:** Confirmed present and callable.

### `search` (CLI command is `query`; MCP tool is `codegraph_search`)

```bash
codegraph query "keyword" -p <project> -j
# Output: [] (empty JSON array)
# Exit: 0
# Flags: -p <path>, -l <limit>, -k <kind filter>, -j (JSON)
```

**Status:** Confirmed present and callable. **NAMING DISCREPANCY:** The ARCHITECTURE.md and plan call this operation "search", but the 1.0.1 CLI command is `query` (not `search`). The MCP tool is `codegraph_search`. No standalone `search` CLI command exists in 1.0.1.

**All 4 operations successfully smoked: explore ✓, node ✓, callers ✓, search/query ✓**

---

## 5. Migration Notes: trace/context → explore; CODEGRAPH_DIR

### Command renames (0.9.7 → 1.0.1)

| 0.9.7 command | 1.0.1 equivalent | Notes |
|---|---|---|
| `context <task>` | `explore <query...>` | Different output format: 1.0.1 returns symbol source + call paths (matches `codegraph_explore` MCP); 0.9.7 returned markdown context summary |
| `query <search>` | `query <search>` | Unchanged CLI name; MCP tool is `codegraph_search` |
| (no `node` cmd) | `node <name>` | New in 1.0.1: symbol source + caller/callee trail |
| `callers` | `callers` | Unchanged |
| `callees` | `callees` | Unchanged |
| `serve` | (no `serve` cmd) | 1.0.1 uses daemon architecture; MCP started via `install` command |

> The `trace` command seen in older CodeGraph docs is not present in either 0.9.7 or 1.0.1; the MCP server exposes `codegraph_trace` as a tool but there is no corresponding CLI command in either version.

### CODEGRAPH_DIR behavior (1.0.1)

- `CODEGRAPH_DIR` is an env var that overrides the per-project index directory name (default: `.codegraph`)
- Must be a single path segment (no separators, no `.`, no `..`, not absolute); invalid values are ignored with a stderr warning, falling back to `.codegraph`
- Read live (not cached at load), so it can be set per-process without restart
- Exported as `CODEGRAPH_DIR` constant from `dist/directory.d.ts`
- The `CodeGraphPort` adapter should pass `CODEGRAPH_DIR` from config/env to the CLI via `-p <project_root>` (the directory name resolution is internal to codegraph)

---

## 6. Open Risks for Phase-1.4 CodeGraphPort Contract

### Risk 1 (HIGH): schema_versions assertion must target version 5, not 1

The plan says "asserts schema_versions=1". The actual current schema version is 5. The `CodeGraphPort` schema check should assert `MAX(version) = 5` (or `>= 5`). Asserting `= 1` will always fail against a 1.0.1 store.

**Recommendation:** The schema probe in `CodeGraphPort.__init__` should query `SELECT MAX(version) FROM schema_versions` and assert `>= 5`. This is forward-safe: if 1.0.2 adds version 6, the port still works.

### Risk 2 (MEDIUM): "search" kind → CLI command is `query`, not `search`

The port contract uses the kind name "search" but the 1.0.1 CLI command is `codegraph query`. The shell-out adapter must map `kind="search"` → `codegraph query`. Do NOT try to shell out `codegraph search` — that command does not exist.

**Recommendation:** Document the mapping explicitly in the `CodeGraphPort` brief:
- `kind="explore"` → `codegraph explore <query> -p <dir>`
- `kind="node"` → `codegraph node <name> -p <dir>`
- `kind="callers"` → `codegraph callers <symbol> -p <dir>`
- `kind="search"` → `codegraph query <symbol> -j -p <dir>` (use `-j` for machine-readable JSON)

### Risk 3 (MEDIUM): Installed version is 0.9.7, not 1.0.1; `explore` and `node` commands are absent from 0.9.7

The globally installed `codegraph` binary (`/Users/dreddy/.nvm/versions/node/v22.13.0/bin/codegraph`) is v0.9.7, which does NOT have `explore` or `node` CLI commands. The `CodeGraphPort` shell-out will fail if it runs against the system codegraph. The port MUST either: (a) require 1.0.1 to be installed and fail-fast with a clear error if the version check fails, or (b) use the MCP server exclusively (no shell-out) as the access path.

**Recommendation:** Add a `CodeGraphPort.health_check()` that runs `codegraph --version` and asserts `>= 1.0.1` before any query. Alternatively, design the port to use the MCP tools exclusively (which already run at 1.0.1 via the daemon), and only fall back to CLI shell-out if the MCP server is unavailable.

### Risk 4 (LOW): Live index is empty; functional smoke of populated-index output shape deferred

All 4 CLI operations returned empty-index results. The exact output shape of a populated-index response (for parser design) could not be verified in this environment. The MCP tool output shapes are documented in `dist/mcp/tools.d.ts` and match what the running MCP server already exposes.

**Recommendation:** Before freezing the `CodeGraphPort` output parser, run the 4 operations against a seeded test fixture (a small indexed project) to capture real output shapes. The `-j` flag on `query`/`callers` gives JSON; `explore` and `node` emit markdown.

---

*Spike complete. File is untracked — do not commit until orchestrator review.*
