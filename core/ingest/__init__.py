"""The §8 ingest pipeline (spine track, Phase 2).

Stage order (ARCHITECTURE.md §8): discover → classify → chunk → context-augment → redact → embed →
LanceDB write. This package lands the deterministic, pure front of that pipeline first; the `add`
orchestration (Task 2.4) wires the stages behind the CLI, and the HostPort mutation chokepoint
(Task 2.S) lands with the first writer.
"""
