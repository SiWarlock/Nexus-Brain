# Handoff — `project-brain` (working name; recommended product name **"Anchorlight"**)

> **Read this first, then `docs/PRD.md`.** This is the state of the project-brain effort as of **2026-06-03**.
> The work so far is **design only** — a comprehensive rough-draft PRD + research dossier. No code yet.
> The product owner paused here to switch back to eval-triage practice; resume project-brain from this doc.

---

## 0. TL;DR — what this is

A **local-first, multi-project developer knowledge platform**. It fuses three things:
1. a **curated docs pipeline** (the layer-docs / LESSONS / planning artifacts that the *cc-crew* repo produces — and, more broadly, **any** docs in a repo),
2. **per-repo live code graphs** (CodeGraph-style AST/call-graph intelligence, one index per repo, **federated** / union-read across the portfolio), and
3. a **frontier model** (Claude/GPT) reached through a **local MCP server harness**,

so you can **ask one question across your entire portfolio of projects** and get an answer where **every claim carries a clickable, continuously-revalidated `file:line`**, is **dated**, and is **honest about staleness**.

**The keystone** is the `file:line` **anchor**, treated not as text but as a **typed, continuously re-validated edge between docs and code** — the join that fuses the docs pipeline to the live code graphs.

**Honest one-liner (from the PRD):** *N live per-repo graphs, fanned-out and union-read, fused on the `file:line` anchor to a curated docs pipeline, on a local-first frontier harness.* No competitor occupies that intersection (local-first AND portfolio-scale AND frontier-harness AND docs-fused-to-per-repo-live-code-graphs).

---

## 1. Current state — files & git

**Repo:** `~/Documents/Dev/AI-tools/project-brain/` — git-initialized, **UNCOMMITTED** (the owner commits themselves; offer an initial commit when resuming).

| File | What it is |
|---|---|
| `docs/PRD.md` | **The deliverable** — comprehensive rough-draft PRD, **723 lines**, 15 sections + a one-screen assumptions table (§1.5). Honest: marks `[VERIFIED]` / `[UNVERIFIED]` / `[ASSUMPTION]` / `[OPEN]` throughout. |
| `docs/RESEARCH.md` | ~30K research dossier — retrieval/embeddings, the CodeGraph probe, federation patterns, competitive analysis. The evidence behind the PRD. |
| `docs/onboarding-and-doc-lifecycle.md` | Captured product-owner requirements (install/onboarding, source-agnostic discovery, the owned/foreign/supplemental doc model). **Already folded into the PRD** — kept for provenance. |
| `docs/HANDOFF.md` | This file. |
| `README.md` | Stub (name + one-line + "see docs/PRD.md"). |

**Sibling repo it depends on:** `~/Documents/Dev/AI-tools/claude-code-tdd-agent-crew-scaffolding/` ("cc-crew") — on `main`, clean. It owns the doc-producing **skills** (`layer-docs`, `learn-site`, the arch-draft chain). Memory at `~/.claude/projects/-Users-dreddy-Documents-Dev-AI-tools-claude-code-tdd-agent-crew-scaffolding/memory/`.

---

## 2. Re-orient — read in this order

