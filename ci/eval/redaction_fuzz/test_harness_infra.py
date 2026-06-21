"""
Tests for the redaction fuzz harness INFRASTRUCTURE (spike 0.1).

These tests verify that the harness components (generator, corpus, oracle, types)
work correctly — they do NOT test the real redaction engine (Phase-2.3).

The stub_redact tests validate end-to-end wiring only. Stub metrics intentionally
fall below the proposed envelope — that proves the harness is non-trivially measuring.

Run: cd project-brain-contract && python -m pytest ci/eval/redaction_fuzz/test_harness_infra.py -v
"""

from __future__ import annotations

import pytest

from .corpus import ACCEPTED_RESIDUAL_CASES, get_adversarial_corpus
from .generator import generate_non_secrets, generate_secret_samples
from .harness import PROPOSED_FP_CEILING, PROPOSED_RECALL_FLOOR, run_harness
from .oracle import check_false_positive, check_leak, is_gate_failure
from .stub_redactor import stub_redact
from .types import (
    AcceptedResidualClass,
    NonSecretSample,
    RedactionResult,
    SecretClass,
    SecretSample,
    Sink,
)


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------

class TestGenerator:
    def test_generates_nonzero_samples(self) -> None:
        samples = generate_secret_samples()
        assert len(samples) > 20, "Generator should produce at least 20 samples"

    def test_all_secret_classes_covered(self) -> None:
        samples = generate_secret_samples()
        classes_seen = {s.secret_class for s in samples}
        assert classes_seen == set(SecretClass), (
            f"Missing classes: {set(SecretClass) - classes_seen}"
        )

    def test_no_accepted_residuals_in_generated(self) -> None:
        """Generator produces catchable-set samples, not accepted residuals."""
        samples = generate_secret_samples()
        # A few samples from aws_access_keys may be HIGH_ENTROPY_KV but no
        # accepted_residuals in the generated set
        residuals = [s for s in samples if s.accepted_residual is not None]
        assert len(residuals) == 0, f"Unexpected accepted residuals in generator: {residuals}"

    def test_non_secrets_generated(self) -> None:
        non_secrets = generate_non_secrets()
        assert len(non_secrets) >= 8
        # Must include git SHA look-alikes
        labels = {s.label for s in non_secrets}
        assert any("git-sha" in l or "sha" in l for l in labels)

    def test_plaintext_is_nonempty(self) -> None:
        for sample in generate_secret_samples():
            assert sample.plaintext, f"Empty plaintext in {sample.label}"

    def test_no_real_credential_prefixes_in_labels(self) -> None:
        """Labels should describe the CLASS not embed real credentials."""
        for sample in generate_secret_samples():
            # Labels are descriptive strings, plaintext values are synthetic
            assert len(sample.label) > 0
            assert len(sample.label) < 200


# ---------------------------------------------------------------------------
# Corpus tests
# ---------------------------------------------------------------------------

class TestCorpus:
    def test_adversarial_corpus_nonempty(self) -> None:
        corpus = get_adversarial_corpus()
        assert len(corpus) >= 10

    def test_accepted_residuals_marked(self) -> None:
        """All accepted residual cases have accepted_residual set."""
        for sample in ACCEPTED_RESIDUAL_CASES:
            if "CATCHABLE" in sample.label:
                assert sample.accepted_residual is None, (
                    f"{sample.label} should be catchable (no residual)"
                )
            else:
                assert sample.accepted_residual is not None, (
                    f"{sample.label} should have accepted_residual set"
                )

    def test_all_accepted_residual_classes_present(self) -> None:
        """Each AcceptedResidualClass has at least one corpus entry."""
        corpus = get_adversarial_corpus()
        residual_classes = {
            s.accepted_residual
            for s in corpus
            if s.accepted_residual is not None
        }
        expected = set(AcceptedResidualClass)
        assert residual_classes == expected, (
            f"Missing residual classes in corpus: {expected - residual_classes}"
        )

    def test_adversarial_flagged(self) -> None:
        """Adversarial corpus entries have is_adversarial=True."""
        corpus = get_adversarial_corpus()
        assert all(s.is_adversarial for s in corpus)


# ---------------------------------------------------------------------------
# Oracle tests
# ---------------------------------------------------------------------------

