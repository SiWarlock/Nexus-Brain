# Project Brain ↔ NexusOps Interface Notes v0.2

> **Purpose:** The Project Brain side of the integration seam with the **NexusOps** platform. This is not the full Project Brain PRD (see [`../product/PRD.md`](../product/PRD.md)).
>
> **Status (2026-06-15):** v0.2. The host platform now exists as **NexusOps**; the binding seam is `NexusOps/ARCHITECTURE.md §13.1` plus the frozen `nexusops-shared` crate (`CONTRACT_VERSION 0.34.0`). The platform-side copy of these notes (`NexusOps/docs/architecture/PROJECT_BRAIN_INTERFACE.md`) is the **v0.1 seed** this engine handed to NexusOps's `/arch-draft`; where the two differ, **the platform side is authoritative**.
>
> **Build-state caveat:** NexusOps **Phase 8 (the Brain seam + drawer) is deferred/unbuilt** — there is no `daemon/src/brainclient` yet, and `BrainEventMapping` only freezes at P8.1. So the contracts below are a **frozen forward target co-designed against frozen platform primitives**, not a live integration. Project Brain (the standalone product is named **Nexus Brain**) ships **standalone first**; everything here is "when integrated."

---

## 1. Boundary

NexusOps and Project Brain are built as sibling products with a clean boundary.

```text
Project Brain owns:
  memory · retrieval · evidence · reasoning
  historical implementation questions
  recommendations · action planning · drafting

NexusOps owns:
  desktop UI · local terminals · Claude/Codex sessions
  worktrees · git operations · GitHub/Linear actions
  credentials · permissions · action execution · audit logs
```

Project Brain can plan or request actions, but **all mutations go through NexusOps's Action Gateway** — there is no bypass. This is the platform's **INV-SEC-1** no-bypass invariant, and reason-vs-execute is one of its three architectural laws (ARCH §4.2).

---

## 2. Integration mode

Project Brain stays a standalone, local-first engine and integrates as a **platform-native sidecar**:

