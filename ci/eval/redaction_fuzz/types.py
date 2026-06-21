"""
Shared types for the redaction fuzz harness.

Anchored to ARCHITECTURE.md §18: "redact(payload, sink∈{persist, mcp_egress, cloud_egress})".
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class Sink(str, enum.Enum):
    """The three sinks at which the Redactor MUST run (§18)."""

    PERSIST = "persist"
    """Chunk text/vector written to LanceDB (index-time sink)."""

    MCP_EGRESS = "mcp_egress"
    """Payload leaving the MCP boundary to an external caller."""

    CLOUD_EGRESS = "cloud_egress"
    """Payload sent to a cloud embedding/model provider."""


class SecretClass(str, enum.Enum):
    """
    The catchable-set classes enumerated in THREAT_MODEL.md §Redaction engine
    and anchored in ARCHITECTURE.md §18 / DECISIONS.md D-15/D-26.

    These are the classes the Redactor MUST recall — the "catchable set".
    """

    PREFIX_TOKEN = "prefix_token"
    """Well-known prefix-tokened secrets: ghp_, github_pat_, sk-, xox*, AKIA, PEM, JWT."""

    HIGH_ENTROPY_KV = "high_entropy_kv"
    """High-entropy value in a KEY=value or shell-export context."""

    JSON_SENSITIVE_VALUE = "json_sensitive_value"
    """JSON field whose key is password / token / secret / api_key / access_key."""

    ENV_DUMP = "env_dump"
    """Multi-line env dump containing multiple KEY=VALUE pairs."""


class AcceptedResidualClass(str, enum.Enum):
    """
    ENUMERATED accepted residuals from ARCHITECTURE.md §18 / DECISIONS.md D-26/C-11.
    These are NOT leaks — they are documented, §18-anchored exceptions.

    CRITICAL: Do NOT add new values here without orchestrator escalation + owner gate.
    """

    GIT_SHA_HEX = "git_sha_hex"
    """Git SHA-1 / SHA-256 hex strings (40/64-char lowercase hex).
    These pass the entropy filter but are non-sensitive version identifiers.
    §18 explicitly lists them as accepted; LanceDB git-SHA version tagging (D-14) requires them."""

    ADVERSARIAL_SHORT_SPLIT = "adversarial_short_split"
    """Secrets split into sub-20-character fragments across chunk boundaries.
    The literal-zero promise was undeliverable for split-secret adversarials (C-11).
    The primary control (keychain-refs-only) prevents secrets from reaching the redactor
    in the first place; the redactor is defense-in-depth."""

    SUB_20_CHAR_JSON = "sub_20_char_json"
    """JSON "password"/"token"/"secret" values that are shorter than 20 characters.
    Below the minimum-length entropy floor, false-positive rate becomes unacceptable
    (common words like 'changeme', 'test', 'admin' match JSON-sensitive keys).
    C-11: literal-zero undeliverable at short lengths."""


@dataclass(frozen=True)
class SecretSample:
    """
    A synthetic secret-shaped input used in the fuzz harness.

    SAFETY: All values are SYNTHETIC — constructed to match the *shape*
    of a real secret class without being real credentials.
    """

    label: str
    """Human-readable description for reporting."""

    plaintext: str
    """The synthetic secret string (the value to detect, NOT a real credential)."""

    secret_class: SecretClass
    """Which catchable-set class this sample exercises."""

    accepted_residual: AcceptedResidualClass | None = None
    """If set, this sample IS expected to survive redaction (it's an accepted residual)."""

    is_adversarial: bool = False
    """True for curated adversarial cases (split, base64, comment-embedded, etc.)."""

    context: str = ""
    """Full payload context string that WRAPS the plaintext (e.g. a code file excerpt)."""


@dataclass(frozen=True)
class NonSecretSample:
    """A non-secret look-alike used for false-positive measurement."""

    label: str
    plaintext: str
    reason: str
    """Why this looks secret-shaped but isn't (for FP analysis)."""


@dataclass
class RedactionResult:
    """Result of running redact() on a single sample."""

    sample: SecretSample
    sink: Sink
    redacted_payload: str
    """The payload after redact() returns."""

    leaked: bool
    """True if the plaintext secret survives in the redacted payload (as judged by the oracle)."""

    residual_class: AcceptedResidualClass | None = None
    """Set if leaked=True AND the leak is in the accepted-residual set."""


@dataclass
class FPResult:
    """Result of running redact() on a non-secret sample (false-positive measurement)."""

    sample: NonSecretSample
    sink: Sink
    redacted_payload: str
    false_positive: bool
    """True if the non-secret was incorrectly redacted."""


@dataclass
class HarnessReport:
    """Aggregate metrics from one harness run."""

    sink: Sink

    # Catchable-set recall
    total_catchable: int = 0
    """Samples in the catchable set (accepted_residual=None)."""

    caught: int = 0
    """Samples in the catchable set that were successfully redacted."""

    # Accepted residuals
    total_accepted_residual: int = 0
    escaped_accepted: int = 0
    """Residuals that escaped — expected; NOT a failure."""

    # False positives
    total_non_secrets: int = 0
    false_positives: int = 0

    # Per-class breakdown
    per_class_recall: dict[SecretClass, tuple[int, int]] = field(default_factory=dict)
    """class → (caught, total) in the catchable set."""

    leaked_samples: list[RedactionResult] = field(default_factory=list)
    """All catchable-set leaks (failures)."""

    fp_samples: list[FPResult] = field(default_factory=list)
    """All false-positive misclassifications."""

    @property
    def recall(self) -> float:
        """Recall over the catchable set (0.0–1.0). This is the gate metric."""
        if self.total_catchable == 0:
            return 1.0
        return self.caught / self.total_catchable

    @property
    def fp_rate(self) -> float:
        """False-positive rate over non-secret look-alikes (0.0–1.0)."""
        if self.total_non_secrets == 0:
            return 0.0
        return self.false_positives / self.total_non_secrets

    def gate_pass(self, recall_floor: float, fp_ceiling: float) -> bool:
        """True if the harness report passes the proposed envelope."""
        return self.recall >= recall_floor and self.fp_rate <= fp_ceiling


@runtime_checkable
class RedactorProtocol(Protocol):
    """
    The interface the Phase-1.5 Redactor freeze MUST satisfy.

    redact(payload, sink) → redacted_payload

    Contracts:
    - MUST redact all catchable-set secrets before they reach the sink.
    - MUST accept all three Sink values.
    - MUST NOT raise on any input string (handle malformed input gracefully).
    - MUST be pure/side-effect-free (no network, no file I/O).
    - MUST be idempotent (redact(redact(p, s), s) == redact(p, s)).
    """

    def __call__(self, payload: str, sink: Sink) -> str: ...
