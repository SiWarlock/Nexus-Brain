# Nexus Brain

> **Nexus Brain** (short: **Nexus**) — the portfolio memory engine. *(On the integration seam into NexusOps, the platform-facing name is **Project Brain** / actor `project_brain` — see [docs/integrations/MAIN_PLATFORM_INTERFACE.md](./docs/integrations/MAIN_PLATFORM_INTERFACE.md). The repo directory stays `project-brain/`.)*

A local-first, multi-project **memory, retrieval, reasoning, and action-planning engine** for software projects. It fuses a curated docs pipeline with a live, federated code graph and serves both to a frontier model — so you can ask one question across your entire portfolio and get an answer where every claim carries a clickable `file:line`, dated and honest about staleness. The `file:line` **anchor** is the trust primitive.

Nexus Brain ships **standalone first** — a native desktop app (Tauri) + the `nexus`/`nb` CLI, usable on any repo — and is designed to later integrate into **NexusOps** (a desktop-first, local-runtime AI engineering control plane) as its propose-only memory/reasoning sidecar. It only ever *proposes* actions; the platform executes them through its Action Gateway.

**Status:** planning complete — binding **[ARCHITECTURE.md](./ARCHITECTURE.md)** + spec-anchored **[IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)** finalized. Product spec: **[docs/product/PRD.md](./docs/product/PRD.md)** · research: **[docs/research/RESEARCH_DOSSIER.md](./docs/research/RESEARCH_DOSSIER.md)** · planning artifacts: `docs/planning/`.
