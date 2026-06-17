"""
Leak oracle — determines whether a secret survived redaction.

Definition of a LEAK:
    A secret leaks if its plaintext (or a recognizable form of it) survives into
    the redacted payload delivered to a sink (persist / MCP-egress / cloud-egress).

The oracle is CONSERVATIVE: it checks for the literal plaintext string.
It does NOT currently track encoding-aware forms (e.g. base64 of a base64 secret)
— that would require encoding-aware oracle layers, which is a Phase-2.3 refinement.
Flag in findings if this matters.

NETWORK: Zero network egress. All sink checks are against in-memory strings.
"""

from __future__ import annotations

from .types import (
    AcceptedResidualClass,
    FPResult,
    NonSecretSample,
    RedactionResult,
    SecretSample,
    Sink,
)


def _normalize(s: str) -> str:
    """Normalize a string for leak detection (lowercase, strip whitespace)."""
    return s.lower().strip()


def check_leak(
    sample: SecretSample,
    sink: Sink,
    redacted_payload: str,
) -> RedactionResult:
    """
    Oracle: determine whether sample.plaintext leaked into redacted_payload.

    A token leaks if the normalized plaintext appears literally in the normalized
    redacted output. This is the simplest conservative oracle.

    For accepted-residual samples, a "leak" is expected and classified accordingly.
    The CI gate only fails on leaks that are NOT in the accepted-residual set.
    """
    normalized_payload = _normalize(redacted_payload)
    normalized_secret = _normalize(sample.plaintext)

    # Minimum detection length: don't cry "leak" for 3-char prefixes alone
    # (the split-secret accepted residual covers those)
    min_len_for_leak = 8

    leaked = (
        len(normalized_secret) >= min_len_for_leak
        and normalized_secret in normalized_payload
    )

    residual_class: AcceptedResidualClass | None = None
    if leaked and sample.accepted_residual is not None:
        residual_class = sample.accepted_residual

    return RedactionResult(
        sample=sample,
        sink=sink,
        redacted_payload=redacted_payload,
        leaked=leaked,
        residual_class=residual_class,
    )


def check_false_positive(
    sample: NonSecretSample,
    sink: Sink,
    original_payload: str,
    redacted_payload: str,
) -> FPResult:
    """
    Oracle: determine whether a non-secret was incorrectly redacted.

    A false positive occurs when the non-secret plaintext was present in the
    original payload but is absent from the redacted payload (i.e. it was
    incorrectly treated as a secret).
    """
    normalized_original = _normalize(original_payload)
    normalized_redacted = _normalize(redacted_payload)
    normalized_value = _normalize(sample.plaintext)

    was_present = normalized_value in normalized_original
    still_present = normalized_value in normalized_redacted

    false_positive = was_present and not still_present

    return FPResult(
        sample=sample,
        sink=sink,
        redacted_payload=redacted_payload,
        false_positive=false_positive,
    )


def is_gate_failure(result: RedactionResult) -> bool:
    """
    True if this result represents a CI gate failure.

    Gate failures are leaks that are NOT in the accepted-residual set.
    Accepted residuals (git SHAs, adversarial splits, sub-20-char JSON)
    are EXPECTED to pass through — they are NOT gate failures.
    """
    return result.leaked and result.residual_class is None