1. **This doc** (you're here).
2. **`docs/PRD.md`** — start with §1 TL;DR, §1.5 assumptions table (the "read this first" screen of every open bet), then skim §7 (functional requirements), §8 (feature catalog), §9 (architecture), §10 (cc-crew relationship), §13 (risks), §14 (roadmap), Appendix D (naming).
3. **`docs/RESEARCH.md`** — for the CodeGraph probe verdict + federation patterns + competitor table.
4. **cc-crew context** — `../claude-code-tdd-agent-crew-scaffolding/skills/{README,ROUTING}.md` and `skills/layer-docs/SKILL.md` (now **incremental** — see §6 below). Plus that repo's memory files.

---

## 3. Naming (OPEN — A9)

Working name `project-brain` (generic). Candidates in **PRD Appendix D**: **Portfolio Brain**, **Anchorlight** (recommended), Lodestar, Graphkeep, Throughline, Cartulary. **Draft recommendation: "Anchorlight — the portfolio brain."** None are trademark-cleared; clearance gates v1.

---

## 4. The decisions already made (and the honest unknowns)

- **The `file:line` anchor is the unlock** (the docs↔code join). Everything trusts it.
- **CodeGraph federation — the honest verdict (from a live probe, baked into the PRD).** CodeGraph's daemon **idle-exits at ~300 s** and has **no standalone watcher/`daemon` subcommand** (it indexes via `serve`/index). So the truthful freshness story is **"live while active, cold-but-fast-catch-up when idle," NOT always-live.** Federation = **read-only WAL `ATTACH`-union over N per-repo SQLite graphs** (union-read). **True cross-repo *symbol* resolution** — the thing that turns "N graphs side by side" into "one graph" — is the **v2 moat and is explicitly UNVERIFIED**, gated by a go/no-go spike (PRD §13 RISK #1/#2). The probe was **Python-only** (multi-language federation also unverified — A2).
- **Local-first & private** by default; cloud model sees only the text the harness deliberately returns, under a per-project policy (ZDR/redaction). A secret-heavy repo can be fully air-gapped.
- **Clean cc-crew boundary** — the brain *consumes* docs through a small versioned contract; it never authors cc-crew's docs or mutates its provenance manifest. **But it is repo-agnostic** (see §6).
- **The brain is a rebuildable derived cache** — "rebuildable" = reproduces equivalent retrieval quality, not bit-identical re-embedding (cloud embedders aren't bit-reproducible — A5).

---

## 5. Feature catalog highlights (PRD §8 has the full tiered, scored catalog)

**Signature features (the identity):**
- **★ M1 Anchor-Live** — anchors re-resolved against the live graph; green if still pointing at the symbol, red if stale.
- **★ M2 + V3 Ask-the-Portfolio** — one `/ask` fusing dense+BM25+call-graph across all projects, every claim cited or refused (grounding gate).
- **★ V10 Self-Updating Project Brain** — detect drift → `layer-docs --check` → `--update` (in-place, don't-clobber) → re-embed only changed chunks. The brain keeps its *own* docs honest.
- **★ M9/W14 Session Memory** — ingest Claude+Codex session transcripts → ask "when did we implement X / why did we choose Y / what was I doing when Z changed," cited to the session + model + date + branch + **linked commit** (see §6/§7 below).
- **★ V1 Drift Radar** (where the docs lie, portfolio-wide), **★ M6 Déjà-Vu LESSONS** recall, **★ W1 Cross-Project Impact Lens** (the v2 federation payoff), M3 Whole-File Hydration, M4 Depth-Dial (plain⇄deep), M5 Provenance/Freshness stamps, M7 Install-and-Go, M8 Source-Agnostic Discovery.

---

## 6. Relationship to cc-crew + the doc-producing skills (PRD §10)

- **cc-crew is ONE (privileged, best-structured) producer; the brain is repo-agnostic.** It discovers **all** docs in any repo regardless of how they were made (cc-crew layer-docs, gstack, Compound Engineering, Mintlify, hand-written, ADRs, READMEs, API schemas, docstrings) via broad globs + a `.brainignore` + an extensible **producer recognizer** (FR-11).
- **Owned / Foreign / Supplemental doc model** (FR-12): OWNED docs (a skill can re-run, e.g. layer-docs) may regenerate+replace but **don't clobber human edits**; FOREIGN docs are ingested + re-read on change, never overwritten; SUPPLEMENTAL are brain-added gap-fills. "Replace in the vector DB" is uniform (content-hash tombstone+upsert keyed on `source_path`); only *regeneration* differs.
- **`layer-docs` is now INCREMENTAL** (changed in cc-crew this session — `skills/layer-docs/`): initial / **update** / **check** modes, a stamped `docs/layers/.layer-docs.json` state file, change detection, and a don't-clobber guard. The brain consumes `layer-docs --check` as the **read-only drift signal** and orchestrates `--update` to refresh OWNED docs. **This is load-bearing for V10.**
- **`learn-site`** (cc-crew) could become the brain's **front-end** (a chat panel over the MCP) in v2.
- **Skills bundling decision (OPEN — A13):** for the install to be self-contained, project-brain should **bundle/vendor the doc-skills it needs** (vs hard-depend on a cc-crew checkout). Lean self-contained.

---

## 7. Today's additions — all folded into the PRD

(These were product-owner brain-dumps this session, now integrated and grounded.)
- **Install-and-Go (M7, FR-10):** global CLI (`npm i -g` / `npx`); one-time `brain setup` ensures **CodeGraph present** (`[UNVERIFIED]` A12 — likely NOT npm; detect→install via brew/cargo/pipx→verify), **registers the MCP server** in host configs (Claude Code/Desktop/Codex, idempotent/reversible/consented), **registers the doc skills**, creates the store. `brain add <repo>` bootstraps a workspace (CodeGraph init + manifest + first ingest + sync hook), with **partial-project handling** (ingest whatever exists now; suggest layer-docs but never block).
- **Source-Agnostic Discovery (M8, FR-11)** — above.
- **Doc lifecycle (FR-12, V10)** — above.
- **Session Memory (M9 Claude-only → v1; W14 full cross-tool → v2; FR-13).** Probed schemas:
  - **Claude `[VERIFIED]`:** `~/.claude/projects/<cwd-with-/-as-->/<uuid>.jsonl`; every record carries `cwd` (exact project association), `gitBranch`, ISO-8601 `timestamp`, `sessionId`, `version`; assistant records carry `model` + content blocks (text/thinking/tool_use). 33 project dirs already on disk.
  - **Codex `[VERIFIED layout / UNVERIFIED assoc]`:** `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (`session_meta`/`event_msg`/`response_item`) + `~/.codex/session_index.jsonl` ({id,thread_name,updated_at}). **A14 open: confirm `session_meta` carries `cwd`** (one `jq` confirms it). Codex sqlite is automation/inbox, not transcripts.
  - Design: don't embed raw transcripts (21 MB each, mostly spam/thinking) → **episode cards** + commit-linking (edit events → nearby commits, heuristic, carries a `confidence`, degrades to `unlinked`). **Privacy is a HARD gate** (opt-in, local-embeddings default, redaction of secrets/keys/PII, exclude `thinking`, ZDR) — transcripts can contain pasted secrets.

---

## 8. Roadmap (PRD §14)

- **v0** — long-context `/ask`, no DB (stuff a project that fits <~200K into the cached window; validates the harness + grounding gate + depth-dial with zero infra).
- **v1** — install/onboarding (M7) + source-agnostic discovery (M8) + docs-RAG (LanceDB per project) + the anchor-aware chunker + `brain add`/sync (Watchman + git hooks + content-hash deltas) + FastMCP server (`search`/`get_file`/`list_projects`) + the provenance contract + **M9 Session Memory (Claude)** + the drift-detection half of V10. **The daily-driver release.**
- **v1.1** — code chunks (AST/CodeHierarchy) + **live code-graph federation** (ATTACH-union) + the **self-updating loop (V10, OWNED docs)** + graph tools (callers/callees/trace/impact) + Drift Radar + PR-aware. **Cross-repo resolution prototyped behind the go/no-go spike** (single-language assumption).
- **v2** — web UI / learn-site chat / team mode (Brain Hub router, `.brain` bundles) + **W14 full Session Memory** + W1 Cross-Project Impact Lens + deeper lifecycle (gap analysis, conflict detection, external connectors).
- **Moonshots** — Since-You-Left briefing, Drift-Adapter, Linear/Jira injector, voice/ambient.

---

## 9. Highest-leverage next steps (pick one to resume)

1. **The federation cross-repo-resolution spike** (the v2 moat; PRD §9.3, §13 RISK #1/#2). A go/no-go: can ATTACH-union + namespaced `qualified_name` + `unresolved_refs` resolve cross-repo at acceptable precision? Everything in v2 depends on it. **The single highest-leverage open item.**
2. **Spec v0** — the long-context `/ask` you could actually build first (no DB, prompt-cached corpus, the grounding gate). Fastest path to a working artifact.
3. **Confirm the Codex `session_meta` cwd field** (A14) — ~30 s `jq` on a `session_meta` record; flips M9/W14's association from assumed to known.
4. **Naming decision** (A9) — pick the product name (Anchorlight recommended).
5. **Initial commit** of the project-brain repo (it's uncommitted).
6. **Harden a section** — e.g. turn the §13 risks into spike plans, or flesh out the privacy/redaction design.

The PRD's own closing note names **the federation layer (#1) and naming (#4)** as the two highest-leverage opens.

---

## 10. Gotchas & context for the next session

- **The PRD was authored by a background Workflow, then revised.** The workflow's `args` did **not** thread into the script (returned `undefined/...`), so the author agent wrote to a *relative* path (a nested `project-brain/` inside cc-crew); it was **consolidated into the correct sibling repo and cc-crew cleaned**. **Lesson: if you re-run a Workflow that writes files, HARDCODE absolute paths in the script — don't rely on `args`.**
- **Honesty convention:** the PRD marks `[VERIFIED]` (live probe / cited), `[UNVERIFIED]` (plausible, don't build as if true), `[ASSUMPTION]`, `[OPEN]`. The assumptions table (§1.5) lists **A1–A17** with gates + defaults. **Keep new claims marked.**
- **cc-crew is on `main`** (ce-integration deleted); `main` is ahead of `origin/main` (the owner pushes). The incremental `layer-docs` upgrade is committed there (`b2c8846`).
- **The eval-triage practice repos are unrelated siblings** (`eval-triage-practice`, `-hard`, `-extreme`, `acme-support-copilot`) — the owner's *next* focus, not part of project-brain.
- **Don't auto-commit / push** — the owner does that. Symlinked skills update live (no re-register needed).

---

## 11. Paste-ready kickoff prompt for the next project-brain session

```
We're resuming the "project-brain" (working name; recommended "Anchorlight") effort — a local-first,
multi-project code+docs AI knowledge platform. It's design-only so far: a comprehensive rough-draft PRD.

Read docs/HANDOFF.md in full first, then docs/PRD.md (§1 TL;DR, §1.5 assumptions, §7 FRs, §8 features,
§9 architecture, §10 cc-crew relationship, §13 risks, §14 roadmap, Appendix D naming), and skim
docs/RESEARCH.md (the CodeGraph probe + competitive analysis). Don't re-read the cc-crew or gstack repos
beyond what §10/§2 point to.

Keep the PRD's honesty markers ([VERIFIED]/[UNVERIFIED]/[ASSUMPTION]/[OPEN]). Don't commit unless I ask.

Then ask me which of the §9 "highest-leverage next steps" to take — I'm most interested in either
(a) the federation cross-repo-resolution go/no-go spike, or (b) speccing v0 (the long-context /ask).
```

---

*End of handoff. The product owner is switching focus to eval-triage practice next; project-brain resumes here.*
