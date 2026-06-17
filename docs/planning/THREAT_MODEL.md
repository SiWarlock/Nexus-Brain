# THREAT_MODEL — Nexus Brain

> `/arch-draft` Phase 14 (security & trust boundaries). Expanded-mode artifact (the privacy surface justified it). Posture: production-grade → these are binding invariants, tested. Aligns with NexusOps's model where integrated.

## Trust boundary & assets
- **Trust boundary:** the local machine, single OS user (D-5). The **MCP server / retrieval core is the only thing that touches raw code**; everything external is on the far side of redaction + policy.
- **Assets to protect:** (1) source code + docs (private), (2) **secrets/credentials** in repos + env + transcripts, (3) Claude/Codex **session transcripts** (most sensitive), (4) API keys (Claude/Voyage), (5) the user's trust (no silent wrong/stale citations).
- **Out of scope (non-goals):** multi-user RBAC, remote/network attackers beyond localhost, a compromised OS, agent egress isolation (the agent's own model-API egress is allowed; we bound *mutations* + keep secrets off agent-reachable surfaces — same residual as NexusOps).

## Adversaries / threats → controls
| # | Threat | Control (binding invariant) |
|---|---|---|
| **T-1** | **Secret/PII reaches the index or a cloud model** (then embedding-inversion reconstructs near-source text) | **Redaction-before-embed** — every chunk passes the Redactor before embedding AND before any cloud-bound generation; raw transcripts never embedded; `thinking` excluded. Secret-shaped property/fuzz test → **zero leaks** (hard gate). High-confidence-unsafe span → quarantine, don't embed. (D-15/PH-2/SR-1) |
| **T-2** | **Cloud embedding provider trains on your code** (Voyage default ToS = opt-IN) | The cloud adapter **MUST enforce + document the provider's training opt-out**; refuse cloud embedding unless opt-out is confirmed; generation over ZDR. Local-first default sidesteps it entirely. (D-23/PH-3/SR-2) |
| **T-3** | **API keys leak** (in config/index/logs) | Secrets **only in the OS keychain** as refs; never in config, the index, events, or traces. Redactor also masks key-shaped strings in any payload. (D-5/PH-2) |
| **T-4** | **Transcript ingested without consent** | Session ingestion is **per-project opt-in, stricter than docs/code**; no consent → skip entirely; episode cards are redacted summaries, not raw text. (PB-5/SR-3) |
| **T-5** | **Agent mutates outside the sanctioned set** | Standalone = **bounded-mutation allowlist** (own store · owned-doc refresh w/ don't-clobber · consented host-config) — everything else propose-only/out-of-scope. Integrated = **strictly propose-only** via the NexusOps Gateway. All mutations previewed + audited. (D-4/SR-4) |
| **T-6** | **Untrusted MCP caller exfiltrates raw code / bypasses policy** | The MCP server **redacts + policy-filters at the boundary regardless of caller**; honors per-project `policy.yaml`; no open port by default (stdio); loopback HTTP gated by a per-launch token. (D-5/T-3) |
| **T-7** | **Telemetry/usage phones home** | OTel instrumentation **off by default, local-only, opt-in**; **no analytics/crash beacons to anyone**; CI egress check. (D-22/SR-5) |
| **T-8** | **Host-config mutation leaves the machine in a broken/irreversible state** | All `setup`/host-config mutations **idempotent + reversible + consented**; `uninstall` reverses every one. (D-4/FR-19/FR-22) |
| **T-9** | **Owned-doc refresh clobbers human edits** | Owned docs → regenerate **with don't-clobber / 3-way-merge** (detect human edits, preserve); foreign docs never overwritten (annotate only); supplemental namespaced. (D-4/F8) |
| **T-10** | **Confident wrong/stale citation** (trust attack, not classic security) | Grounding gate (answer-but-flag) + continuous anchor revalidation + provenance packet; stale anchor never presented as live. (D-6/D-7/PR-1) |
| **T-11** | **Index/store corruption or unclean-quit data loss** | LanceDB atomic-commit on local FS + blue-green generations (prior generation serves on crash) + reproducible-from-source; (this is also why DuckDB-VSS's crash-unsafe HNSW was rejected). (D-14/D-25) |
| **T-12** | **Supply-chain / dep risk** (CodeGraph, models, FastMCP) | Pin versions; verify on install; provision via real channels; permissive-license gate; non-commercial models excluded from defaults. (C-5..C-11) |

## Redaction engine (MVP)
Curated high-recall token-prefix set (`ghp_`,`github_pat_`,`sk-`,`xox`,`AKIA`,PEM,JWT, …) + Shannon-entropy fallback on `KEY=value` / JSON-value lines (allowlist git-SHA/ULID/UUID). Quarantine on high-confidence-unsafe. Mirrors NexusOps's `prefix-entropy-v3` approach so the integrated path inherits a proven engine. **Primary control is keychain-refs-only**; the redactor is defense-in-depth for accidental leaks. Tested by a property/fuzz corpus (living regression fixture) with a recall-floor / FP-ceiling.

## Integrated mode (NexusOps) deltas
When integrated: inputs arrive **already redacted** (secrets as `keychain_ref`); Brain is **propose-only** (INV-SEC-1; safety rule #10); may **never** set/change an ExecutionProfile (#8); consumes the **redacted outbox**. The standalone Redactor is the same engine, so the trust story is continuous across the boundary.
