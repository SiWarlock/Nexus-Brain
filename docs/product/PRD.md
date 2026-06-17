# Nexus Brain PRD v2 — Platform-Native Memory, Reasoning, and Action Planning Engine

> Status: Draft v2 · Source input: `PRD_ROUGH_DRAFT.md`, `requirements/ONBOARDING_AND_DOC_LIFECYCLE.md`, `research/RESEARCH_DOSSIER.md`, and product-planning discussion · Date: 2026-06-06 · Aligned to the NexusOps platform contract (`CONTRACT_VERSION 0.34.0`) on 2026-06-15  
> Working product relationship: Nexus Brain is standalone first, but designed as the memory/reasoning/action-planning service for **NexusOps** — a desktop-first, local-runtime AI engineering control plane built alongside it as a sibling product. (The platform-side Brain seam, NexusOps Phase 8, is deferred/unbuilt, so the contracts below are a *frozen forward target*, not a live integration.)

---

## 1. Executive Summary

Nexus Brain is a **local-first, multi-project memory, retrieval, reasoning, and action-planning engine** for software projects. It indexes code, documentation, architecture artifacts, implementation plans, git history, pull requests, and local Claude/Codex session history so a developer can ask questions such as:

- “When did we implement feature Y?”
- “Why did we choose this architecture?”
- “Which session changed this file?”
- “What code, commits, PRs, docs, and tasks are relevant to this decision?”
- “What should I work on next?”
- “Start the next backend implementation task, using the project workflow.”

The original rough PRD correctly positions Nexus Brain as a local-first, portfolio-scale, docs+code-fused knowledge platform where `file:line` anchors are the trust primitive. V2 preserves that thesis and adds the missing future-platform contract:

1. Nexus Brain remains usable as a standalone CLI/MCP-backed product.
2. Nexus Brain becomes platform-native through shared object IDs, events, workflow-pack awareness, and an Action Gateway.
3. Nexus Brain evolves from passive Q&A into an **action-capable co-pilot** that can plan, draft, and request platform actions with explicit permissions and auditability.
4. Nexus Brain treats cc-crew as one privileged workflow producer, not a precondition.
5. Nexus Brain understands the difference between reusable workflow templates and project-specific personalized workflow instances.

The short version:

> Nexus Brain understands project memory. The NexusOps platform executes project operations. Nexus Brain may plan and request actions, but the platform owns permissions, execution, credentials, terminals, worktrees, and audit logs.

---

## 2. Product Positioning

### 2.1 What Nexus Brain Is

Nexus Brain is a local-first project intelligence engine that combines:

- Code indexing
- Documentation indexing
- Session memory
- Git/commit provenance
- Plan/task awareness
- Workflow-pack awareness
- Evidence-backed Q&A
- Drift/staleness detection
- Historical implementation lookup
- Action planning
- Platform (NexusOps) action requests

### 2.2 What Nexus Brain Is Not

Nexus Brain is not:

- A full IDE
- A terminal multiplexer
- A git client
- A cloud SaaS
- A replacement for Claude Code, Codex, or CodeGraph
- A replacement for cc-crew
- A workflow orchestrator by itself
- A system that silently mutates code, tickets, git state, or host config

It can **orchestrate certain owned documentation refresh workflows** and later **request platform actions**, but execution of operational actions belongs to the platform’s permissioned action layer.

### 2.3 Relationship to NexusOps

NexusOps — a desktop-first, local-runtime AI engineering control plane ("air-traffic control for AI coding agents"): a macOS Tauri client plus a detached Rust daemon that is the single, audited mutator of all state, supervising Claude Code + Codex across local projects — is the AI coding operations console that manages:

- Projects
- Sessions
- Terminals
- Worktrees
- Git actions
- Pull requests
- Tickets
- Agent teams
- Execution profiles
- Workflow packs
- Code editor/review surfaces
- Human approvals

Nexus Brain is the embedded intelligence layer behind that platform.

The platform asks Nexus Brain:

- “What does this project know?”
- “What changed and why?”
- “Which task/session/PR/commit is this related to?”
- “What action should happen next?”

Nexus Brain asks the platform:

- “May I create a session?”
- “May I create a worktree?”
- “May I start `/team-start` for this plan track?”
- “May I link this Linear issue to this plan task?”
- “May I update the implementation plan?”

---

## 3. Product Thesis

AI coding agents create a new project-management problem: developers are no longer only writing code, they are supervising work performed by many local and remote agents across many repos, sessions, tickets, worktrees, branches, PRs, and documents.

The hardest part is not merely search. The hardest part is **memory with provenance**:

- What happened?
- When did it happen?
- Which agent/session did it?
- Which task caused it?
- Which files changed?
- Which commit/PR carried it?
- Which architectural decision governed it?
- Which docs are now stale?
- What should happen next?

Nexus Brain’s thesis:

> A useful AI project memory system must treat code, docs, sessions, commits, tasks, and workflow artifacts as connected evidence, not as independent chunks in a vector store.

---

## 4. Goals

### G1. Evidence-backed project Q&A

