# CONSTRAINTS — Nexus Brain

> `/arch-draft` Phase 7. The boundaries the architecture must respect. Posture: production-grade · no timebox (correctness over speed, D-18).

## Platform & runtime
- **C-1** macOS-first (Apple Silicon arm64), **Linux-ready** via the OS-service seam (launchd ∥ systemd `--user`); Windows out of scope (D-16).
- **C-2** Two-process desktop app: **Tauri** (Rust host + WebView, reuses `NexusOps-ui-kit`) + a **bundled Python core sidecar** (PyInstaller). The core MUST be independently runnable headless (CLI/MCP) without the UI (D-17).
- **C-3** **Python** is the core language (LlamaIndex / LanceDB / Ollama / FastMCP ecosystem is Python-first; aligns with the NexusOps Python/FastMCP sidecar). Rust only for the Tauri shell.
- **C-4** Single OS user, single machine; **no open network port** by default (stdio MCP); opt-in loopback HTTP + per-launch token (D-5). No multi-user RBAC.

## External dependencies (versioned, pluggable where noted)
- **C-5** **CodeGraph** (`@colbymchenry/codegraph`) — external structural index; per-repo SQLite; read-only to us; provisioned by `setup`. Multi-repo federation is OUR job (no native cross-repo).
- **C-6** **LanceDB** — pinned (high-level API pre-1.0 Alpha on stable Lance SDK 1.0/format 2.1); the D-25 maintenance contract is mandatory. Apache-2.0.
- **C-7** **Ollama** + the local embed/rerank models — provisioned by `setup`; multi-GB model pulled at setup (not bundled) (D-20).
- **C-8** **FastMCP 3.x** (pinned major; 3.0 has breaking changes — budget migration, D-24).
- **C-9** **Frontier model API** (Claude) for the embedded agent + generation; hybrid posture default.
- **C-10** **Observability backends** (Langfuse, SigNoz, OTel Collector) are **dev/CI/ops infra — NOT shipped** (D-9/D-22).

## License / privacy / legal
- **C-11** Prefer **permissive** licenses for shipped components (Apache-2.0/MIT). Flagged: `jina-*` models often CC-BY-NC (opt-in non-commercial only); `zerank-2` weights CC-BY-NC (use via API). The provider menu marks these (D-23).
- **C-12** **Cloud provider training opt-out MUST be enforced** (Voyage default ToS opts into training) (D-23/PH-3). Cloud generation over ZDR.
- **C-13** **No phone-home / no telemetry exfiltration** — privacy-first local tool (D-22).
- **C-14** Local-first by default; raw code + indexes + transcripts stay local; session ingestion stricter + opt-in (PB-11).

## Integration contract (forward)
- **C-15** The standalone↔NexusOps boundary is the **`HostPort`** + **`MAIN_PLATFORM_INTERFACE.md` v0.2** + the published `nexus-brain-core` API (D-21). NexusOps Phase 8 (Brain seam) is **deferred/unbuilt** → conform to the frozen platform primitives (22 IDs, EventEnvelope, RiskLevel 0–4, ActionPlan shape, propose-only), co-design the rest.
- **C-16** Integrated, Nexus Brain is **propose-only** through the Gateway; consumes the redacted outbox; uses shared IDs; surfaces as the drawer.

## Build posture (steers everything)
- **C-17** **Production-grade** (D-1): error paths, idempotency, observability, secrets handling, deploy/rollback, the maintenance contract = baseline, not deferred. **No timebox** (D-18) — correctness/best-practice gate over speed. Cuts are explicit, flagged `scope simplification`/`deferred`.