- It runs independently for indexing, retrieval, and project Q&A (standalone-first).
- **Runtime (DECIDED — ADR-005):** a **stdio-MCP sidecar** (Python / FastMCP 3.x), **daemon-owned lifecycle**, **opens no port**. Fallback: FastMCP streamable-HTTP on `127.0.0.1` + a per-launch loopback token (the macOS-notarization fallback). The user-installed-CLI path was rejected. *(Drop the old "service / library" framing.)*
- It exposes **MCP tools** (proposals/queries fed into the Gateway as intents via the daemon's `brainclient`) and emits **MCP notifications** (`resources/updated`, `…/list_changed`, Tasks status, ProjectBrain status report) that the platform maps to events via `BrainEventMapping`. Brain is **never the transport** — it submits intents *into* the Gateway methods.
- It uses **shared IDs** for platform objects (§3) and **consumes platform events via the redacted outbox** (§4) when integrated.
- It **never** directly creates terminals, changes git state, modifies tickets, or runs workflow commands outside the Action Gateway.

---

## 3. Shared IDs and references

These **22 identifiers are FROZEN** as the `IdKind` enum (`NexusOps/shared/src/ids.rs`, frozen at contract 0.5), and Project Brain's list matches **1:1**:

```text
workspace_id  project_id  repo_id  worktree_id  branch_name  commit_sha
session_id  agent_team_id  execution_profile_id  workflow_pack_id
workflow_instance_id  workflow_command_id  implementation_plan_id  plan_task_id
architecture_anchor  linear_issue_id  github_issue_number  pr_number
action_request_id  event_id  artifact_id  evidence_item_id
```

**Format:** platform-minted IDs are **prefixed ULIDs** `<prefix><ULID>` (Crockford base32, lexicographically sortable, fail-closed parse) — **16 minted** (e.g. `ws_`, `proj_`, `repo_`, `wt_`, `sess_`, `team_`, `prof_`, `pack_`, `wfi_`, `cmd_`, `evt_`, `act_`, …). The **6 external** IDs (`branch_name`, `commit_sha`, `architecture_anchor`, `linear_issue_id`, `github_issue_number`, `pr_number`) keep native provider values. Note: `aplan_` (ActionPlan) and `appr_` (Approval) are platform-minted but **outside** the frozen 22.

---

## 4. Inputs Project Brain ingests from NexusOps

When integrated, Project Brain ingests or references (all by shared ID):

- Projects and repos · implementation plans and plan tasks · architecture anchors and docs.
- Code and docs · commits and changed files · pull requests (via `PullRequestSynced`) and reviews.
- GitHub issues and Linear tickets · agent-team summaries.
- Workflow-pack metadata and workflow-instance state · decisions · Action Gateway plans/results.
- **Event log entries — delivered via the platform's redacted transactional OUTBOX** (at-least-once push; restricted/secret fields stripped; `object_refs` preserved by shared ID; order by `seq`; dedup on `event_id`/`idempotency_key`). Not a raw tail, not the UDS subscribe stream.

Session summaries / **episode cards are Brain-owned derivations** from consent-gated transcripts (NexusOps SOM §26), produced via `brain.summarize_session` — Project Brain does **not** ingest them as platform events (there is no `SessionSummaryCreated`/`EpisodeCardCreated` event).

---

## 5. Outputs Project Brain provides to NexusOps

- Evidence-backed answers · current-state summaries · historical implementation answers ("when/how did we implement Y?").
- Plan/task recommendations · review explanations · diff explanations · draft PR descriptions · draft task prompts.
- **Action plans** for Action Gateway review (§7).
- **Evidence chips** — each serializes to an `EvidenceRef {type, label, resource_ref?, confidence?}` whose `type` ∈ the closed **11-value `EvidenceType`** (`project_brain_evidence_item, file_anchor, architecture_anchor, plan_task, session_episode, commit, pr_check, terminal_event, ticket, workflow_manifest, user_instruction`); render with the **5-state freshness** lifecycle (ARCH §11.3). Docs surface as `architecture_anchor`/`file_anchor`; Linear+GitHub collapse to `ticket`; PRs surface as `pr_check`.
- **Reverse direction:** a **ProjectBrain status report** (the platform's ~10-token health vocabulary; the platform *derives* `stale` from `brain_status_reported_at`, so Brain emits the other ~9) plus the MCP notifications mapped to `BrainIndexStarted/Completed/Failed` + `BrainSourceIngested`.

---

## 6. Project Brain drawer behavior (NexusOps §11.5 — DECIDED)

NexusOps exposes Project Brain as a drawer / side panel (opened from the TopBar) with modes:

```text
Ask  ·  Plan  ·  Review  ·  Decisions  ·  Memory  ·  Actions
```

Scope chips **constrain retrieval** (a filter parameter on the Brain query):

```text
Entire project · Current session · Current file · Current diff
Current PR · Current plan task · Current agent team
```

The drawer header shows status + grounded-at/staleness + privacy/transport; every substantive answer shows evidence chips and per-answer confidence. This **implies** the Brain query API should accept a retrieval-scope parameter. *(Standalone, Project Brain's own UI may add portfolio / worktree / selection scopes as a superset — it is not constrained by the platform's 7 chips.)*

---

## 7. Action planning flow

```text
User: Start the next backend task.

Project Brain retrieves: current implementation plan, architecture anchors, active
  sessions, workflow-instance state, execution profiles, worktree state, linked tickets.

Project Brain emits an ActionPlan via submit_action_plan (requester_type = project_brain),
  each step wrapping a catalog ActionRequest:
  1. git.create_worktree        agent/p2-backend-auth
  2. session.create             under the Claude Max Main execution profile
  3. plan.link_task             session ↔ PlanTask phase-2-backend-auth
  4. session.send_message       the generated task prompt
  5. session.attach_terminal    open the session terminal

NexusOps: PlanAck → per-step preview + risk (0–4) → user approves (all / step-by-step) →
  executes → emits events → Project Brain indexes the resulting evidence later.
```

---

## 8. Safety requirements

- Project Brain must not silently mutate files, tickets, git state, sessions, or workflow config — **INV-SEC-1** (the platform's no-bypass invariant; safety rule #10: "Brain proposes, never executes").
- Every requested mutation becomes a typed Action Gateway request. Project Brain has **no auto-execute and no non-zero-risk path**: on the integer **`RiskLevel` 0–4** scale, risk-0 is the platform's auto-execute tier and Brain does not own it.
- Project Brain may **never** set or change an ExecutionProfile (safety rule #8 — no silent account-hopping).
- Risk-4 (critical) actions always require explicit human approval; answers and proposed actions cite evidence when available.
- Project Brain respects project privacy policies and transcript-ingestion consent. **When integrated, inputs arrive already redacted** (secrets are `keychain_ref` pointers; the platform's Redactor gates persist + embed + sync). **Standalone, Project Brain runs its own redactor** before embedding / cloud-bound generation.

---

## 9. Architecture decisions (RESOLVED by NexusOps)

The v0.1 "architecture draft implications" are now decided platform-side:

| Question | Resolution | Anchor |
|---|---|---|
| Project Brain service boundary | reason-vs-execute split; Brain = propose-only | ARCH §4.2, §13.1 |
| IPC/API to the platform | stdio-MCP sidecar (FastMCP 3.x), daemon-owned, no port; loopback-HTTP fallback | ADR-005, §13.1 |
| Shared object IDs / ref types | 22 frozen `IdKind` (prefixed-ULID); platform objects referenced as `ResourceRef`/`ResourceType` | §5.2, `shared/src/ids.rs` |
| How Brain consumes the event log | redacted transactional outbox (push, at-least-once, `object_refs` by shared ID) | §13.1, §7 |
| Storing evidence refs back to platform objects | `EvidenceRef` (11-value `EvidenceType`) + `object_refs` by shared ID | `shared/src/actions.rs` |
| How the Gateway accepts Brain plans | `submit_action_plan` → `PlanAck`; `requester_type = project_brain` | §6.1 |
| Unavailable / stale platform data | platform degrades gracefully, never hard-depends on Brain; Brain tolerates unknown/newer events | §13.1 |
| Embedded vs sidecar vs service vs library | **stdio-MCP sidecar, daemon-owned lifecycle** | ADR-005 |

**Still open platform-side (a co-design opportunity, not a settled spec):** Phase 8 and `BrainEventMapping` are deferred and not yet frozen — so the exact `brain.*` catalog wiring, the notification→event mapping, and the drawer details remain a live design surface on **both** sides. Track the `ResourceType` count as a known cross-doc gap (the code carries ~20; ARCH §6.2/Appendix A name 21).
