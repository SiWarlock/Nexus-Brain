"""
Redaction fuzz harness for Nexus Brain.

Spike 0.1 — property generator + adversarial corpus + leak oracle + measurement harness.
Parametrized on a `redact(payload, sink)` callable; the real engine lands in Phase-2.3.
Anchored to ARCHITECTURE.md §18 + DECISIONS.md D-26/C-11 + THREAT_MODEL.md §Redaction engine.

SAFETY: All secrets in this module are SYNTHETIC. No real credentials are generated or stored.
NETWORK: Zero network egress. All sinks are simulated in-memory.
"""
