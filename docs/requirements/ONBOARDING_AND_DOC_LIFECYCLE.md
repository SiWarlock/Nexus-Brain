# Captured requirements — install, onboarding & doc lifecycle

> Source: user direction (2026-06-03). Originally captured "to be folded into `PRD.md`"; now a standing
> companion (indexed in `../README.md`), partially folded into PRD §2.2 / Functional Requirements. These add an
> **Installation, setup & onboarding** section and a **Documentation lifecycle / freshness loop** requirement,
> and they sharpen the cc-crew boundary (skills bundling). Standalone-first; NexusOps integration caveats inline.

## R-INSTALL — one-command global install that bootstraps EVERYTHING
Installable as a desktop app + CLI — Homebrew Cask / signed `.dmg` with the bundled **`nexus`/`nb` CLI** (D-20; supersedes the earlier `npm i -g` idea, since the core is Python + Tauri). A single
`nexus setup` (run once per machine) makes it ready out of the box by ensuring **all** moving parts:
1. **CodeGraph present.** Nexus Brain treats CodeGraph as a dependency and ensures it's installed +
   on PATH. (Caveat to verify via the CodeGraph probe: CodeGraph may NOT be an npm package — it could be a
   separate binary/toolchain. So "dependency" means setup *detects → installs via its real channel*
   (brew/cargo/pipx/download) → verifies, not necessarily an npm `dependencies` entry.)
2. **MCP server configured + installed.** Register the Nexus Brain MCP server into the host configs
   (Claude Code `~/.claude.json` / Claude Desktop / Codex `~/.codex/config.toml`) — idempotent, reversible,
   with consent. This is what makes the brain queryable from any frontier-model session.
3. **Skills registered.** Auto-register the doc skills it needs (`layer-docs`, `learn-site`, and any new
   doc-update skill) into `~/.claude/skills` (and, if that host convention is confirmed by probe, `~/.codex/skills`).
4. **Central store created** (`~/.project-brain/`) + the project registry.
**Boundary decision this forces:** for a fresh machine with ONLY Nexus Brain to work, Nexus Brain must
**bundle or fetch the skills it needs** (vs. depend on a cc-crew checkout). Options: (a) extract the
doc-skills into a shared installable unit both repos use; (b) Nexus Brain vendors its own copy/fork of the
doc skills; (c) hard dependency on cc-crew. Lean (a) or (b) so install is self-contained.

## R-ADD — `nexus add` bootstraps the WORKSPACE
Running `nexus add` inside a repo should set up everything that project needs, automatically:
1. **Init CodeGraph for the workspace** (`codegraph init`/index — exact command TBD from probe) so structural
   queries work immediately.
2. **Write `.project-brain.json`** manifest (project id, globs, embed model, last-indexed sha).
3. **Register project-local needs** — ensure the doc skills are available when working in this project (skills
   are global, but `add` can also drop a project-local `.claude/` pointer to the brain MCP + skills).
4. **First ingest** of whatever docs + code exist now.
5. **Enroll sync** — start the watcher/daemon and/or install the git hook (post-commit/merge) for the project.

## R-PARTIAL — handle unfinished projects gracefully
A project may not be finished, so `add` must NOT hard-require complete docs:
- Ingest whatever exists *now* (README, ARCHITECTURE, planning, code) so there's immediate value.
- If `docs/layers/` is absent/thin, **suggest** running `/layer-docs` (or offer a non-interactive best-effort
  pass) — but don't block. Re-running `add`/`sync` after docs improve upgrades the index.
- The brain can surface a "doc completeness" signal per project and nudge accordingly.

## R-DOCLIFECYCLE — docs must be UPDATABLE, and the vector DB must replace stale docs
When features/changes are added, the documentation must be refreshable and the index must swap old → new:
1. **Doc regeneration (cc-crew side):** `layer-docs` **already ships** a re-runnable / incremental refresh
   (`/layer-docs --check` reports staleness; reruns regenerate only changed areas in place) — this is NOT a new
   cc-crew capability to build, just one to consume. *(Nexus Brain's vendored scaffold copy is behind the
   current scaffold; pull the current scaffold before relying on this.)*
2. **Drift detection (the trigger):** detect when code changed but its docs didn't (the docs↔code `file:line`
   anchors make this checkable) → flag stale layers → prompt or auto-run the doc refresh.
3. **Replace-on-change (brain side):** `sync` already does content-hash incremental upsert — changed doc
   files re-chunk and **tombstone + replace** their old chunks keyed on `source_path`. So "new docs replace
   old in the vector DB" is handled by the sync engine; the new piece is the regeneration trigger + in-place
   doc update.