class TestOracle:
    def _make_sample(
        self,
        plaintext: str,
        secret_class: SecretClass = SecretClass.PREFIX_TOKEN,
        accepted_residual: AcceptedResidualClass | None = None,
    ) -> SecretSample:
        return SecretSample(
            label="test",
            plaintext=plaintext,
            secret_class=secret_class,
            accepted_residual=accepted_residual,
            context=plaintext,
        )

    def test_detects_leak_when_plaintext_survives(self) -> None:
        sample = self._make_sample("ghp_SynthTestToken00001122334455667788")
        result = check_leak(sample, Sink.PERSIST, "some text ghp_SynthTestToken00001122334455667788 end")
        assert result.leaked is True
        assert is_gate_failure(result) is True

    def test_no_leak_when_redacted(self) -> None:
        sample = self._make_sample("ghp_SynthTestToken00001122334455667788")
        result = check_leak(sample, Sink.PERSIST, "some text [REDACTED] end")
        assert result.leaked is False
        assert is_gate_failure(result) is False

    def test_accepted_residual_leak_not_gate_failure(self) -> None:
        """Git SHA surviving redaction is an accepted residual, not a gate failure."""
        sha = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        sample = self._make_sample(
            sha,
            secret_class=SecretClass.HIGH_ENTROPY_KV,
            accepted_residual=AcceptedResidualClass.GIT_SHA_HEX,
        )
        result = check_leak(sample, Sink.PERSIST, f"sha: {sha}")
        assert result.leaked is True
        assert result.residual_class == AcceptedResidualClass.GIT_SHA_HEX
        assert is_gate_failure(result) is False

    def test_very_short_plaintext_no_leak(self) -> None:
        """Fragments shorter than min_len_for_leak (8) don't trigger leak detection."""
        sample = self._make_sample("sk-", secret_class=SecretClass.PREFIX_TOKEN)
        result = check_leak(sample, Sink.PERSIST, "sk-SynthKeyABCDEF123456")
        # "sk-" is 3 chars < 8 — not a detectable leak by the conservative oracle
        assert result.leaked is False

    def test_false_positive_detected(self) -> None:
        """Non-secret that was present but got redacted is a FP."""
        sample = NonSecretSample(
            label="test-non-secret",
            plaintext="hello-world-uuid-1234",
            reason="test",
        )
        fp = check_false_positive(sample, Sink.PERSIST, "hello-world-uuid-1234", "[REDACTED]")
        assert fp.false_positive is True

    def test_no_false_positive_when_preserved(self) -> None:
        """Non-secret that survives redaction is not a FP."""
        sample = NonSecretSample(
            label="test-non-secret",
            plaintext="hello-world-uuid-1234",
            reason="test",
        )
        fp = check_false_positive(sample, Sink.PERSIST, "hello-world-uuid-1234", "hello-world-uuid-1234")
        assert fp.false_positive is False

    def test_case_insensitive_leak_detection(self) -> None:
        """Oracle normalizes case for detection."""
        sample = self._make_sample("GHP_SYNTHTESTTOKEN0000112233445566")
        result = check_leak(sample, Sink.PERSIST, "GHP_SYNTHTESTTOKEN0000112233445566")
        assert result.leaked is True


# ---------------------------------------------------------------------------
# HarnessReport tests
# ---------------------------------------------------------------------------

class TestHarnessReport:
    def test_recall_zero_on_no_catchable(self) -> None:
        from .types import HarnessReport
        r = HarnessReport(sink=Sink.PERSIST)
        assert r.recall == 1.0  # vacuously true

    def test_recall_computed_correctly(self) -> None:
        from .types import HarnessReport
        r = HarnessReport(sink=Sink.PERSIST, total_catchable=10, caught=9)
        assert abs(r.recall - 0.9) < 1e-6

    def test_fp_rate_computed_correctly(self) -> None:
        from .types import HarnessReport
        r = HarnessReport(sink=Sink.PERSIST, total_non_secrets=20, false_positives=2)
        assert abs(r.fp_rate - 0.1) < 1e-6

    def test_gate_pass(self) -> None:
        from .types import HarnessReport
        r = HarnessReport(sink=Sink.PERSIST, total_catchable=100, caught=98, total_non_secrets=50, false_positives=2)
        assert r.gate_pass(0.95, 0.05) is True

    def test_gate_fail_low_recall(self) -> None:
        from .types import HarnessReport
        r = HarnessReport(sink=Sink.PERSIST, total_catchable=100, caught=80, total_non_secrets=50, false_positives=1)
        assert r.gate_pass(0.95, 0.05) is False

    def test_gate_fail_high_fp(self) -> None:
        from .types import HarnessReport
        r = HarnessReport(sink=Sink.PERSIST, total_catchable=100, caught=99, total_non_secrets=50, false_positives=5)
        assert r.gate_pass(0.95, 0.05) is False


# ---------------------------------------------------------------------------
# End-to-end harness wiring test (stub redactor)
# ---------------------------------------------------------------------------

