# Project Brain PRD v2 — Platform-Native Memory, Reasoning, and Action Planning Engine

> Status: Draft v2 · Source input: `PRD.md`, `onboarding-and-doc-lifecycle.md`, `RESEARCH(2).md`, and product-planning discussion · Date: 2026-06-06  
> Working product relationship: Project Brain is standalone first, but designed as the memory/reasoning/action-planning service for the future AI coding operations platform.

---

## 1. Executive Summary

Project Brain is a **local-first, multi-project memory, retrieval, reasoning, and action-planning engine** for software projects. It indexes code, documentation, architecture artifacts, implementation plans, git history, pull requests, and local Claude/Codex session history so a developer can ask questions such as:

- “When did we implement feature Y?”
- “Why did we choose this architecture?”
- “Which session changed this file?”
- “What code, commits, PRs, docs, and tasks are relevant to this decision?”
- “What should I work on next?”
- “Start the next backend implementation task, using the project workflow.”

The original rough PRD correctly positions Project Brain as a local-first, portfolio-scale, docs+code-fused knowledge platform where `file:line` anchors are the trust primitive. V2 preserves that thesis and adds the missing future-platform contract:

1. Project Brain remains usable as a standalone CLI/MCP-backed product.
2. Project Brain becomes platform-native through shared object IDs, events, workflow-pack awareness, and an Action Gateway.
3. Project Brain evolves from passive Q&A into an **action-capable co-pilot** that can plan, draft, and request platform actions with explicit permissions and auditability.
4. Project Brain treats cc-crew as one privileged workflow producer, not a precondition.
5. Project Brain understands the difference between reusable workflow templates and project-specific personalized workflow instances.

The short version:

> Project Brain understands project memory. The AgentOps platform executes project operations. Project Brain may plan and request actions, but the platform owns permissions, execution, credentials, terminals, worktrees, and audit logs.

---

## 2. Product Positioning

### 2.1 What Project Brain Is

Project Brain is a local-first project intelligence engine that combines:

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
- Future platform action requests

### 2.2 What Project Brain Is Not

Project Brain is not:

- A full IDE
- A terminal multiplexer
- A git client
- A cloud SaaS
- A replacement for Claude Code, Codex, or CodeGraph
- A replacement for cc-crew
- A workflow orchestrator by itself
- A system that silently mutates code, tickets, git state, or host config

It can **orchestrate certain owned documentation refresh workflows** and later **request platform actions**, but execution of operational actions belongs to the platform’s permissioned action layer.

### 2.3 Relationship to the Future Platform

The future platform is an AI coding operations console that manages:

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

Project Brain is the embedded intelligence layer behind that platform.

The platform asks Project Brain:

- “What does this project know?”
- “What changed and why?”
- “Which task/session/PR/commit is this related to?”
- “What action should happen next?”

Project Brain asks the platform:

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

Project Brain’s thesis:

> A useful AI project memory system must treat code, docs, sessions, commits, tasks, and workflow artifacts as connected evidence, not as independent chunks in a vector store.

---

## 4. Goals

### G1. Evidence-backed project Q&A

Every answer should cite the evidence it used, including file paths, line ranges, commits, PRs, session IDs, plan anchors, architecture anchors, and freshness/staleness metadata.

### G2. Historical implementation memory

Project Brain should answer temporal/provenance questions such as:

- “When did we implement X?”
- “How did we implement X?”
- “Why did we choose Y?”
- “Which session fixed bug Z?”
- “What was I doing when this file last changed?”

### G3. Local-first privacy

Indexes, embeddings, transcript processing, and code graph data should remain local by default. Sensitive inputs, especially transcripts, require stricter opt-in and redaction.

### G4. Portfolio-wide project intelligence

Project Brain should support many local projects, with per-project stores and federated query. It should degrade gracefully if cross-repo symbol resolution is unavailable.

### G5. Source-agnostic documentation ingestion

Project Brain should work on any repo. cc-crew outputs are the richest input tier, but not a requirement.

### G6. Workflow-pack awareness

Project Brain should understand workflow packs, workflow instances, implementation plans, commands, skills, subagents, and generated/personalized scaffolding.

### G7. Action planning

Project Brain should produce actionable plans that the future platform can execute through a permissioned Action Gateway.

### G8. Trust through freshness and drift detection

Project Brain should surface stale docs, stale anchors, stale graph state, partial indexes, and low-confidence session/commit associations. Silent degradation is not acceptable.

---

## 5. Non-Goals

### NG1. Project Brain does not directly own operational execution

It does not directly start terminals, create worktrees, merge PRs, delete branches, edit credentials, or kill sessions. Those are future platform actions.

### NG2. Project Brain does not require cc-crew

