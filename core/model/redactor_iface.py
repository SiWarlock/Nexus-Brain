"""The Redactor boundary contract — the §18 redaction gate (ARCHITECTURE.md §18, Appendix A).

★ Freeze-before-fork contract (Key safety rule #2). This slice (1.5a) freezes the SIGNATURE +
behavioral invariants of the redactor that runs at all three sinks — it does NOT implement the
catchable-set engine (that is `core/ingest/redactor.py` at Phase 2.3, gated by the
`ci/eval/redaction_fuzz/` fuzz harness). Like the 1.4 provider/CodeGraph ports, this is a behavioral
`@runtime_checkable Protocol` (no Pydantic fields); the only schema surface is the `Sink` alphabet,
pinned by a `spec(§18)` membership snapshot.

D-A5/D-A6 are OWNER-DEFERRED to Phase 2.3: whether `cloud_egress` applies stricter policy than the
other sinks (FLAG-4) and the exact 95/5 threshold are not decided here. The signature is
sink-parameterized so it accommodates BOTH a uniform engine and a cloud-stricter one — it freezes
neither behavior.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable


class Sink(StrEnum):
    """The closed three-sink alphabet — every chunk passes the Redactor at all three (§18).

    A NAMED boundary alphabet (reused by Phase-2 ingest at `persist`, Phase-4.2 at hydration egress,
    Phase-8 at MCP egress), hence a `StrEnum`, not an inline `Literal` (LESSON 6). Membership is a
    frozen contract pinned by `test_sink_values` (`spec(§18)`).
    """

    PERSIST = "persist"
    MCP_EGRESS = "mcp_egress"
    CLOUD_EGRESS = "cloud_egress"


@runtime_checkable
class Redactor(Protocol):
    """The redaction gate (§18, Key safety rule #2) — `redact(payload, sink) -> str`.

    Removes the **catchable set** of secrets (curated prefix-tokened keys, high-entropy `KEY=value`,
    JSON sensitive values, env dumps) before a payload reaches a sink. The keychain-refs-only law is
    the PRIMARY control; the redactor is defense-in-depth (§18).

    Accepted residuals (the ONLY classes exempted by §18 / DECISIONS C-11 — `redact()` is NOT a
    literal-zero guarantee; callers must not treat it as one):
      1. **git-SHA hex** — 40-char SHA-1 / 64-char SHA-256 pass through UNREDACTED (zero-tolerance,
         §18 / D-14: redacting one breaks LanceDB version tagging, `last_resolved_sha` provenance,
         and manifest integrity).
      2. **adversarial <20-char split** — secret fragments split below the 20-char detection floor
         across chunk boundaries (the keychain-refs-only primary control prevents the whole secret
         from arriving).
      3. **sub-20-char JSON** — `"password"`/`"token"`/`"secret"` values under 20 chars (below this
         floor the false-positive rate on common words is unacceptable).

    Envelope (DOCUMENTED here, ENFORCED at Phase 2.3 by the fuzz CI gate — never bake a recall claim
    into this interface or its Fake): on the catchable set the engine must achieve
    `recall >= PROPOSED_RECALL_FLOOR` (>=95%) and `fp_rate <= PROPOSED_FP_CEILING` (<=5%), with the
    git-SHA false-positive rate held at 0%. Those two constants live in
    `ci/eval/redaction_fuzz/harness.py` and are the SINGLE SOURCE OF TRUTH for the gate — this
    module references them by name only and MUST NOT import `ci/` (core does not depend on ci/).

    Behavioral contract (pinned against `FakeRedactor`):
      - **idempotent** — `redact(redact(p, s), s) == redact(p, s)`.
      - **never raises** — on any input string (empty, control/NUL, very long, non-ASCII, env-dump).
      - **pure** — no network, no file I/O (in-memory only; safety rule #6).
      - returns a `str` for a `str` input, for every `Sink`.
    """

    def redact(self, payload: str, sink: Sink) -> str:
        """Return `payload` with the catchable-set secrets removed for delivery to `sink`."""
        ...