**Capstone capability that emerges:** the brain isn't a passive index — it can **orchestrate the doc
pipeline**: detect staleness → trigger `layer-docs` refresh (`--check` then regenerate) → re-embed. A self-updating
project brain. Strong differentiator; call it out as a signature feature. **NexusOps integration note:** standalone,
the brain runs this loop in-process; **integrated, any doc mutation is propose-only through the Action Gateway**, and
the NexusOps MVP has **no gateway-executable doc-refresh action** (the 3 MVP `brain.*` actions are
`brain.ask` / `brain.sync` / `brain.summarize_session`; `brain.refresh_owned_docs` is risk-3, spec-only, post-MVP).

## Cross-cutting notes
- All "modify host config / install global" actions must be **idempotent, reversible, and consented**
  (`setup --register-mcp`, `setup --uninstall`).
- These requirements thread into existing PRD sections: Functional Requirements (add ingest-bootstrap +
  doc-lifecycle), Architecture (setup/installer component; the orchestration loop), cc-crew Relationship
  (skills bundling decision), Roadmap (setup/installer is part of v1; the drift→refresh loop is v1.1/v2).

## R-DISCOVERY — source-agnostic: discover ALL relevant docs, not just cc-crew artifacts
The brain must NOT assume cc-crew. It works on ANY repo and **auto-discovers all relevant documentation**
however it was produced — cc-crew layer-docs, gstack (`/document-generate`, `/document-release`), Compound
Engineering, Mintlify/Docusaurus, hand-written notes, ADRs, wikis. **cc-crew is just one (privileged,
well-structured) producer; the brain degrades gracefully to "whatever docs exist."** This makes it a general
product, not a cc-crew appendage.
- **Broad discovery:** `**/*.{md,mdx,rst,adoc}`, `README*`, `ARCHITECTURE*`, `CONTRIBUTING*`, `CHANGELOG*`,
  `docs/**`, `**/adr/**` / RFCs, `.github/**`, OpenAPI/GraphQL/JSON schemas, notebooks, diagrams (Mermaid),
  and code-embedded docs (docstrings/JSDoc/module headers). Respect `.gitignore` + a `.brainignore`; skip
  vendored/build/secrets.
- **Source/producer recognition:** tag each doc with its `producer` (cc-crew-layer-docs | gstack | CE |
  human | other-generated) via frontmatter, signature markers, or path conventions — an extensible
  "doc-source recognizer" registry. Drives the owned/foreign/supplemental behavior below.
- **Classification:** `doc_type` (architecture | layer | planning | lesson | api | guide | readme | changelog
  | adr | design) for filtering + organization.

### The model that resolves "update vs replace vs supplement": OWNED / FOREIGN / SUPPLEMENTAL
- **Owned** — produced by a skill the brain can re-run (layer-docs). The brain may **regenerate + replace**
  (and re-embed). Honors the don't-clobber discipline: if a human hand-edited an owned doc, detect it and
  preserve/merge rather than overwrite (same philosophy as scaffold-upgrade's 3-way merge).
- **Foreign** — produced by gstack/CE/humans/other tools. The brain **ingests** and **re-ingests on change**
  (hash) but **never overwrites**. It may **annotate** (flag staleness vs code) and offer a supplemental note.
- **Supplemental** — docs the brain *adds* where gaps exist (via layer-docs), clearly namespaced + marked as
  brain-generated, never clobbering human docs.
- **Uniform replace-in-DB:** regardless of source, the content-hash sync tombstones + replaces stale chunks
  keyed on `source_path`. Only the *regeneration* differs (owned can be re-run; foreign is just re-read when
  its author/tool updates it).

### Gaps to fill (proactive — beyond what was asked)
- **Provenance & trust ranking** at retrieval time: when docs (or a doc vs code) conflict, rank by source
  authority × recency × code-agreement (do the doc's `file:line` anchors still match current code?). Every
  answer cites provenance + freshness.
- **Drift/staleness as a first-class signal for ALL docs** (not just owned): heuristic = referenced
  files/symbols changed since the doc's last edit. Owned → auto-refresh; foreign → flag + offer a "what
  changed" supplement.
- **Conflict detection** (doc-vs-doc and doc-vs-code) and **doc-gap analysis** ("these code areas have no
  docs" → suggest layer-docs). Both are signature-worthy features.
- **Non-markdown + external sources:** API schemas, notebooks, diagrams now; external connectors
  (Notion/Confluence/wiki links referenced in the repo) as a v2 roadmap item.
