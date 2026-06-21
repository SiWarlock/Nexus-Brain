# contract-008 — 2026-06-20 — Phase 0 close-out + fork-gate orchestration (0.3 O-FED + 0.4 dispatch + the fork gate)

> **Orchestrator-side** session doc (the implementer's round doc is [contract-007](contract-007-2026-06-20-phase0-lancedb-bakeoff-rig.md), covering 0.4). This doc covers the **orchestrator-side** work: the 0.3 federation investigation (run as an orchestrator spike-agent), the 0.4 dispatch+review, the round close-out, and the fork-gate merge.

- **Phase:** 0 (Pre-build spikes) — the last two spikes → the fork gate.
- **Track:** contract (worktree `project-brain-contract`, branch `track/contract`).
- **Predecessor (orchestrator):** [contract-006](contract-006-2026-06-20-phase1.5-1.6-orchestrator-handoff.md)
- **Successor (orchestrator):** _(next /orchestrate-end — post-fork; spine/providers are the owner's separate /team-start)_

## Why this session existed

The fresh full-runway team's stretch to the **fork gate**. Phase 1 (1.1–1.6) was frozen + pushed last round (suite 232/232). The remaining before-fork work was the two Phase-0 spikes — **0.3** (O-FED, federation cross-repo resolution; investigation-style, orchestrator-side) and **0.4** (O-LANCE-BAKEOFF, the LanceDB maintenance bake-off RIG; implementer `/tdd`). After both: `/orchestrate-end` → `/phase-exit 1` → merge `track/contract`→`main` = **the fork gate** (the owner's green light for spine + providers).

## What landed (orchestrator-side)

- **Spike 0.3 (O-FED federation) — investigation, DONE.** Run as an orchestrator spike-agent (the 0.2 precedent), producing `ci/probes/federation_spike.md`. **Verdict:** `unresolved_refs.reference_name` × namespaced-`qualified_name` resolution is VIABLE as a *uniqueness-gated merge enrichment*, NOT the default — side-by-side-marked (`{projects_requested, answered, excluded[]}`) stays the conservative default; merge only on a unique segment-suffix match against `is_exported` nodes; no heuristic tie-breaking. Synthetic 56-ref/35-node corpus: **precision 1.000 / recall 0.967**; the rule fails SAFE (namespace loss → AMBIGUOUS/NO_MATCH, never a wrong merge). A bounded real cross-check (already-present v0.9.7, no install — §18-clean) surfaced **2 HIGH real-data risks** (sparse/empty real `unresolved_refs` caps recall; thin real `qualified_name` → more homonyms, precision preserved). The §11 design decision is **deferred to the Phase-6 federation track** (recommendation recorded).
- **Spike 0.4 (O-LANCE-BAKEOFF rig) — dispatched + reviewed, DONE.** Brief `contract-021`; spec-lint PASS `@6c6373a5`. Step-2.5 APPROVED (strong design — impl added 2 tests beyond the outline + folded the `num_unindexed==0` monitor into the gate + the `upsert_batch(sha_tag=)` refinement). Step-9 SHIP. Impl committed `ad8972f` + session doc `e8cd7f9`.
- **Doc routing (this `/orchestrate-end`):** LESSON 18 (the reusable-rig pattern) + `core/CLAUDE.md` index row (worktree); §11 O-FED annotation + §6 PROPOSED budget-envelope note (root/main `ARCHITECTURE.md`); tick 0.3/0.4 + Acceptance(0) + Log + Carry-forward (root/main `IMPLEMENTATION_PLAN.md`).

## Decisions made

- **D-A17 (owner-approved):** spike 0.4 depth = **scope B** — the reusable rig + real instrumentation + a Fake target + a documented methodology + best-effort local numbers pre-fork; the authoritative real reference-Mac bake-off (real `lancedb` + embedding model + multi-repo corpus) defers to Phase 3. O-LANCE-BAKEOFF acceptance unknown = deferred, not dropped.
- **D-A18 (orchestrator, lead-noted; §18-touching):** spike 0.3 re-scoped to a schema-faithful synthetic corpus after the safety classifier (correctly) blocked an ad-hoc CodeGraph install — aligned with §18 "supply-chain pin-by-hash, fail-closed" (CodeGraph is provisioned via `setup`, not ad-hoc-installed in a spike). Real validation deferred to provisioning.
- **The 0.3/0.4 split** (0.3 investigation, orchestrator-run; 0.4 TDD rig, implementer) — lead-approved as the orchestrator's call; matches the 0.1/0.2 precedents + parallelizes the two-agent team.
- **LESSON 18** banked: a reusable measurement RIG ships real instrumentation + a Fake target + `PROPOSED_*` envelope constants; authoritative numbers land where the real backend lands.

## Decisions explicitly NOT made (deferred / handed off)

- The §11 federation-router merge policy (decision → Phase-6 track; spike recommendation recorded).
- The authoritative §6 maintenance budget numbers (→ Phase 3 real run; `PROPOSED_*` placeholders only).
- HITL-parked (unchanged): D-A2 (0.5 notarization live step), D-A3 (`/preflight.md` mypy), D-A11 (EvidenceType/IdKind membership before spine Phase 4), D-A5/A6 (per-sink redaction strictness + 95/5 threshold at 2.3).

## Fork-gate merge mechanic (topology-aware)

`track/contract` was **33 ahead / 10 behind** `main` (merge-base `f8703286`). The 10 main-only commits are the lead's living-doc edits (`IMPLEMENTATION_PLAN.md` / `ARCHITECTURE.md` / decision log / team-handoffs). The **only overlapping (conflict) file is `IMPLEMENTATION_PLAN.md`** — main is canonical for it; the worktree's copy is the known-stale original. `ARCHITECTURE.md` changed on main only → clean. All code/briefs/sessions/probes changed on track only → clean union. The merge resolves `IMPLEMENTATION_PLAN.md` to main's living version; everything else unions cleanly.

## Open follow-ups (carried into `/phase-exit 1` + the contract→spine handoff)

- **★SAFETY fork obligations (MUST land in the contract→spine handoff):** **D-A13 / Task 2.S** (the §14 INV-allowlist FULL runtime proof + real `StandaloneHost`; Phase 2) and **D-A14 / Task 4.2** (CodeGraph CLI argv-hardening — the PRIMARY query-arg injection defense; Phase 4).
- **Phase-6 federation:** the 0.3 recommendation + the 2 HIGH real-data risks; run a real-CodeGraph validation pass once provisioned.
- **Phase-3:** the authoritative O-LANCE-BAKEOFF real bake-off run (reuse the rig unchanged; set the real budget numbers).

**Round seal:** implementer slice `ad8972f` + impl session `e8cd7f9`; orchestrator round commit (this doc + `federation_spike.md` + brief `contract-021` + LESSON 18) on `track/contract`; root/main annotations on `main`. Then `/phase-exit 1` → merge = the fork gate.
