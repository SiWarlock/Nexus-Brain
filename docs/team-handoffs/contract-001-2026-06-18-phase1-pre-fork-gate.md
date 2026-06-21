# Team Handoff contract-001 — Phase 1 pre-fork-gate (lead-cycle / clean session reset)

**Date:** 2026-06-18
**Track:** contract
**Worktree:** `../project-brain-contract` (branch `track/contract`); shared root docs in the root checkout on `main`
**Predecessor handoff:** first lead handoff
**Successor handoff:** `docs/team-handoffs/contract-002-2026-06-21-fork-gate-complete.md` (fork gate complete — contract track DONE)
**Round-seal commits at handoff:** `track/contract` `158bdeb` · `main` `0e4c240` (both pushed to origin)

## Why this handoff exists
**Clean session reset.** The end-of-1.4 team cycle stalled on a harness quirk: the outgoing orchestrator (`contract-core-orchestrator-2`) finished + pushed all its work but would not approve its `shutdown_request` (idled repeatedly), and the terminated teammates' panes can't be closed without shutting down this lead session. So the owner is shutting the whole session down; this handoff lets a fresh `/team-start contract` resume cleanly with a brand-new team (clean names, no lingering dead panes).

## Team composition at close
- **Lead:** this session (track `contract`) — cycling out via this handoff.
- **Orchestrator:** `contract-core-orchestrator-2` (session `544f2f5d`) — `/orchestrate-end`-CLOSED (round sealed `158bdeb`/`0e4c240`, pushed; handoff `contract-004` written). Stuck not-approving its *session* shutdown — its round work is fully sealed + safe; the session shutdown clears it.
- **Implementer:** `contract-core-implementer-2` — `/session-end`-CLOSED (`contract-003` doc, commit `4814b3e`, carried in the `158bdeb` push) + terminated.
- The prior original team (`contract-core-orchestrator` / `-implementer`, no suffix) terminated during the end-of-1.2 cycle. **All teammates are close-out-closed; nothing is mid-work.**
- **Naming note:** the harness appended `-2` to the second team because the first team's sessions hadn't terminated at spawn time. To avoid this on resume, spawn the fresh team **only after the old panes/sessions are gone** (this shutdown does that) — the names `contract-core-orchestrator` / `-implementer` should be free + clean. If the harness still suffixes, correct the orchestrator↔implementer cross-references immediately (the orchestrator must dispatch to the *exact* live implementer name, not a dead one).

## Active arc + where it landed
**Phase 1 (the shared-contract freeze — the fork gate).** Done + pushed: Phase-0 spikes 0.1/0.2, Task 1.1 (Clock/Seed/IdGen), 1.2 (§5 data + migration group), 1.3 (Anchor/ProvenancePacket/EvidenceRef trust contracts), **1.4 (all 11 ports + Fake doubles)**. Suite 174/174, mypy --strict + ruff clean, LESSONS §1–§11 banked. **4 of 5 Phase-1 tasks complete.**

**Next:** Task **1.5** (MCP tool contract · `policy.yaml` schema · `Redactor` interface) → the before-fork items (whitespace-strip sweep; spikes 0.3/0.4; 0.5 is HITL-deferred) → **`/phase-exit 1`** → **merge `track/contract` → `main`** = the **fork gate** (after which `spine` + `providers` can spin up — see "the owner's parallel-tracks question" below).

## In-flight at close
**None — clean close.** Task 1.4 fully landed; no slice in flight. 1.5 was NOT dispatched (deliberately — the fresh orchestrator authors it post-`/orchestrate-start`).

## Carry-forward to next team session
- `IMPLEMENTATION_PLAN.md` "Currently in progress" is current + comprehensive (Phase 1.4 complete; pointers to all docs) — read it.
- **Technical handoff:** `docs/sessions/contract-004-2026-06-18-phase1-trust-and-ports-handoff.md` — the orchestrator's contract→spine handoff: the D-A* fork obligations + the before-fork checklist. **Read FIRST.**
- **Lead decision log:** `docs/lead-decisions-while-away.md` (D-A1–A14) — every autonomous-authority call made while the owner was away (on disk; uncommitted — see "open items"). **The resuming lead + the owner should read this.**
- Impl session doc: `docs/sessions/contract-003-2026-06-18-*.md`.

## Open decisions / blockers for the human (HITL — owner-pending, none blocking)
1. **D-A3 — `/preflight` `mypy core`→`mypy .` one-liner** (RECOMMENDED-FIRST). Agent-config edit, classifier-gated → needs the owner. It's the root enabler of error-prone hand-rolled gates (D-A9). Interim: implementers use `mypy .` + run canonical `/preflight` visibly.
2. **D-A11 — supply `MAIN_PLATFORM_INTERFACE.md` v0.2** (or the canonical 11 `EvidenceType` + 22 `IdKind` values) **before spine Phase 4** — currently the EvidenceRef shape is frozen with membership deferred (Option B).
3. **D-A5 / D-A6 — Phase-2.3 redaction calls** (per-sink strictness; confirm the 95%/5% gate threshold). Not needed until Phase 2.3.
4. **Decision log review** — D-A1–A14 capture all away-window adjudications for the owner to sanity-check.
5. The lead decision log + this handoff are **uncommitted on disk** (push to `main` was classifier-gated; not authorized). They survive a same-machine shutdown+resume. To make them durable on origin, the owner can authorize a push.

