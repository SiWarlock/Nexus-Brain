# USERS — Nexus Brain

> `/arch-draft` Phase 2 (Users, Actors & Permissions). Mode: Expanded · Posture: Production-grade. Tags: `locked` / `proposed` / `open question`.

## Primary User — Persona A (portfolio solo developer / owner)
- **Role:** solo developer running many local projects, each often with Claude Code / Codex sessions + project-specific workflow scaffolding.
- **Goal:** remember what happened across the portfolio with trustable provenance; ask one question across many repos; safely delegate/plan next work.
- **Context:** local-first, single machine, single OS user. Privacy-sensitive (own code, secrets, transcripts).
- **Pain points:** lost context across repos/sessions/PRs; stale docs; "when/how/why did we do X"; no cross-project memory.
- **Workflow:** `setup` once → `add` repos → ask (embedded agent UI/CLI or external agent over MCP) → opt-in session memory → drift radar.
- **Success state:** a cited, fresh, correct answer in seconds; confidence the citations are live.
- **Failure state:** a confident answer with a stale/wrong citation (trust collapse); a silent mutation; a leaked secret in the index.

## Secondary / Future Users
- **Persona B — new teammate / collaborator:** needs a cited guided understanding without reading every file. (Standalone read use; future shared/sync is a non-goal now.)
- **Persona C — tech lead / reviewer:** drift, PR impact, "why" decisions, how current change relates to prior work.
- **Persona D — future NexusOps platform user:** uses Nexus Brain *inside* NexusOps (the drawer) to ask/plan/review — propose-only.

## Operators / Admins
For the standalone MVP, the **owner is also the operator** (single-user, local). Operational surface = the `setup`/`add`/`sync`/`status` CLI + a local service manager (launchd/systemd `--user`) managing the federation router + per-project workers.

## Non-Human Actors
| Actor | Role |
|---|---|
| **Embedded agent** | Frontier-model (Claude API) loop behind the standalone chat UI/CLI; a client of the retrieval core. |
| **External agents** | Claude Code / Codex / CI driving the **MCP server** (retrieval tools). |
| **Federation router** | Always-on; maps `project_id → db_path + schema_version + model_version`; union-reads N stores; routes structural queries to per-repo CodeGraph DBs. |
| **Per-project index workers** | Lazy-started on demand, idle-evicted (LRU); own ingest/embed/re-embed for one project. |
| **Sync watcher + git-hooks** | Watchman/fswatch (freshness) + `post-commit/merge/checkout` hooks (guaranteed convergence). |
| **CodeGraph daemons** | Per-repo structural index (`serve --mcp` or one-shot CLI); 300 s idle timeout, self-healing catch-up. |
| **Drift radar** | Revalidates anchors/docs vs current code; flags staleness; triggers owned-doc refresh. |
| **Redactor** | Secret/PII redaction gate before embed + before cloud-bound generation. |
| **(Later) NexusOps daemon / Gateway / event outbox** | The platform that executes Brain proposals + emits the redacted event stream Brain consumes. |

## Permission Matrix
| Actor | Can Do | Cannot Do | Risk |
|---|---|---|---|
| Owner (human) | add/remove projects; set `policy.yaml`/`.brainignore`; approve mutations; choose embedding/privacy posture | — | — |
| Embedded agent | retrieve + answer (grounded); **bounded local-mutation allowlist** (below) with preview+consent | mutate outside the allowlist; embed raw transcripts/secrets; answer without evidence | high (mutation + cloud egress) |
| External agent (MCP) | call retrieval tools (`search`/`get_file`/`graph`/`list_projects`/`status`); receive redacted, policy-filtered results | touch raw code directly; bypass redaction/policy; trigger mutations without the allowlist+consent path | medium |
| Federation router | read-only union over per-project stores (WAL read-only); route structural queries | write any store; cross trust boundary to raw secrets | low |
| Index worker | write its own project store; re-embed; tombstone-replace | write another project's store; mutate user source files | medium |
| Sync watcher / hooks | signal "files changed"; trigger incremental re-index | mutate source; embed unredacted | low |
| Redactor | mask/quarantine secrets pre-embed + pre-cloud | let unredacted content reach embed/cloud/index | **load-bearing** |

## Locked Decisions (this phase)
- **D-USR-1 `[locked — owner 2026-06-15]` Standalone mutation authority = bounded allowlist.** Standalone, the agent may directly perform, **with preview + consent**: (a) write its own `~/.project-brain/` store + `.project-brain/manifest.json`; (b) **owned-doc refresh** (e.g. `layer-docs`) with don't-clobber / 3-way-merge (never overwrite human-edited owned docs, never touch foreign docs); (c) **idempotent, reversible, consented host-config** during `setup` (MCP registration, skills registration). **Everything else** (git, tickets, arbitrary FS/shell) is **propose-only or out-of-scope** standalone. **Integrated, it is strictly propose-only via the NexusOps Action Gateway.**
- **D-USR-2 `[locked — owner 2026-06-15]` Trust posture = single-user local + optional loopback HTTP.** One OS user, one machine. Primary transport = **stdio MCP** (no open port). **Optional opt-in loopback** transport = FastMCP streamable-HTTP on `127.0.0.1` + **per-launch token** (mirrors NexusOps's HTTP fallback) for clients that can't do stdio — notably the **standalone UI running as a separate process / browser**. Secrets (Claude/Voyage API keys) live in the **OS keychain**, never in config/index. Per-project `policy.yaml` + the Redactor are enforced **at the MCP boundary regardless of caller**. No multi-user RBAC (explicit non-goal).

## User Questions Still Open
- Is the **standalone UI** a native app, a local web app (browser → loopback HTTP), or a TUI? (→ Phase 11 decision; the loopback-HTTP choice leans toward a separate-process/browser UI.)
- Default **privacy posture** (local-only vs hybrid: local embed + cloud generation over ZDR) and default **embedding model** (cloud voyage-code-3 vs local bge-m3). (→ Phase 7/11.)