Every answer should cite the evidence it used, including file paths, line ranges, commits, PRs, session IDs, plan anchors, architecture anchors, and freshness/staleness metadata.

### G2. Historical implementation memory

Nexus Brain should answer temporal/provenance questions such as:

- “When did we implement X?”
- “How did we implement X?”
- “Why did we choose Y?”
- “Which session fixed bug Z?”
- “What was I doing when this file last changed?”

### G3. Local-first privacy

Indexes, embeddings, transcript processing, and code graph data should remain local by default. Sensitive inputs, especially transcripts, require stricter opt-in and redaction.

### G4. Portfolio-wide project intelligence

Nexus Brain should support many local projects, with per-project stores and federated query. It should degrade gracefully if cross-repo symbol resolution is unavailable.

### G5. Source-agnostic documentation ingestion

Nexus Brain should work on any repo. cc-crew outputs are the richest input tier, but not a requirement.

### G6. Workflow-pack awareness

Nexus Brain should understand workflow packs, workflow instances, implementation plans, commands, skills, subagents, and generated/personalized scaffolding.

### G7. Action planning

Nexus Brain should produce actionable plans that NexusOps can execute through its permissioned Action Gateway.

### G8. Trust through freshness and drift detection

Nexus Brain should surface stale docs, stale anchors, stale graph state, partial indexes, and low-confidence session/commit associations. Silent degradation is not acceptable.

---

## 5. Non-Goals

### NG1. Nexus Brain does not directly own operational execution

It does not directly start terminals, create worktrees, merge PRs, delete branches, edit credentials, or kill sessions. Those are NexusOps platform actions.

### NG2. Nexus Brain does not require cc-crew

It can ingest cc-crew richly, but must still work on repos with ordinary README files, ADRs, architecture docs, generated docs, or code-only structure.

### NG3. Nexus Brain does not silently mutate user files

Any write to docs, plans, tickets, git state, or workflow files must be explicit, previewed, and audited.

### NG4. Nexus Brain is not a generic enterprise RAG tool

Its core domain is software project memory: code, docs, sessions, commits, PRs, implementation plans, and engineering decisions.

### NG5. Nexus Brain is not a hosted SaaS by default

The default posture is local-first. Future sharing/sync capabilities must preserve explicit trust boundaries.

---

## 6. Target Users

### Persona A — Portfolio solo developer

Runs many local projects, often with Claude Code/Codex sessions and project-specific workflow scaffolding. Needs to remember what happened across projects and delegate work safely.

### Persona B — New teammate / future collaborator

Needs a cited, trustworthy guided understanding of a project without reading every file and stale doc manually.

### Persona C — Technical lead / reviewer

Needs to understand architectural drift, PR impact, why decisions were made, and how current changes relate to previous work.

### Persona D — Future NexusOps platform user

Supervises many AI coding agents and uses Nexus Brain inside the platform to ask, plan, dispatch, review, and coordinate work.

---

## 7. Core Product Concepts

### 7.1 Anchor

A typed `file:line` or `file:line-range` edge between prose and code.

Anchors are not plain text. They are the primary trust primitive.

Fields:

- `anchor_id`
- `project_id`
- `source_file`
- `source_span`
- `target_path`
- `target_line_start`
- `target_line_end`
- `target_symbol`
- `state: live | stale | moved | unknown`
- `last_resolved_sha`
- `confidence`

### 7.2 Evidence Chip

A user-visible reference attached to an answer or action plan.

Evidence chip types:

- Code file/line
- Documentation section
- Architecture anchor
- Plan task
- Commit
- Pull request
- Linear ticket
- GitHub issue
- Session episode
- Agent team run
- Decision record
- Test result
- Workflow manifest

> **NexusOps alignment (integration mode).** When integrated, an evidence chip serializes to the platform's `EvidenceRef` (a `{type, label, resource_ref?, confidence?}` value), and `type` must be one of the **closed 11-value `EvidenceType`** enum: `project_brain_evidence_item, file_anchor, architecture_anchor, plan_task, session_episode, commit, pr_check, terminal_event, ticket, workflow_manifest, user_instruction`. Mapping: *Code file/line* → `file_anchor`; *Documentation section* → `architecture_anchor`/`file_anchor`; *Linear ticket* **and** *GitHub issue* both collapse to `ticket`; *Pull request* surfaces as `pr_check`; add `terminal_event` and `user_instruction`. *Agent team run* and *Decision record* are **`ResourceRef` references (a `ResourceType`), not `EvidenceType`s**; *Test result* has no platform-backed evidence type (surface it as a `terminal_event`/`pr_check`). Freshness/provenance render via the 5-state freshness lifecycle (§11.3). In **standalone** mode, Nexus Brain may keep the richer chip vocabulary internally and serialize down to this enum only at the seam.

### 7.3 Memory Source

An indexed input source.

Types:

- Code
- README
- Architecture docs
- ADRs
- Planning docs
- `IMPLEMENTATION_PLAN.md` (the cc-crew task tracker; legacy name `MVP_TASKS.md`)
- Layer docs
- Lessons
- PRs
- Commits
- Claude Code transcripts
- Codex transcripts
- Session summaries
- Workflow manifests
- Workflow commands
- Ticket metadata

