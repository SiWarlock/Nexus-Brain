# Nexus Brain `core/` — Build Guide

> **You're in `core/`.** This file plus root `CLAUDE.md` both load. The root file covers global project conventions + shared comm rules (track-prefix, escalation taxonomy, messaging budget); this file owns code-area conventions for the Python engine (core).

## Launch protocol

| Working on... | cwd | Loads |
|---|---|---|
| Planning / docs / commits | repo root (`project-brain/`) | root `CLAUDE.md` only |
| the Python engine (core) code | `core/` | this `CLAUDE.md` + root |

<!-- For a multi-area project, add a row per additional code area. -->

If you find yourself fighting the wrong conventions, check your cwd.

## Session start/end protocol

**At session start:**
1. Read `IMPLEMENTATION_PLAN.md` (repo root) **by section, not whole** — `grep -n "^##" IMPLEMENTATION_PLAN.md` for offsets, then Read with offset/limit just "Currently in progress" + the active phase. (The file grows; never load it whole.)
2. Confirm with the user what feature this session is targeting.
3. Read the relevant section of `ARCHITECTURE.md` from the lookup table below.

**At session end** (only when the user explicitly says we're done):

1. **Implementer runs `/session-end`.** Implementer writes ONLY:
   - `core/` code files (the slice's implementation)
   - test files (the slice's tests)
   - dependency manifest / lockfile (deps the slice adds)
   - `docs/sessions/<NNN>-<date>-<topic>.md` (session doc, created at `/session-end` Step 5)

   **Implementer must NOT touch (all orchestrator territory).** *This list is the canonical statement
   of the territory rule — `/session-end`, the brief template, and the generated
   `scripts/guards/territory-guard.sh` PreToolUse hook (which mechanically enforces it in team mode)
   all point here.*
   - `IMPLEMENTATION_PLAN.md`
   - `core/LESSONS.md`
   - `core/CLAUDE.md` (entire file — both the Cross-doc invariants table AND the Lessons logged index)
   - `ARCHITECTURE.md`
   - `docs/orchestrator-briefing.md` / `docs/tdd-brief-template.md` / `docs/briefs/` / `docs/runbooks/`
   - other top-level deliverable / design docs
   - `.gitignore` and root-level dotfiles (unless adding a new artifact to ignore, flagged at Step 9)

   At Step 10: **explicit `git add <path>` per slice file; never `git add -A`/`.`; never stage an orchestrator-territory file.** Changes to any orchestrator-territory file (a new cross-doc model, a lesson, an arch note) are **flagged at Step 9**, not edited here — the orchestrator writes them hot (root `CLAUDE.md` + the Step-9 matrix).

2. **Orchestrator runs `/orchestrate-end`** for round close-out + Carry-forward triage + round terminal commit + push.

## Lookup table — where to find canonical info

Don't paste these sections into the prompt. Grep the file:section, read only what you need. `/check-arch <topic>` dispatches off this table.

| Topic | File (relative to repo root) | Section |
|---|---|---|
| <subsystem A> | `ARCHITECTURE.md` | §X |
| <subsystem B> | `ARCHITECTURE.md` | §Y |
| Lessons logged (full prose) | `core/LESSONS.md` | by lesson # |

<!-- Starts near-empty. Add a row whenever a topic is looked up twice. -->

**Code intelligence & docs (when available):** prefer a code-intelligence MCP / docs MCP over grep+read loops — see root `CLAUDE.md` "Code intelligence & docs."

## Stack

<!-- ▼ EXAMPLE BLOCK [id=area-stack]: stack quick-reference for implementer sessions. Canonical stack lives in root CLAUDE.md + ARCHITECTURE.md; this is the cheat sheet. ▼ -->

- **Runtime:** Python 3.12
- **Framework:** FastMCP 3.x · LlamaIndex · LanceDB
- **Validation:** Pydantic v2
- **Lint / types / tests:** ruff / mypy --strict / pytest

<!-- ▲ END EXAMPLE BLOCK [id=area-stack] ▲ -->

## Standard commands

```bash
# Install deps (run once; re-run when the manifest changes)
uv sync

# Run the dev server (if applicable)
uv run nexus

# Tests
uv run pytest

# Quality
uv run ruff check .
uv run ruff format --check .
uv run mypy core

# Preflight (use before saying "done" with a feature)
uv run ruff check . && uv run mypy core && uv run pytest
```

## TDD protocol

**Write the failing test first.** Applies to deterministic code — see the TDD posture in root `CLAUDE.md` for what is test-first vs. exempt.

**Commit per slice when practical.** Never bundle a safety-critical slice with anything else.

## Forbidden patterns

<!-- ▼ EXAMPLE BLOCK [id=forbidden-patterns]: forbidden patterns — 3-5 narrow, enforceable, domain-specific rules. Shape: "Don't <pattern X> because <reason / past incident>; use <alternative Y>." Test-pin them where possible. Starts small; accretes as lessons surface. ▼ -->

Do not:

1. **Write code without a failing test first** (for deterministic code). Even one-line functions.
2. **Embed a chunk before it passes the Redactor** — every chunk goes through `redact(payload, sink)` at persist / MCP-egress / cloud-egress; raw transcripts + `thinking` are never embedded. (§18; pin: the redaction fuzz gate.)
3. **Reach an FS/git/external/session mutation outside `HostPort.perform`** — the core only *proposes* intents; the host adapter authorizes + executes. (§4/§7; pin: the architecture-invariant test.)
4. **Read `datetime.now()`, mint ids, or seed RNG directly** — inject the `Clock` / `Seed`/`IdGen` ports (the determinism seams). Wall-clock + ungoverned randomness break the eval/test seams.
5. **Hardcode the CodeGraph DB path or call `codegraph_trace`/`codegraph_context`** — resolve via `CODEGRAPH_DIR`, query table `nodes` (not `symbols`), use `codegraph_explore`, assert `schema_versions` at startup. (D-27.)
6. **Mix embedding models/dims in one LanceDB dataset, or open a 2nd writer** — model change = blue-green new generation; one writer per dataset; federation is read-only. (§5/§6/§11.)

**Enforcement patterns (machine-readable — `/preflight` warn-greps the staged diff against these).**

```forbidden-patterns
# rule 4 (use the Clock port): datetime\.(now|utcnow)\(
# rule 4 (use the Seed/IdGen port): \b(uuid4|random\.|secrets\.token)
# rule 5 (no deleted CodeGraph tools): codegraph_(trace|context)
# rule 5 (no hardcoded codegraph path): ['\"]\.codegraph/
```

<!-- ▲ END EXAMPLE BLOCK [id=forbidden-patterns] ▲ -->

## Cross-doc invariants — schema/docs mirroring

Several typed models in this codebase are **contracts** mirrored in `ARCHITECTURE.md` and indexed in the table below. The architecture doc is the canonical contract; the model is the executable enforcement. Drift produces silent disagreement.

**Authoring discipline (orchestrator owns this table).** The implementer never edits this table or `ARCHITECTURE.md` directly — it flags a field add/remove/rename at Step 9 as a `Cross-doc invariant change`; the orchestrator writes the row + the arch edit hot the same round (see root `CLAUDE.md` + `docs/orchestrator-briefing.md`). Commits stagger; the working tree stays aligned within the round.

| Model | `ARCHITECTURE.md` section | Notes |
|---|---|---|
| <model> | §X | <field summary> |

<!-- Starts empty (or with the first model if one exists). Populated as contract models land. -->

## Module organization

<!-- ▼ EXAMPLE BLOCK [id=module-layout]: module layout + layer dependency rule. Replace with the project's real directory tree and import-direction DAG. ▼ -->

```
core/
  ports/        # interfaces (HostPort · Embedding/Reranker/Context/Model · CodeGraphPort · Event · Secret · Observability · Clock · Seed/IdGen) — depend on nothing
  model/        # frozen Appendix-A contracts (Chunk · Anchor · ProvenancePacket · stamp · manifest/registry · MCP-tool · policy · state machines)
  redactor/     # the Redactor (fan-in hub)
  ingest/ index/ retrieval/ grounding/ federation/ sync/ drift/ sessions/ agent/ plans/
  mcp/ providers/ obs/ setup/ lifecycle/ nexusops/   # entrypoints / adapters / P2
```

Layer dependency direction — the `ARCHITECTURE.md §2.5` import DAG (top imports bottom, never reverse; **no cross-sibling imports**):

```
entrypoints (cli · mcp · agent · host-adapters)
  → {retrieval · drift · federation} → grounding → index → ingest
  → {redactor · providers · ports · model(manifest/registry)}
```

`redactor` (index-time + MCP-egress + cloud-egress) and `grounding` are **fan-in hubs**, not pipeline stages; `observability` is a **leaf sink** every node emits to. Enforce the import-direction with a test where possible.

Cross-cutting layers can be imported from anywhere. Enforce the rule mechanically with a test where possible — the test *is* the spec for the rule.

<!-- ▲ END EXAMPLE BLOCK [id=module-layout] ▲ -->

## Subagents

See `.claude/agents/README.md` for the canonical inventory + integration points.

<!-- ▼ EXAMPLE BLOCK [id=area-subagent-candidates]: area-specific subagent candidates — list candidates that would earn their keep specifically in this area (e.g. an ABI/types syncer for a frontend area, a Pyth/feed verifier for a contracts area). Build only on real friction. ▼ -->

<!-- ▲ END EXAMPLE BLOCK [id=area-subagent-candidates] ▲ -->

## Lessons logged from prior sessions

The full prose for each lesson lives in `core/LESSONS.md`. This index is the compact orientation surface.

**Lesson numbers are stable IDs** — once assigned, they don't change. New lessons get the next sequential number. `/session-end` proposes additions when it detects them; the user approves before the entry is written and a row is added here.

Lessons start at §1.

| # | Date | Topic | Rule (one-liner) |
|--:|---|---|---|
| | | | |

<!-- Starts empty. Each row links to its `LESSONS.md` anchor. -->

<!-- Slash commands: see root CLAUDE.md "Slash commands available." Implementer pair: /session-start + /session-end. -->
