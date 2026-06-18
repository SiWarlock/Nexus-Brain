"""Unit tests for the Redactor boundary contract (ARCHITECTURE.md §18, Key safety rule #2).

★ Freeze-before-fork behavioral interface — the §18 redaction gate that runs at all three sinks
(persist · mcp_egress · cloud_egress). This slice (1.5a) freezes the `Sink` alphabet + the
`@runtime_checkable Redactor` Protocol + a contract-faithful `FakeRedactor` double; the
catchable-set recall/FP ENGINE + its CI fuzz gate land at Phase 2.3 (spike 0.1 §7.1). The envelope
(recall ≥95% / FP ≤5% / git-SHA FP 0%) is documented on the interface but enforced only at 2.3.

D-A5/D-A6 (per-sink strictness + the 95/5 threshold) are owner-deferred — the sink-parameterized
signature accommodates both uniform and cloud-stricter behavior; NO per-sink behavior is frozen
here.
"""

from __future__ import annotations

import pytest

from model.redactor_iface import Redactor, Sink
from testing.fakes import FakeRedactor

pytestmark = pytest.mark.unit

# A 40-char SHA-1 and a 64-char SHA-256 — non-sensitive version identifiers that MUST survive
# redaction (§18 / D-14 zero-tolerance: redacting these breaks LanceDB version tagging,
# `last_resolved_sha` provenance, and manifest integrity).
_SHA1 = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# Adversarial payloads for the never-raises contract — a redactor that throws is a DoS at the
# ingest/egress boundary (spike §7.1.4).
_ADVERSARIAL_PAYLOADS = (
    "",  # empty
    "\x00\x01\x02\x1f",  # NUL + control chars
    "x" * 100_000,  # very long
    "héllo wörld 日本語 🔑 café",  # non-ASCII / multibyte
    "PATH=/usr/bin\nAWS_SECRET_ACCESS_KEY=wJalrXUtnFEXAMPLEKEY\nHOME=/root\n",  # env dump
)


def test_redactor_protocol_conformance() -> None:
    # LESSON 1: the Fake structurally satisfies the runtime_checkable port.
    assert isinstance(FakeRedactor(), Redactor)


def test_sink_values() -> None:
    # spec(§18): the §2.5-seam schema-snapshot for this contract — the closed three-sink alphabet
    # ("the redactor runs at all three sinks", LESSON 6). Drift here is a cross-track Finding.
    assert {s.value for s in Sink} == {"persist", "mcp_egress", "cloud_egress"}


def test_redact_accepts_all_sinks() -> None:
    # spec(§18): redact(payload, sink) returns a str for every sink member ("runs at all three").
    r = FakeRedactor()
    for sink in Sink:
        assert isinstance(r.redact("some payload", sink), str)


def test_redact_is_idempotent() -> None:
    # spike §7.1.4: redact(redact(p, s), s) == redact(p, s) for every sink + payload (a second pass
    # over already-redacted output is a no-op — the redaction marker is not itself re-redacted).
    r = FakeRedactor()
    payloads = (
        "plain text, nothing to redact",
        "leaked token=ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        f"release {_SHA1} shipped",
        "",
    )
    for sink in Sink:
        for p in payloads:
            once = r.redact(p, sink)
            assert r.redact(once, sink) == once


def test_redact_never_raises() -> None:
    # spike §7.1.4: never raises on ANY input string (empty / NUL+control / very long / non-ASCII /
    # multi-line env-dump-shaped); always returns a str.
    r = FakeRedactor()
    for sink in Sink:
        for p in _ADVERSARIAL_PAYLOADS:
            assert isinstance(r.redact(p, sink), str)


@pytest.mark.parametrize("sha", [_SHA1, _SHA256, _SHA1.upper(), _SHA256.upper()])
def test_git_sha_passthrough(sha: str) -> None:
    # spec(§18) / D-14 zero-tolerance sub-invariant: a 40-char AND 64-char hex SHA survive
    # (case-insensitive) on ALL three sinks. Architecture-level, not just a quality metric.
    r = FakeRedactor()
    for sink in Sink:
        out = r.redact(f"checkout {sha} then build", sink)
        # exact, case-preserving containment — proves the SHA survived byte-for-byte (not merely
        # that some hex run appears), the precise §18/D-14 "git SHA is never redacted" invariant.
        assert sha in out


def test_fake_redactor_is_observably_applied() -> None:
    # LESSON 1: a contract-faithful double, not a silent identity — it observably strips an obvious
    # prefix-tokened credential so downstream "was the redactor applied?" tests have a signal. This
    # makes NO catchable-set recall claim (that is the Phase-2.3 engine + its fuzz gate).
    r = FakeRedactor()
    token = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
    out = r.redact(f"export GH_TOKEN={token}", Sink.PERSIST)
    assert token not in out