### 7.4 Episode Card

A redacted, summarized representation of a Claude/Codex session. Raw transcripts are not embedded by default.

Fields:

- `episode_id`
- `session_id`
- `project_id`
- `tool: claude | codex | other`
- `model`
- `start_ts`
- `end_ts`
- `branch`
- `worktree_path`
- `user_intents`
- `files_touched`
- `key_decisions`
- `errors_fixed`
- `outcome_summary`
- `linked_commits`
- `linked_tasks`
- `privacy_redacted`

> **NexusOps alignment.** The EpisodeCard is **Brain-owned** (NexusOps's SOM models it as belonging to the ProjectBrainIndex), produced via the `brain.summarize_session` action; the platform does not mint it. Keep raw transcripts unembedded and `thinking` blocks excluded (matches §15 redaction-before-embed). When integrated, `session_id`/`project_id`/`worktree_path`/`linked_commits`/`linked_tasks` reference platform objects by **shared ID**; align field names to the platform's session vocabulary at the seam.

### 7.5 Implementation Plan

A structured internal representation of an implementation plan file such as `IMPLEMENTATION_PLAN.md` (legacy name `MVP_TASKS.md`).

Fields:

- `plan_id`
- `project_id`
- `source_path`
- `phases`
- `tracks`
- `tasks`
- `anchors`
- `architecture_refs`
- `linked_sessions`
- `linked_prs`
- `linked_issues`
- `status`

### 7.6 Plan Task

A parsed task from an implementation plan.

Fields:

- `plan_task_id`
- `project_id`
- `plan_id`
- `phase`
- `track`
- `title`
- `description`
- `source_anchor`
- `architecture_anchor`
- `acceptance_criteria`
- `dependencies`
- `status`
- `linked_linear_issue_id`
- `linked_github_issue_number`
- `linked_sessions`
- `linked_worktrees`
- `linked_prs`

### 7.7 Workflow Pack

A reusable template/package of workflow conventions, commands, skills, subagents, plan parsers, launch recipes, and upgrade rules.

A workflow pack is not necessarily ready to run in a project. Some workflow packs must be personalized.

Fields:

- `workflow_pack_id`
- `name`
- `source_repo`
- `source_ref`
- `templates`
- `commands`
- `skills`
- `subagents`
- `hooks`
- `detectors`
- `plan_parsers`
- `personalization_flow`
- `upgrade_flow`
- `launch_recipes`

### 7.8 Workflow Instance

A project-specific generated/personalized workflow created from a workflow pack.

Fields:

- `workflow_instance_id`
- `workflow_pack_id`
- `project_id`
- `status`
- `manifest_path`
- `generated_from_sha`
- `last_upgraded_from_sha`
- `mode`
- `track`
- `code_areas`
- `task_tracker_path`
- `architecture_doc_path`
- `available_commands`
- `generated_files`
- `customization_ledger`

Lifecycle (the **12 frozen R-7 states**, mirroring NexusOps `shared/src/status.rs`):

- `not_detected`
- `pack_available`
- `needs_personalization`
- `personalization_in_progress`
- `generated_review_required`
- `active`
- `ready_for_team_run`
- `degraded`
- `drift_detected`
- `upgrade_available`
- `archived` *(terminal)*
- `detached` *(terminal)*

> **NexusOps alignment.** This replaces the earlier ad-hoc set (`available`/`installed`/`detected`/`running` dropped; `available`→`pack_available`; `generated_review_required` and `degraded` added). Team-run-in-progress is **not** an instance state — it is tracked on the `AgentTeam` machine (R-6), not the WorkflowInstance.

### 7.9 Workflow Personalization Run

The process of applying a reusable workflow pack to a concrete project.

Fields:

- `personalization_run_id`
- `workflow_pack_id`
- `project_id`
- `status`
- `inferred_values`
- `unresolved_questions`
- `user_answers`
- `generation_plan`
- `generated_diff`
- `approvals`
- `resulting_manifest`

### 7.10 Action Plan

A proposed set of actions Nexus Brain wants the platform to execute.

Fields:

- `action_plan_id`
- `project_id`
- `user_request`
- `summary`
- `steps`
- `risk_level`
- `required_permissions`
- `evidence`
- `preview`
- `dry_run_result`
- `approval_mode`

> **NexusOps alignment (wire shape).** The above are Nexus Brain's *internal* action-plan fields. When submitted to the platform via `submit_action_plan`, the plan serializes to the **frozen `ActionPlan` shape** (`shared/src/actions.rs`): `{ plan_id (aplan_<ULID>), title, steps: ActionPlanStep[], dependencies: ActionDependency[], overall_risk (0–4), approval_mode }` — there is **no** plan-level `summary`/`user_request`/`evidence`/`preview`/`dry_run_result`. Map the richer fields down: `user_request`/`summary` → the lead `ActionRequest.inputs` (or a Brain-side memo); per-step `preview`/`dry_run_result` → each `ActionPlanStep`/`ActionPreview`; `evidence` → `EvidenceRef[]` on the steps; `required_permissions` → derived by the platform from each step's catalog `locked_risk`. `submit_action_plan` returns a `PlanAck{plan_id,…}`; `requester_type = project_brain`.

---

## 8. Relationship to cc-crew and Workflow Packs

### 8.1 cc-crew Is a Workflow Pack, Not a Required Dependency

The cc-crew scaffold should be modeled as a workflow pack that can produce a project-specific workflow instance. Nexus Brain should understand it, but must not require it.

The product must distinguish:

- **Workflow Pack:** reusable scaffold/template machinery.
- **Workflow Instance:** project-specific generated/personalized scaffold.
- **Workflow Personalization Run:** the process that turns a template into a project-specific instance.

This matters because the scaffold is not ready to run out of the box. It becomes ready after project architecture, task artifacts, and generated/personalized files exist.

### 8.2 cc-crew Detection States

For a project, Nexus Brain should classify cc-crew/workflow state as:

- No workflow detected
- Workflow pack available
- Template files detected
- Needs personalization
- Personalization in progress
- Personalized workflow instance detected
- Active workflow instance
- Ready for `/team-start`
- Drift detected
- Upgrade available

> **NexusOps alignment.** These are Brain-side **detection heuristics**, not the platform's status values. They map onto the 12 frozen `WorkflowInstance` states (§7.8): "No workflow detected"→`not_detected`, "Workflow pack available"→`pack_available`, "Needs personalization"→`needs_personalization`, "Personalization in progress"→`personalization_in_progress`, "Active workflow instance"→`active`, "Ready for `/team-start`"→`ready_for_team_run`, "Drift detected"→`drift_detected`, "Upgrade available"→`upgrade_available`; the platform adds `generated_review_required` and `degraded`. "Template files detected" / "Personalized workflow instance detected" stay Brain heuristics (filesystem signals), not status values.

### 8.3 cc-crew Artifacts to Ingest

Nexus Brain should ingest and understand:

- `.scaffolding/manifest.json`
- `.project-brain/manifest.json`
- `ARCHITECTURE.md`
- `IMPLEMENTATION_PLAN.md` (legacy name: `MVP_TASKS.md`)
- `docs/planning/*.md`
- `docs/layers/**`
- `docs/learn-site/content.json`
- `<area>/LESSONS.md`
- root/per-area `CLAUDE.md`
- `.claude/commands/**`
- `.claude/skills/**`
- `.claude/agents/**`
- `docs/briefs/**`
- `docs/sessions/**`
- `docs/team-handoffs/**`

### 8.4 cc-crew Integration Rules

Nexus Brain may:

- Read cc-crew artifacts.
- Parse implementation plans.
- Parse architecture anchors.
- Parse workflow manifest metadata.
- Index commands, skills, subagents, and generated docs.
- Suggest workflow actions.
- Request platform execution of workflow commands.
- Orchestrate owned doc-refresh loops where explicitly allowed.

Nexus Brain must not:

- Mutate `.scaffolding/manifest.json`.
- Pretend a template is an active workflow instance.
- Auto-run a workflow command without confirmation.
- Auto-overwrite human/foreign docs.
- Create a fake plan/task mapping when confidence is low.

---

## 9. Nexus Brain as an Action-Capable Co-Pilot

### 9.1 The Key Boundary

Nexus Brain can reason and plan. The platform executes.

Nexus Brain owns:

- Understanding
- Retrieval
- Memory
- Evidence
- Reasoning
- Recommendations
- Action planning
- Drafting

The platform owns:

- UI
- Terminals
- Worktrees
- Git commands
- PR creation/merge
- Linear/GitHub mutations
- Claude/Codex session runtime
- Credentials
- Permission prompts
- Audit logs
- Rollback/undo surfaces

### 9.2 Action Modes

#### Mode 1 — Read-only

Nexus Brain answers questions and retrieves evidence. No mutations.

Examples:

- “When did we implement X?”
- “Which session changed this file?”
- “What docs are stale?”

#### Mode 2 — Draft

Nexus Brain drafts content, but does not create or update anything.

Examples:

- Draft a PR description.
- Draft a Linear issue from a plan task.
- Draft a Claude prompt for a task.
- Draft a plan update.

#### Mode 3 — Confirmed Action

Nexus Brain proposes a single action and asks the platform/user for confirmation.

Examples:

- Link a plan task to a Linear issue.
- Create a worktree.
- Create a new session.
- Send a message to an active agent.

#### Mode 4 — Approved Workflow

Nexus Brain proposes a bundled multi-step workflow for approval.

Examples:

- Start the next backend task.
- Fix failing PR checks.
- Start `/team-start` for a plan track.
- Create a PR from completed session changes.

#### Mode 5 — Policy Automation

User-defined policies allow Nexus Brain to request or trigger low-risk actions automatically.

Examples:

- Auto-summarize completed sessions.
- Auto-link commits to sessions when branch naming matches.
- Auto-mark plan tasks as “in review” when a PR opens.

### 9.3 Action Gateway

Nexus Brain must call a typed Action Gateway instead of directly executing operational actions.

Action types (each maps to one of NexusOps's **closed, dotted `action_type` catalog** strings; an unknown `action_type` fails closed → `Deny`):

- Project actions — e.g. `project.rescan`
- Plan actions — e.g. `plan.link_task`
- Session actions — e.g. `session.create`, `session.attach_terminal`, `session.send_message`, `session.pause`, `session.resume`
- Git actions — e.g. `git.status`, `git.diff`, `git.create_worktree`, `git.create_branch`, `git.stage_hunk`
- Code/review actions — e.g. `code.open_file`, `review.request_agent_fix`
- Integration actions — e.g. `github.create_pr`, `github.create_pr_draft`, `linear.link_issue`, `linear.create_issue`, `integration.connect`
- Workflow actions — e.g. `workflow.detect`, `workflow.command.invoke`
- Brain actions — e.g. `brain.ask`, `brain.sync`, `brain.summarize_session`
- Agent team actions — *(P1; the `AgentTeam` machine exists, but `/team-start` orchestration is deferred in the platform MVP)*

> **NexusOps alignment.** Nexus Brain's proposed action set must be a **subset of (or PR'd into) the NexusOps catalog** — it cannot invent types. The earlier **"Documentation lifecycle actions"** namespace is dropped from the MVP: there is no gateway-executable doc-refresh action yet (`brain.refresh_owned_docs` is a risk-3, spec-only, post-MVP idea). Standalone Nexus Brain can run owned-doc refresh in-process; only the *request-the-platform-to-do-it* path needs a catalog type.

Each action must define:

- Action ID
- Inputs
- Required permission
- Risk level
- Preview
- Dry-run behavior
- Expected side effects
- Audit event
- Rollback/undo guidance

### 9.4 Risk Levels

NexusOps classifies every action on an **integer `RiskLevel` 0–4** (the catalog's per-type `locked_risk` is authoritative; these word-labels are display-only). Nexus Brain mirrors that scale:

**Read-only (0)** — auto-execute-eligible; no approval, but still observable:

- Search project
- Open file
- Draft prompt *(Brain-side; not a catalog mutation)*

**Low (1):**

- Link existing objects with confirmation

**Medium (2):**

- Summarize session *(catalog-locked at risk-2 — approval-gated, not Low)*
- Create session
- Create worktree
- Create Linear/GitHub issue
- Update plan task status
- Send message to agent
- Create draft PR

**High (3):**

- Commit changes
- Push branch
- Delete worktree
- Modify workflow files / invoke a workflow command
- Update architecture docs
- Run arbitrary shell command

**Critical (4):**

- Merge to main
- Force push
- Delete branch
- Modify credentials/secrets
- Change global Claude/Codex settings

> **NexusOps alignment.** Only **risk-0** is auto-execute-eligible; **every risk ≥ 1 is audited and policy/approval-gated**, and **risk-4 (critical)** plus non-standing-grant-eligible types (e.g. `workflow.command.invoke`, `git.discard_hunk`, `integration.connect`) are **never approve-all** and are always per-action approved. Nexus Brain itself has **no auto-execute and no non-zero-risk execution path** — it only proposes; the platform owns the final eligibility gate. Brain may **never** set or change an ExecutionProfile (NexusOps safety rule #8).

---

## 10. Functional Requirements

### PB-1. Project Registration and Ingestion

- The system MUST support adding a project from a local repo path.
- The system MUST maintain a project registry.
- The system MUST maintain per-project stores, not one giant shared index.
- The system MUST ingest code and docs even when no workflow scaffold exists.
- The system MUST write its own manifest and not mutate external workflow manifests.

### PB-2. Source-Agnostic Documentation Discovery

- The system MUST discover documentation broadly across markdown, architecture docs, ADRs, READMEs, API specs, docs folders, and code-embedded docs.
- The system MUST classify producers, including cc-crew, human, generated, and unknown.
- The system MUST classify docs as owned, foreign, or supplemental.
- The system MUST support `.brainignore`.

### PB-3. Anchor-Aware Chunking and Drift Detection

- The system MUST parse `file:line` anchors as structured edges.
- The system MUST revalidate anchors against current code.
- The system MUST surface stale anchors.
- The system MUST include drift state in answer provenance.

### PB-4. Retrieval and Answering

- The system MUST support hybrid retrieval.
- The system SHOULD support whole-file hydration when appropriate.
- The system MUST return evidence-backed answers.
- The system MUST distinguish authored plain/deep registers from generated summaries.
- The system MUST refuse or flag unsupported claims according to the grounding policy.

### PB-5. Session Memory

- The system SHOULD ingest Claude Code session history early.
- The system MAY ingest Codex session history after schema association is verified.
- Session ingestion MUST be opt-in per project.
- Session embeddings MUST default to local models.
- Raw transcripts MUST NOT be embedded by default.
- `thinking` blocks MUST be excluded from embeddings.
- Session summaries MUST become episode cards.
- Commit linking MUST carry confidence.

### PB-6. Implementation Plan Awareness

- The system MUST parse implementation plan files such as `IMPLEMENTATION_PLAN.md` (and the legacy `MVP_TASKS.md`) when present.
- The system SHOULD extract phases, tracks, tasks, anchors, acceptance criteria, dependencies, and architecture refs.
- Plan tasks SHOULD be linkable to Linear issues, GitHub issues, sessions, branches, worktrees, PRs, and commits.
- The system SHOULD preserve manual linking before attempting automated sync.

### PB-7. Workflow Pack Awareness

- The system MUST distinguish workflow packs from workflow instances.
- The system MUST detect whether a project has a personalized workflow instance.
- The system MUST not assume template availability equals readiness.
- The system SHOULD index workflow commands, skills, subagents, hooks, and manifests.
- The system SHOULD expose workflow readiness and drift status to the platform.

### PB-8. Action Planning

- The system MUST be able to produce action plans with evidence.
- The system MUST not execute privileged actions directly.
- The system MUST call the platform Action Gateway for operational side effects.
- The system MUST support read-only, draft, confirmed-action, approved-workflow, and policy-automation modes.

### PB-9. Platform Event Consumption

Nexus Brain SHOULD be able to consume NexusOps platform events. Events arrive via the platform's **redacted transactional outbox** — an at-least-once push where restricted/secret fields are stripped and `object_refs` are preserved by shared ID — **not** a raw event tail or the UDS subscribe stream. Order by `seq`; dedup on `event_id`/`idempotency_key`; tolerate unknown/newer `event_type`/`event_version` (deny-unknown-fields applies to known types). Representative events (names map to the as-built EventTypeRegistry):

- Project added / rescanned (`ProjectRescanned`)
- Workflow pack detected (`WorkflowDetected`)
- Workflow instance personalized
- Plan task linked (`PlanTaskLinked`)
- Session started / ended (`SessionStarted`, plus the session lifecycle events)
- Agent team started
- Command invoked (`WorkflowCommandInvoked`)
- Worktree created (`WorktreeCreated`)
- Commit created
- Pull request synced (`PullRequestSynced` — PR opened/merged surface through this, not separate Opened/Merged events)
- Approval requested / resolved (`ActionApprovalRequested`, `…Approved`/`…Denied`/`…Expired`)
- Decision saved

> **NexusOps alignment.** **"Session summary created" is removed** — Nexus Brain *owns* session summaries / episode cards (it produces them via the `brain.summarize_session` action), so it does not *consume* them as a platform event. Reverse direction: the Brain emits a ProjectBrain status report plus MCP notifications that the platform maps (via `BrainEventMapping`) to `BrainIndexStarted/Completed/Failed` and `BrainSourceIngested` events.

### PB-10. Evidence and Provenance

Every answer and action plan SHOULD include a provenance packet with:

- Project ID
- Source IDs
- File paths and lines
- Commit SHAs
- Session IDs
- Timestamps
- Ingested-from SHA
- Index freshness
- Confidence markers
- Drift/staleness markers
- Low-confidence association markers

### PB-11. Safety, Privacy, and Consent

- Raw code and indexes stay local by default.
- Session ingestion is opt-in and stricter than docs/code ingestion.
- Host-config mutations must be idempotent, reversible, and consented.
- Nexus Brain action requests must be audited.
- High-risk and critical actions require explicit confirmation.
- Secret and PII redaction must happen before embedding and before cloud-bound generation.

---

## 11. Embedded Platform UX Requirements

When Nexus Brain is embedded in NexusOps, it should appear as a persistent drawer.

### 11.1 Drawer Modes

- Ask
- Plan
- Review
- Actions
- Decisions
- Memory

> **NexusOps alignment.** Renamed "Dispatch" → **Actions** to match the platform's §11.5 drawer mode set (`Ask, Plan, Review, Decisions, Memory, Actions`).

### 11.2 Scope Selector

The drawer should support scoped questions:

- Entire portfolio
- Current project
- Current session
- Current worktree
- Current PR
- Current file
- Current selection
- Current plan task

> **NexusOps alignment.** When integrated, scope chips **constrain retrieval** (a filter parameter on the Brain query), and the platform drawer exposes a **7-chip set**: `Entire project, Current session, Current file, Current diff, Current PR, Current plan task, Current agent team`. *Entire portfolio*, *Current worktree*, and *Current selection* are **standalone-only supersets** (the standalone product is portfolio-first); *Current file*+*Current selection* fold into the platform's `Current file`, and the seam adds `Current diff` + `Current agent team`.

### 11.3 Answer UI

Answers should include:

- Direct answer
- Evidence chips
- Freshness/staleness banner
- Confidence markers
- Related sessions
- Related commits/PRs
- Related plan tasks
- Suggested next actions

### 11.4 Action Plan UI

Nexus Brain action responses should show:

- Proposed steps
- Risk level
- Required permissions
- Expected artifacts
- Preview/diff when applicable
- Approve all
- Approve step-by-step
- Edit plan
- Cancel

Example:

```text
User: Start the next backend task using cc-crew.

Brain:
I found the next unstarted backend task:
Phase 2.3 — Auth callback persistence
Architecture: ARCHITECTURE.md §Auth Flow
Workflow: cc-crew active instance
Command: /team-start backend

Proposed action plan:
1. Create worktree agent/p2-auth-callback
2. Start Claude Code team session using execution profile Claude Max Main
3. Send /team-start backend
4. Link agent team to plan task Phase 2.3
5. Open Agent Team View

Risk: Medium
Needs approval: worktree creation, session start, command invocation

[Edit Plan] [Approve Step-by-Step] [Approve All]
```

---

## 12. Standalone Product Scope

Nexus Brain should be useful before the full platform exists.

Standalone v1 should support:

- CLI setup/status/add/sync
- Local project registry
- Source-agnostic docs/code ingestion
- Anchor-aware chunking
- Local vector/index store
- MCP query server
- Evidence-backed Q&A
- Claude Code session-memory ingestion, opt-in
- Initial implementation-plan parsing
- cc-crew artifact recognition
- Drift/freshness reporting
- Minimal web/dev console

The standalone product should expose APIs that later map cleanly into the platform.

---

## 13. NexusOps Integration Scope

When integrated with NexusOps, Nexus Brain should additionally support:

- Shared object IDs
- Platform event ingestion
- Action planning
- Action Gateway requests
- Workflow Pack/Instance status
- Plan-task-to-session linking
- Plan-task-to-Linear/GitHub linking
- Session/worktree/branch/PR provenance
- Agent team history
- Review/diff explanations
- Human decision ledger
- Action audit trail

---

## 14. Roadmap

### MVP — Standalone Trust Substrate

- Project registry
- Source-agnostic ingest
- Per-project store
- Anchor-aware chunks
- Hybrid retrieval
- Evidence-backed answers
- Freshness/staleness stamps
- Setup/add/status CLI
- Basic MCP server
- Basic Nexus Brain web/dev console

### P1 — Session Memory and Workflow Awareness

- Claude Code session ingestion
- Episode cards
- Session Q&A
- Implementation plan parser
- cc-crew workflow instance detector
- Workflow Pack/Instance model
- Manual plan-task linking
- Doc drift radar
- Owned-doc refresh proposal flow

### P2 — Platform-Native Action Planning

- Shared platform object IDs
- Event ingestion
- Action Gateway client
- Action plan generation
- Nexus Brain drawer UX
- Plan task → session/action workflows
- `/team-start` action plans
- PR/diff review explanations
- Linear/GitHub linking plans

### P3 — Full Provenance and Cross-Tool Memory

- Codex session ingestion after association validation
- Commit-link confidence model
- Agent team provenance
- PR/issue/ticket provenance
- Decision ledger
- Since-you-left summaries
- Cross-project impact spike

---

## 15. Success Metrics

### Trust

- % of served claims with evidence chips
- Citation precision
- Stale-anchor false-confidence rate
- Low-confidence association surfacing rate
- Grounding-gate intervention rate

### Memory Utility

- % of questions answered with relevant session/commit/PR provenance
- Time to find “when/how did we implement X?”
- Déjà-vu hit rate across projects
- User-rated usefulness of evidence chips

### Freshness

- Index lag after file save
- Git-hook backstop convergence
- Drift detection latency
- Time to first grounded answer after project add

### Platform Readiness

- % of Nexus Brain answers that include shared object IDs
- % of action plans that can be executed through the Action Gateway
- % of sessions linked to tasks/worktrees/branches/PRs
- % of workflow instances correctly classified

### Safety

- Session-ingestion opt-in compliance
- Secret/PII redaction findings
- High-risk action confirmation rate
- Unauthorized mutation incidents, target zero

---

## 16. Open Questions

> Several questions below were **decided platform-side** when NexusOps ran `/arch-finalize` (these planning docs predate it). Those are marked **[RESOLVED — NexusOps]** with a citation and are no longer open. The rest remain Nexus Brain's own calls.

1. **[RESOLVED — owner, D-19]** Product name = **Nexus Brain** (short: **Nexus**). The integration-seam name remains **Project Brain** (actor `project_brain`) per `MAIN_PLATFORM_INTERFACE.md`.
2. **[RESOLVED — NexusOps]** Parent platform name = **NexusOps** (`NexusOps/ARCHITECTURE.md:1`, root `CLAUDE.md`; crate `nexusops_shared`).
3. **[OPEN]** Which vector store should be locked for MVP? *(RESEARCH §1 leans LanceDB; Brain-internal and platform-agnostic.)*
4. **[OPEN, leaning resolved]** Python-first CLI, Node wrapper, or both? *(RESEARCH §5 and the platform's decided Python/FastMCP sidecar both point to **Python-first** for the engine + MCP server; the standalone UI stack is a separate decision — see §17 / the open decisions.)*
5. **[OPEN]** How much cc-crew parsing should be hardcoded vs provided by a workflow-pack parser?
6. **[RESOLVED — NexusOps]** Minimum-viable Action Gateway schema = the **frozen §6.2 family** in `shared/src/actions.rs` — `ActionRequest`, `ActionPlan` (+`ActionPlanStep` +`ActionDependency`), `ActionPreview`, `Approval`, `ActionResult`, `PolicyDecision`, `ResourceRef`, `EvidenceRef`; `RiskLevel` integer 0–4; `ApprovalMode {approve_all, step_by_step, mixed, blocked}`; two mutation entrypoints `submit_action` / `submit_action_plan` over the UDS `GatewayPort`. Generate Pydantic from the published JSON-Schema; do not hand-author. *(Caveat: NexusOps Phase 8 / `BrainEventMapping` is deferred, so co-design the Brain-specific wire details against this frozen base.)*
7. **[RESOLVED — NexusOps]** Which actions auto-execute under policy → only **risk-0** is auto-execute-eligible; every **risk ≥ 1** is audited + policy/approval-gated; Brain may never set/change an ExecutionProfile (safety rule #8). (§9.4)
8. **[RESOLVED — NexusOps]** What always requires confirmation → **risk-4 (critical)** and non-standing-grant-eligible types (`workflow.command.invoke`, `git.discard_hunk`, `integration.connect`, …) are never approve-all and are always per-action approved. (§6.2; `catalog.rs`)
9. **[RESOLVED — NexusOps]** Own UI / sidecar form → ADR-005: a **stdio-MCP sidecar** (Python/FastMCP 3.x), daemon-owned lifecycle, opens no port (fallback: FastMCP streamable-HTTP on `127.0.0.1` + per-launch loopback token). **Standalone**, Nexus Brain owns its own CLI + UI; **integrated**, it surfaces as the §11.5 NexusOps drawer. *(Replaces the old "embedded intelligence layer / expose APIs only" framing.)*
10. **[OPEN]** How should plan-task-to-Linear linking store mappings?
11. **[OPEN]** How should workflow personalization runs be captured and replayed?
12. **[OPEN]** How should transcript redaction be tested?
13. **[RESOLVED — NexusOps]** Event schema = the **frozen `EventEnvelope`** (R-3) — 16 required fields, ordered by `seq` (not `occurred_at`), deny-unknown-fields, closed `ActorType`(10)/`SourceType`(15)/`Sensitivity`(5)/`RedactionStatus`(2) enums, edges via `object_refs[]` — published as `nexusops-contract.schema.json` at `CONTRACT_VERSION 0.34.0`. Brain must tolerate unknown/newer `event_version`/`event_type`. (`shared/src/event_envelope.rs`; ARCH §7.1)

---

## 17. Recommended Decision Updates

### Decision 1 — Keep Nexus Brain standalone, but platform-native

Nexus Brain should remain independently useful as a local memory engine, but it must use shared IDs and integration contracts that NexusOps can consume.

### Decision 2 — Add an Action Planner, not direct execution

Nexus Brain should become action-capable through an Action Gateway. It should not directly mutate operational state.

### Decision 3 — Model cc-crew as a Workflow Pack

cc-crew should be supported as a privileged Workflow Pack with rich parsers and launch recipes, but not required.

### Decision 4 — Distinguish Workflow Pack from Workflow Instance

A template repo is not the same as a personalized, ready-to-run project workflow.

### Decision 5 — Start Linear sync as linking

Plan task ↔ Linear/GitHub linking should come before one-way creation or bidirectional sync.

### Decision 6 — Make evidence chips a core UX primitive

Every meaningful answer and action plan should show the exact code/docs/session/commit/PR evidence behind it.

---

## 18. Appendix — Example Nexus Brain Answer

User:

```text
For Project X, when and how did we implement feature Y?
```

Answer shape:

```text
Feature Y was implemented during the Phase 2 auth work, primarily in the Claude Code session `claude-auth-impl-2026-03-12`.

Timeline:
- Plan source: IMPLEMENTATION_PLAN.md Phase 2.3
- Architecture anchor: ARCHITECTURE.md §Auth Callback Flow
- Session: Claude Code / Opus / branch agent/p2-auth-callback
- Commit: abc123, confidence likely
- PR: #84
- Main files: auth/callback.ts, session/store.ts

How it was implemented:
The session added the callback handler, persisted the provider token, and updated session state refresh logic. Tests were added in auth/callback.test.ts.

Evidence:
[Commit abc123] [PR #84] [Session episode] [IMPLEMENTATION_PLAN Phase 2.3] [ARCHITECTURE §Auth] [auth/callback.ts:42-118]

Freshness:
Grounded at repo SHA def456. No stale anchors detected. Session-to-commit link confidence: likely.
```

---

## 19. Appendix — Example Action Plan

User:

```text
Start the next backend task.
```

Nexus Brain plan:

```text
I found the next unstarted backend task: Phase 2.3 — Auth callback persistence.

The cc-crew workflow instance is active and ready for team runs.

Proposed actions:
1. Create worktree agent/p2-auth-callback from main.
2. Start a Claude Code session using execution profile Claude Max Main.
3. Invoke /team-start backend.
4. Link the resulting agent team to PlanTask phase-2-3-auth-callback.
5. Open the Agent Team View.

Risk: Medium.
Requires confirmation for worktree creation, session start, and command invocation.
```

Platform executes only after user approval.

