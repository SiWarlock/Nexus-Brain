"""Unit tests for the catchable-set redaction engine (ARCHITECTURE.md §18, Key safety rule #2).

The engine (`core/ingest/redactor.py`) implements the frozen `core.model.redactor_iface.Redactor`
Protocol: it redacts the four catchable secret classes (prefix-token incl. JWT/PEM, high-entropy KV,
JSON-sensitive-value, env-dump) at all three sinks, and PASSES THROUGH the three §18 accepted
residuals — git-SHA hex (ZERO-TOLERANCE: redacting one is the cardinal failure), the adversarial
<20-char split, and sub-20-char JSON values. Behavioral invariants (frozen-iface): idempotent,
never-raises, pure, str-for-every-Sink. The final test runs the real `ci/eval/redaction_fuzz/` gate
against the engine (recall ≥ floor, FP ≤ ceiling, git-SHA FP == 0%).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ingest.redactor import CatchableSetRedactor
from model.redactor_iface import Redactor as RedactorProtocol
from model.redactor_iface import Sink

pytestmark = pytest.mark.unit

# A 40-char SHA-1 and a 64-char SHA-256 (lower + UPPER) — the cardinal §18 zero-tolerance residual.
SHA1 = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
SHA256 = "deadbeefcafe0000000000000000000000000000000000000000000000001234"


def _engine() -> CatchableSetRedactor:
    return CatchableSetRedactor()


def test_redactor_conforms_to_protocol() -> None:
    # spec(§18): the engine satisfies the frozen 1.5 Redactor Protocol (runtime_checkable).
    assert isinstance(_engine(), RedactorProtocol)


def test_redacts_prefix_tokens() -> None:
    # spec(§18): PREFIX_TOKEN class — each well-known prefix-tokened secret is removed.
    eng = _engine()
    secrets = [
        "ghp_" + "A" * 36,
        "github_pat_" + "B" * 82,
        "sk-" + "C" * 48,
        "xoxb-111111111-222222222222-" + "D" * 24,
        "AKIA" + "EFGHIJKLMNOPQR12",  # AKIA + 16
    ]
    for secret in secrets:
        out = eng.redact(f"key = {secret}", Sink.PERSIST)
        assert secret not in out, secret


def test_redacts_pem_block() -> None:
    # spec(§18): PREFIX_TOKEN/PEM — a PEM private-key block is removed wholesale.
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIBODADADADADAD\n-----END RSA PRIVATE KEY-----"
    out = _engine().redact(f"# deploy key\n{pem}\n", Sink.PERSIST)
    assert "MIIBODADADADADAD" not in out
    assert "BEGIN RSA PRIVATE KEY" not in out


def test_redacts_jwt() -> None:
    # spec(§18): PREFIX_TOKEN/JWT — a three-segment base64url token is removed.
    jwt = "eyJhbGciOiJIUzI1NiableHEADER0.payLOADpayLOADpayLOADpayLOAD12345.sigSIGsigSIGsigSIG99"
    out = _engine().redact(f"Authorization: Bearer {jwt}", Sink.MCP_EGRESS)
    assert jwt not in out


def test_redacts_high_entropy_kv() -> None:
    # spec(§18): HIGH_ENTROPY_KV — a high-entropy value in KEY=value context is redacted.
    value = "Xq7Z9pL2mK4nB6vC8wD0fG1hJ3sR5tA7yU"  # 34-char high-entropy
    for ctx in (f"API_KEY={value}", f'export API_KEY="{value}"', f"api-key: {value}"):
        out = _engine().redact(ctx, Sink.PERSIST)
        assert value not in out, ctx


def test_redacts_json_sensitive_value() -> None:
    # spec(§18): JSON_SENSITIVE_VALUE — a sensitive-keyed value (>=20) is redacted; key preserved.
    value = "SynthPass20CharExact"  # exactly 20 — at the floor, catchable
    out = _engine().redact(f'{{"password": "{value}"}}', Sink.PERSIST)
    assert value not in out
    assert "password" in out  # the key is preserved, only the value goes


def test_redacts_env_dump() -> None:
    # spec(§18): ENV_DUMP — a multi-line env dump's secret value is redacted (benign vars kept).
    secret = "SyntheticEnvSecretKeyForFuzzTesting0001"
    dump = f"PATH=/usr/bin\nSECRET_KEY={secret}\nTERM=xterm-256color\n"
    out = _engine().redact(dump, Sink.PERSIST)
    assert secret not in out
    assert "PATH=/usr/bin" in out  # benign low-entropy var untouched


def test_redacts_url_credential() -> None:
    # spec(§18): URL-credential pass — the password in ://user:PASS@ is redacted, but a
    # credential-LESS URL (ubiquitous in docs/code) is returned UNTOUCHED (FP guard).
    eng = _engine()
    secret = "SyntheticDBPass99999Extra"  # >= 20
    out = eng.redact(f"DATABASE_URL=postgres://admin:{secret}@db.host:5432/app", Sink.PERSIST)
    assert secret not in out
    assert "db.host" in out  # only the password goes — URL structure is preserved
    clean_url = "https://github.com/SiWarlock/Nexus-Brain.git"
    assert eng.redact(clean_url, Sink.PERSIST) == clean_url  # no credential → untouched


def test_redacts_comma_embedded_sensitive_value() -> None:
    # spec(§18): a sensitive value with an embedded structural delimiter is redacted WHOLE — the
    # high-entropy tail after the `,` must not leak (the value charset must not split-and-drop it).
    secret = "Xq7Z9pL2mK,4nB6vC8wD0fG1hJ3sR5tA7yU"  # 35 chars incl. an embedded comma
    out = _engine().redact(f"API_KEY={secret}", Sink.PERSIST)
    assert "4nB6vC8wD0fG1hJ3sR5tA7yU" not in out  # the post-comma tail must be gone


def test_keeps_public_url_under_sensitive_key() -> None:
    # spec(§18): FP guard — a public endpoint under a sensitive-NAMED key (token_url/auth_endpoint)
    # is NOT a secret; a URL value passes through (embedded creds are the URL-credential pass job).
    eng = _engine()
    for line in (
        "token_url: https://oauth2.googleapis.com/token",
        "auth_endpoint=https://login.example.com/authorize",
    ):
        assert eng.redact(line, Sink.PERSIST) == line


def test_marker_prefix_cannot_suppress_redaction() -> None:
    # spec(§18): idempotence is EXACT-match on the marker set, not a startswith prefix — ingested
    # content beginning with the literal "[REDACTED" must not suppress an adjacent real secret.
    out = _engine().redact("API_KEY=[REDACTED]realLeakSecretValue000001", Sink.PERSIST)
    assert "realLeakSecretValue000001" not in out


def test_fail_closed_on_internal_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # spec(§18): SECURITY property — on an internal error the engine fails CLOSED (never returns the
    # original secret-bearing payload). Force a sub-pass to raise on a secret input; assert no leak.
    eng = _engine()
    secret = "ghp_" + "Z" * 36

    def _boom(_payload: str) -> str:
        raise RuntimeError("synthetic sub-pass failure")

    monkeypatch.setattr(eng, "_pass_pem", _boom)
    out = eng.redact(f"token = {secret}", Sink.PERSIST)
    assert secret not in out  # fail-closed: the secret must NOT survive an internal error


def test_pure_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    # spec(§18) / safety rule #6: the engine performs no network/file I/O. The spies record the call
    # BEFORE raising, so `calls` catches the attempt even through the fail-closed except.
    import builtins
    import socket

    calls: list[str] = []

    def _spy_open(*a: object, **k: object) -> object:
        calls.append("open")
        raise AssertionError("file I/O attempted")

    def _spy_socket(*a: object, **k: object) -> object:
        calls.append("socket")
        raise AssertionError("socket I/O attempted")

    monkeypatch.setattr(builtins, "open", _spy_open)
    monkeypatch.setattr(socket, "socket", _spy_socket)
    eng = _engine()
    eng.redact("API_KEY=" + "q" * 40 + "\nPATH=/usr/bin\n" + f"sha={SHA1}", Sink.PERSIST)
    assert calls == []  # no file/socket I/O


def test_git_sha_passthrough_zero_tolerance() -> None:
    # spec(§18): the cardinal residual — 40/64-char git-SHA hex (lower + UPPER) survives VERBATIM
    # at every sink, bare AND in a KEY=value context (allowlist runs BEFORE the entropy detector).
    eng = _engine()
    for sha in (SHA1, SHA1.upper(), SHA256, SHA256.upper()):
        for sink in Sink:
            assert eng.redact(sha, sink) == sha, (sha, sink)
            assert sha in eng.redact(f"last_resolved_sha={sha}", sink), (sha, sink)


def test_adversarial_short_split_passes() -> None:
    # spec(§18): accepted residual — a sub-20-char fragment is not redacted (below the floor).
    out = _engine().redact("token_part1 = 'ghp_SYNTH'", Sink.PERSIST)
    assert "ghp_SYNTH" in out


def test_sub_20_char_json_passes() -> None:
    # spec(§18): accepted residual — a sub-20-char JSON sensitive value is not redacted (FP floor).
    for word in ("changeme", "admin", "letmein"):
        out = _engine().redact(f'{{"password": "{word}"}}', Sink.PERSIST)
        assert word in out, word


def test_idempotent() -> None:
    # frozen-iface: redact(redact(p,s),s) == redact(p,s) — the marker never re-triggers a detector.
    eng = _engine()
    payloads = [
        "ghp_" + "A" * 36,
        f"API_KEY={'Xq7Z9pL2mK4nB6vC8wD0fG1hJ3sR5tA7yU'}",
        '{"token": "SynthPass20CharExactValue99"}',
        "PATH=/usr/bin\nSECRET_KEY=" + "Z" * 40 + "\n",
    ]
    for p in payloads:
        for sink in Sink:
            once = eng.redact(p, sink)
            assert eng.redact(once, sink) == once, p


def test_never_raises() -> None:
    # frozen-iface: never raises on any input string; always returns a str.
    eng = _engine()
    inputs = ["", "\x00\x01\x02", "a" * 100_000, "héllo wörld 🔑", "K=" + "x" * 50, "\n\n\t  "]
    for s in inputs:
        for sink in Sink:
            assert isinstance(eng.redact(s, sink), str)


def test_all_three_sinks_return_str() -> None:
    # frozen-iface: every Sink value returns a str (sink-total).
    eng = _engine()
    for sink in Sink:
        assert isinstance(eng.redact("API_KEY=" + "q" * 40, sink), str)


def test_marker_contains_no_secret() -> None:
    # spec(§18): redaction actually removes the secret — the output retains none of the secret body.
    secret = "Xq7Z9pL2mK4nB6vC8wD0fG1hJ3sR5tA7yU"
    out = _engine().redact(f"API_KEY={secret}", Sink.PERSIST)
    assert secret not in out
    assert "REDACTED" in out  # a fixed secret-free marker replaced it


def test_fuzz_gate_passes_all_sinks() -> None:
    # spec(§18): the acceptance gate — the real ci/ fuzz harness run against THIS engine passes the
    # proposed envelope for every sink AND holds the git-SHA false-positive subclass at exactly 0%.
    # The engine module stays ci/-free; only this test reaches across the root (core ⊥ ci/).
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from ci.eval.redaction_fuzz.harness import (  # noqa: E402
        PROPOSED_FP_CEILING,
        PROPOSED_RECALL_FLOOR,
        run_harness,
    )

    # The harness calls with ITS OWN Sink enum (str-valued, distinct class). Adapt explicitly to
    # core's Sink so the boundary stays type-honest even if a future engine branches on the sink.
    eng = _engine()

    def _adapter(payload: str, sink: object) -> str:
        return eng.redact(payload, Sink(getattr(sink, "value")))  # noqa: B009 (ci Sink → core Sink)

    reports = run_harness(_adapter)
    assert reports, "harness returned no reports"
    for sink, report in reports.items():
        assert report.gate_pass(PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING), (
            f"{sink}: recall={report.recall:.3f} fp={report.fp_rate:.3f}"
        )
        git_sha_fps = [fp for fp in report.fp_samples if fp.sample.label.startswith("git-sha")]
        assert not git_sha_fps, f"{sink}: git-SHA false positives (zero-tolerance): {git_sha_fps}"