It can ingest cc-crew richly, but must still work on repos with ordinary README files, ADRs, architecture docs, generated docs, or code-only structure.

### NG3. Project Brain does not silently mutate user files

Any write to docs, plans, tickets, git state, or workflow files must be explicit, previewed, and audited.

### NG4. Project Brain is not a generic enterprise RAG tool

Its core domain is software project memory: code, docs, sessions, commits, PRs, implementation plans, and engineering decisions.

### NG5. Project Brain is not a hosted SaaS by default

The default posture is local-first. Future sharing/sync capabilities must preserve explicit trust boundaries.

---

## 6. Target Users

### Persona A — Portfolio solo developer

Runs many local projects, often with Claude Code/Codex sessions and project-specific workflow scaffolding. Needs to remember what happened across projects and delegate work safely.

### Persona B — New teammate / future collaborator

Needs a cited, trustworthy guided understanding of a project without reading every file and stale doc manually.

### Persona C — Technical lead / reviewer

Needs to understand architectural drift, PR impact, why decisions were made, and how current changes relate to previous work.

### Persona D — Future AgentOps platform user

Supervises many AI coding agents and uses Project Brain inside the platform to ask, plan, dispatch, review, and coordinate work.

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

### 7.3 Memory Source

An indexed input source.

Types:

- Code
- README
- Architecture docs
- ADRs
- Planning docs
- `MVP_TASKS.md`
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

### 7.5 Implementation Plan

A structured internal representation of an implementation plan file such as `MVP_TASKS.md`.

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

Lifecycle:

- `available`
- `installed`
- `detected`
- `needs_personalization`
- `personalization_in_progress`
- `active`
- `ready_for_team_run`
- `running`
- `drift_detected`
- `upgrade_available`
- `archived`
- `detached`

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

A proposed set of actions Project Brain wants the platform to execute.

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

---

## 8. Relationship to cc-crew and Workflow Packs

### 8.1 cc-crew Is a Workflow Pack, Not a Required Dependency

The cc-crew scaffold should be modeled as a workflow pack that can produce a project-specific workflow instance. Project Brain should understand it, but must not require it.

The product must distinguish:

- **Workflow Pack:** reusable scaffold/template machinery.
- **Workflow Instance:** project-specific generated/personalized scaffold.
- **Workflow Personalization Run:** the process that turns a template into a project-specific instance.

This matters because the scaffold is not ready to run out of the box. It becomes ready after project architecture, task artifacts, and generated/personalized files exist.

### 8.2 cc-crew Detection States

For a project, Project Brain should classify cc-crew/workflow state as:

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

### 8.3 cc-crew Artifacts to Ingest

Project Brain should ingest and understand:

- `.scaffolding/manifest.json`
- `.project-brain/manifest.json`
- `ARCHITECTURE.md`
- `MVP_TASKS.md`
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

Project Brain may:

- Read cc-crew artifacts.
- Parse implementation plans.
- Parse architecture anchors.
- Parse workflow manifest metadata.
- Index commands, skills, subagents, and generated docs.
- Suggest workflow actions.
- Request platform execution of workflow commands.
- Orchestrate owned doc-refresh loops where explicitly allowed.

Project Brain must not:

- Mutate `.scaffolding/manifest.json`.
- Pretend a template is an active workflow instance.
- Auto-run a workflow command without confirmation.
- Auto-overwrite human/foreign docs.
- Create a fake plan/task mapping when confidence is low.

---

## 9. Project Brain as an Action-Capable Co-Pilot

### 9.1 The Key Boundary

Project Brain can reason and plan. The platform executes.

Project Brain owns:

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

Project Brain answers questions and retrieves evidence. No mutations.

Examples:

- “When did we implement X?”
- “Which session changed this file?”
- “What docs are stale?”

#### Mode 2 — Draft

Project Brain drafts content, but does not create or update anything.

Examples:

- Draft a PR description.
- Draft a Linear issue from a plan task.
- Draft a Claude prompt for a task.
- Draft a plan update.

#### Mode 3 — Confirmed Action

Project Brain proposes a single action and asks the platform/user for confirmation.

Examples:

- Link a plan task to a Linear issue.
- Create a worktree.
- Create a new session.
- Send a message to an active agent.

#### Mode 4 — Approved Workflow

Project Brain proposes a bundled multi-step workflow for approval.

Examples:

- Start the next backend task.
- Fix failing PR checks.
- Start `/team-start` for a plan track.
- Create a PR from completed session changes.

#### Mode 5 — Policy Automation

User-defined policies allow Project Brain to request or trigger low-risk actions automatically.

Examples:

- Auto-summarize completed sessions.
- Auto-link commits to sessions when branch naming matches.
- Auto-mark plan tasks as “in review” when a PR opens.

### 9.3 Action Gateway

Project Brain must call a typed Action Gateway instead of directly executing operational actions.