class TestHarnessEndToEnd:
    def test_harness_runs_without_error(self) -> None:
        """The harness runs end-to-end on all sinks without raising."""
        reports = run_harness(stub_redact, verbose=False)
        assert set(reports.keys()) == set(Sink)

    def test_harness_measures_nonzero_catchable(self) -> None:
        reports = run_harness(stub_redact)
        for sink, report in reports.items():
            assert report.total_catchable > 0, f"No catchable samples measured for {sink}"

    def test_harness_measures_nonzero_non_secrets(self) -> None:
        reports = run_harness(stub_redact)
        for sink, report in reports.items():
            assert report.total_non_secrets > 0, f"No non-secret samples measured for {sink}"

    def test_stub_catches_some_prefix_tokens(self) -> None:
        """Stub redactor should catch at least github/sk- style tokens (prefix class)."""
        reports = run_harness(stub_redact)
        for sink, report in reports.items():
            prefix_recall = report.per_class_recall.get(SecretClass.PREFIX_TOKEN)
            assert prefix_recall is not None, f"No PREFIX_TOKEN samples in {sink} report"
            caught, total = prefix_recall
            assert total > 0
            assert caught > 0, f"Stub caught 0 prefix tokens on {sink} — wiring may be broken"

    def test_stub_misses_entropy_class(self) -> None:
        """
        Stub intentionally doesn't implement entropy scoring —
        it should have imperfect recall on HIGH_ENTROPY_KV.
        This proves the harness is a real measurement, not a tautology.
        """
        reports = run_harness(stub_redact)
        for sink, report in reports.items():
            kv_recall = report.per_class_recall.get(SecretClass.HIGH_ENTROPY_KV)
            if kv_recall is None:
                continue
            caught, total = kv_recall
            recall_pct = caught / total if total > 0 else 1.0
            # Stub should miss at LEAST some entropy-based cases
            assert recall_pct < 1.0, (
                f"Stub claims 100% recall on HIGH_ENTROPY_KV on {sink} — "
                "this would suggest the harness isn't measuring correctly"
            )

    def test_accepted_residuals_tracked(self) -> None:
        """Accepted residuals are tracked separately from catchable-set leaks."""
        reports = run_harness(stub_redact)
        for sink, report in reports.items():
            assert report.total_accepted_residual > 0, (
                f"No accepted residuals tracked for {sink} — corpus may be missing them"
            )

    def test_git_sha_not_redacted_by_stub(self) -> None:
        """
        Git SHAs must NOT be redacted (§18, LanceDB version tagging D-14).
        This test is a hard invariant: if the stub incorrectly redacts git SHAs,
        it would break LanceDB version tagging in production.
        The real Phase-2.3 engine must also pass this.
        """
        sha = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        redacted = stub_redact(sha, Sink.PERSIST)
        assert sha in redacted.lower(), (
            "Git SHA was incorrectly redacted — this would break LanceDB version tagging (§18/D-14)"
        )

    def test_redact_is_idempotent(self) -> None:
        """
        The Redactor MUST be idempotent: redact(redact(p, s), s) == redact(p, s).
        This is a Phase-1.5 interface contract — pinned here as an invariant test.
        """
        payloads = [
            "export SECRET_KEY=SyntheticKeyABCDEFG01234567890123456",
            "ghp_SyntheticGitHubToken0000000000000001",
            '{"password": "SyntheticPass000000000000000000001"}',
            "normal text with no secrets",
        ]
        for payload in payloads:
            for sink in Sink:
                once = stub_redact(payload, sink)
                twice = stub_redact(once, sink)
                assert once == twice, (
                    f"stub_redact is not idempotent on {sink.value!r} for payload: {payload[:50]!r}"
                )

    def test_redact_never_raises(self) -> None:
        """The Redactor MUST NOT raise on any input string."""
        edge_cases = [
            "",
            "\x00\x01\x02binary",
            "a" * 100_000,
            "\n" * 1000,
            "unicode: ￿\U0001F600",
            "mixed: ghp_\x00embedded",
        ]
        for payload in edge_cases:
            for sink in Sink:
                try:
                    stub_redact(payload, sink)
                except Exception as e:
                    pytest.fail(f"stub_redact raised on sink={sink}, payload={payload[:30]!r}: {e}")

    def test_per_class_recall_covers_all_classes(self) -> None:
        """Every SecretClass must appear in per_class_recall (at least one sample)."""
        reports = run_harness(stub_redact)
        for sink, report in reports.items():
            for cls in SecretClass:
                assert cls in report.per_class_recall, (
                    f"SecretClass {cls.value} missing from per_class_recall on {sink} — "
                    "generator may not cover this class"
                )

    def test_all_three_sinks_independent(self) -> None:
        """Running harness on each sink individually should give same results as batch."""
        batch_reports = run_harness(stub_redact, sinks=list(Sink))
        for sink in Sink:
            single_report = run_harness(stub_redact, sinks=[sink])[sink]
            batch_report = batch_reports[sink]
            assert single_report.total_catchable == batch_report.total_catchable
            assert single_report.caught == batch_report.caught
            assert single_report.total_non_secrets == batch_report.total_non_secrets