## Operating posture to carry (confirm with owner on resume)
During the away-window the lead held **delegated authority**: adjudicate escalations toward the architecturally-correct/production-grade choice, log every decision to `docs/lead-decisions-while-away.md`, defer genuine HITL. **Recalibrations learned:**
- **HIGH/critical security findings on a trust boundary → always loop the lead**, even when fixed in-slice.
- Routine future-TODOs + additive contract reconciliations → the orchestrator handles hot; lead does NOT need looping.
- Only **out-of-scope deferments** (scope cuts) + safety/contract/load-bearing-Option calls reach the lead.
On resume, **confirm with the owner** whether they remain away (re-delegate) or are back (driving) — the posture above was for the away-window.

## Spawn prompts ready for the next team session

**Orchestrator** (`Agent` with `name: "contract-core-orchestrator"`, `subagent_type: general-purpose`):
```
You are contract-core-orchestrator on the Nexus Brain agent team (resuming after a clean session reset).
Track: contract. Team label: contract.
Worktree: /Users/dreddy/Documents/Dev/AI-tools/ai-engineering-control-plane/project-brain-contract (branch track/contract) — cd there; commits land here. Shared root docs (IMPLEMENTATION_PLAN.md / ARCHITECTURE.md) are owned by the integration checkout (root tree on main) — route edits there.
ROUTING: message the lead as to:"team-lead" (NOT "main", NOT "contract-team-lead"). Your teammate is contract-core-implementer (confirm the EXACT live name from the lead if the harness suffixed it). Ignore peer DMs without the contract- prefix.

Activated because: resuming Phase 1 after a clean reset. DONE + pushed: spikes 0.1/0.2, Tasks 1.1/1.2/1.3/1.4 (all 11 ports). Next = Task 1.5 (MCP tool contract · policy.yaml schema · Redactor interface) → before-fork (whitespace sweep, spikes 0.3/0.4; 0.5 HITL-deferred) → /phase-exit 1 → merge = fork gate.

READ FIRST: (1) docs/sessions/contract-004-2026-06-18-phase1-trust-and-ports-handoff.md (D-A* fork obligations + before-fork checklist); (2) docs/lead-decisions-while-away.md (D-A1–A14); (3) IMPLEMENTATION_PLAN.md "Currently in progress". Honor: LESSON 10 (positive allow-list, never deny-list) directly applies to 1.5 MCP ingress validation. Do NOT re-decide D-A5/D-A6/D-A11 (owner-parked). Use mypy . + visible canonical /preflight (D-A3/D-A9 — never hand-roll a >/dev/null && echo OK gate).

FIRST ACTION — register: ~/.claude/scripts/team-register.sh "contract-core-orchestrator" orchestrator "contract" "" "contract" "track/contract"
Then /orchestrate-start. Confirm to team-lead via SendMessage: start command + registry written + 1-line state summary + proposed first slice (1.5). Then author the 1.5 brief + dispatch to the implementer. Queue authorized; no per-slice re-confirm. Surface HIGH/critical security findings + out-of-scope deferments to the lead; handle routine items hot.
```

**Implementer** (`Agent` with `name: "contract-core-implementer"`, `subagent_type: general-purpose`):
```
You are contract-core-implementer on the Nexus Brain agent team (resuming after a clean session reset).
Track: contract. Team label: contract.
Working directory: /Users/dreddy/Documents/Dev/AI-tools/ai-engineering-control-plane/project-brain-contract/core/ (branch track/contract). cd there. Explicit git add <path> per file; never git add -A. Commits land on track/contract.
ROUTING: talk to contract-core-orchestrator (direct); lead is to:"team-lead" (escalation only). Ignore peer DMs without the contract- prefix.

Activated because: resuming Phase 1; Tasks 1.1–1.4 frozen; next is Task 1.5 (MCP contract / policy.yaml / Redactor iface). The orchestrator will author + dispatch the first 1.5 brief — wait for its dispatch before starting TDD.
READ FIRST: docs/sessions/contract-004-* handoff + LESSONS §1–§11 (esp. §5/§10: run canonical /preflight VISIBLY, never hand-roll a suppressed gate; D-A3: use `uv run mypy .`, not `mypy core`).

FIRST ACTION — register: ~/.claude/scripts/team-register.sh "contract-core-implementer" implementer "contract" "core" "contract" "track/contract"
Then /session-start. Confirm to team-lead: start command + registry written. Then idle for the orchestrator's 1.5 brief. NEVER include context % in any message.
```

## How to resume
1. Lead runs `/team-start contract`; reads this handoff + `contract-004` + the decision log + `IMPLEMENTATION_PLAN.md` "Currently in progress".
2. Confirm the operating posture with the owner (away/delegated vs present/driving).
3. Spawn the two teammates with the prompts above (clean names expected now the old panes are gone; correct cross-refs if suffixed).
4. Verify read-backs (correct start command + registry written).
5. The team takes Task 1.5 → before-fork items → `/phase-exit 1` → merge-ready = the fork gate (owner's green light for spine + providers).