Action types:

- Project actions
- Plan actions
- Session actions
- Agent team actions
- Git actions
- Code/review actions
- Integration actions
- Workflow actions
- Documentation lifecycle actions

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

Low-risk:

- Search project
- Open file
- Summarize session
- Draft prompt
- Link existing objects with confirmation

Medium-risk:

- Create session
- Create worktree
- Create Linear/GitHub issue
- Update plan task status
- Send message to agent
- Create draft PR

High-risk:

- Commit changes
- Push branch
- Delete worktree
- Modify workflow files
- Update architecture docs
- Run arbitrary shell command

Critical:

- Merge to main
- Force push
- Delete branch
- Modify credentials/secrets
- Change global Claude/Codex settings

Critical actions should always require explicit user confirmation.

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

- The system MUST parse implementation plan files such as `MVP_TASKS.md` when present.
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

Project Brain SHOULD be able to consume future platform events, including:

- Project added
- Workflow pack detected
- Workflow instance personalized
- Plan task linked
- Session started
- Session ended
- Agent team started
- Command invoked
- Worktree created
- Commit created
- PR opened
- PR merged
- Approval requested
- Approval resolved
- Decision saved
- Session summary created

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
- Project Brain action requests must be audited.
- High-risk and critical actions require explicit confirmation.
- Secret and PII redaction must happen before embedding and before cloud-bound generation.

---

## 11. Embedded Platform UX Requirements

When Project Brain is embedded in the future platform, it should appear as a persistent drawer.

### 11.1 Drawer Modes

- Ask
- Plan
- Review
- Dispatch
- Decisions
- Memory

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

Project Brain action responses should show:

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

Project Brain should be useful before the full platform exists.

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

## 13. Future Platform Integration Scope

When integrated with the platform, Project Brain should additionally support:

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
- Basic Project Brain web/dev console

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
- Project Brain drawer UX
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

- % of Project Brain answers that include shared object IDs
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

1. What should the final Project Brain name be?
2. What should the parent platform name be?
3. Which vector store should be locked for MVP?
4. Should Project Brain ship as Python-first CLI, Node wrapper, or both?
5. How much cc-crew parsing should be hardcoded vs provided by a workflow-pack parser?
6. What is the minimum viable Action Gateway schema?
7. Which actions can Project Brain execute automatically under policy?
8. What should always require user confirmation?
9. Should Project Brain own a minimal UI, or should it only expose APIs until the platform exists?
10. How should plan-task-to-Linear linking store mappings?
11. How should workflow personalization runs be captured and replayed?
12. How should transcript redaction be tested?
13. What exact event schema will the future platform emit?

---

## 17. Recommended Decision Updates

### Decision 1 — Keep Project Brain standalone, but platform-native

Project Brain should remain independently useful as a local memory engine, but it must use shared IDs and integration contracts that the future platform can consume.

### Decision 2 — Add an Action Planner, not direct execution

Project Brain should become action-capable through an Action Gateway. It should not directly mutate operational state.

### Decision 3 — Model cc-crew as a Workflow Pack

cc-crew should be supported as a privileged Workflow Pack with rich parsers and launch recipes, but not required.

### Decision 4 — Distinguish Workflow Pack from Workflow Instance

A template repo is not the same as a personalized, ready-to-run project workflow.

### Decision 5 — Start Linear sync as linking

Plan task ↔ Linear/GitHub linking should come before one-way creation or bidirectional sync.

### Decision 6 — Make evidence chips a core UX primitive

Every meaningful answer and action plan should show the exact code/docs/session/commit/PR evidence behind it.

---

## 18. Appendix — Example Project Brain Answer

User:

```text
For Project X, when and how did we implement feature Y?
```

Answer shape:

```text
Feature Y was implemented during the Phase 2 auth work, primarily in the Claude Code session `claude-auth-impl-2026-03-12`.

Timeline:
- Plan source: MVP_TASKS.md Phase 2.3
- Architecture anchor: ARCHITECTURE.md §Auth Callback Flow
- Session: Claude Code / Opus / branch agent/p2-auth-callback
- Commit: abc123, confidence likely
- PR: #84
- Main files: auth/callback.ts, session/store.ts

How it was implemented:
The session added the callback handler, persisted the provider token, and updated session state refresh logic. Tests were added in auth/callback.test.ts.

Evidence:
[Commit abc123] [PR #84] [Session episode] [MVP_TASKS Phase 2.3] [ARCHITECTURE §Auth] [auth/callback.ts:42-118]

Freshness:
Grounded at repo SHA def456. No stale anchors detected. Session-to-commit link confidence: likely.
```

---

## 19. Appendix — Example Action Plan

User:

```text
Start the next backend task.
```

Project Brain plan:

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

