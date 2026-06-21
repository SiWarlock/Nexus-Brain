"""
Measurement harness — runs a redact() callable over the full corpus and reports recall + FP rate.

Usage (as a script):
    cd project-brain-contract
    python -m ci.eval.redaction_fuzz.harness [--verbose] [--sink SINK]

Or import and call run_harness() programmatically (e.g. from pytest).

The harness is PARAMETRIZED on a redact(payload, sink) callable — swap in the
real Phase-2.3 engine without changing the harness itself.

NETWORK: Zero network egress.
SAFETY: Synthetic secrets only.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from typing import Callable

from .corpus import CORPUS_NON_SECRETS, get_adversarial_corpus
from .generator import generate_non_secrets, generate_secret_samples
from .oracle import check_false_positive, check_leak, is_gate_failure
from .types import (
    FPResult,
    HarnessReport,
    RedactionResult,
    SecretClass,
    SecretSample,
    Sink,
)

# ---------------------------------------------------------------------------
# Proposed envelope (the deliverable of spike 0.1)
# Anchored to §18 + THREAT_MODEL.md + D-26/C-11.
# Rationale in docs/audits/redaction-envelope.md.
# ---------------------------------------------------------------------------

PROPOSED_RECALL_FLOOR: float = 0.95
"""
Proposed minimum recall over the catchable set (non-residual samples).

Rationale:
  - THREAT_MODEL.md T-1 requires "zero leaks" (hard gate) — anchored to the CATCHABLE set only.
  - §18/D-26/C-11 enumerates the accepted residuals (git SHA, split <20-char, sub-20 JSON);
    the "zero-leak" gate applies ONLY to catchable-set samples.
  - The real `prefix-entropy-v3` approach (THREAT_MODEL.md) achieves near-perfect recall
    on prefix and JSON classes; entropy fallback covers KV. 0.95 is conservative — the
    real engine should target 0.98+ on a calibrated run.
  - 0.95 floor leaves room for genuinely novel adversarial forms not yet in the corpus.
  - Flag for orchestrator if data from the real Phase-2.3 engine suggests raising to 0.98.
"""

PROPOSED_FP_CEILING: float = 0.05
"""
Proposed maximum false-positive rate over non-secret look-alikes.

Rationale:
  - Git SHAs, UUIDs, short JSON values are explicitly excluded from the catchable set.
  - False positives degrade ingest quality (redacted content becomes unsearchable).
  - 0.05 (5%) ceiling allows some noise from high-entropy code literals.
  - The real engine MUST NOT redact git SHAs (LanceDB version tagging, D-14).
  - Flag for orchestrator if FP rate on git SHAs > 0% (zero tolerance for that subclass).
"""


def run_harness(
    redact_fn: Callable[[str, Sink], str],
    sinks: list[Sink] | None = None,
    verbose: bool = False,
) -> dict[Sink, HarnessReport]:
    """
    Run the measurement harness for all specified sinks.

    Args:
        redact_fn: The redact(payload, sink) callable to evaluate.
        sinks: Which sinks to test. Defaults to all three.
        verbose: Print per-sample results to stdout.

    Returns:
        dict[Sink, HarnessReport] — one report per sink.
    """
    if sinks is None:
        sinks = list(Sink)

    # Build the full corpus
    generated_secrets = generate_secret_samples()
    adversarial_secrets = get_adversarial_corpus()
    all_secrets = generated_secrets + adversarial_secrets

    generated_non_secrets = generate_non_secrets()
    corpus_non_secrets = CORPUS_NON_SECRETS
    all_non_secrets = generated_non_secrets + corpus_non_secrets

    reports: dict[Sink, HarnessReport] = {}

    for sink in sinks:
        report = HarnessReport(sink=sink)
        per_class: dict[SecretClass, list[tuple[bool, SecretSample]]] = defaultdict(list)

        # --- Secret samples ---
        for sample in all_secrets:
            payload = sample.context if sample.context else sample.plaintext
            redacted = redact_fn(payload, sink)
            result = check_leak(sample, sink, redacted)

            if sample.accepted_residual is not None:
                # Accepted residual — not part of the catchable-set gate
                report.total_accepted_residual += 1
                if result.leaked:
                    report.escaped_accepted += 1
                # Don't count toward recall
            else:
                # Catchable-set sample
                report.total_catchable += 1
                was_caught = not result.leaked
                per_class[sample.secret_class].append((was_caught, sample))
                if was_caught:
                    report.caught += 1
                else:
                    report.leaked_samples.append(result)
                    if verbose:
                        print(f"  LEAK [{sink.value}] {sample.label!r}: {sample.plaintext[:40]!r}")

        # Aggregate per-class
        for cls, results in per_class.items():
            caught_count = sum(1 for caught, _ in results if caught)
            total_count = len(results)
            report.per_class_recall[cls] = (caught_count, total_count)

        # --- Non-secret samples (FP measurement) ---
        for ns_sample in all_non_secrets:
            payload = ns_sample.plaintext  # FP samples are measured on the raw plaintext
            redacted = redact_fn(payload, sink)
            fp_result = check_false_positive(ns_sample, sink, payload, redacted)
            report.total_non_secrets += 1
            if fp_result.false_positive:
                report.false_positives += 1
                report.fp_samples.append(fp_result)
                if verbose:
                    print(f"  FP   [{sink.value}] {ns_sample.label!r}: {ns_sample.plaintext[:40]!r} — {ns_sample.reason}")

        reports[sink] = report

    return reports


def print_report(report: HarnessReport, recall_floor: float, fp_ceiling: float) -> None:
    """Print a human-readable report to stdout."""
    pass_fail = "PASS" if report.gate_pass(recall_floor, fp_ceiling) else "FAIL"
    print(f"\n=== Sink: {report.sink.value} — {pass_fail} ===")
    print(f"  Catchable-set recall:  {report.recall:.1%}  ({report.caught}/{report.total_catchable})")
    print(f"  False-positive rate:   {report.fp_rate:.1%}  ({report.false_positives}/{report.total_non_secrets})")
    print(f"  Accepted residuals:    {report.escaped_accepted}/{report.total_accepted_residual} escaped (expected)")
    print(f"  Gate (floor={recall_floor:.0%}, FP≤{fp_ceiling:.0%}): {pass_fail}")

    print("\n  Per-class recall:")
    for cls, (caught, total) in sorted(report.per_class_recall.items(), key=lambda x: x[0].value):
        pct = (caught / total * 100) if total else 0
        print(f"    {cls.value:<30} {caught}/{total}  ({pct:.0f}%)")

    if report.leaked_samples:
        print(f"\n  LEAKS ({len(report.leaked_samples)}):")
        for r in report.leaked_samples[:10]:
            print(f"    - [{r.sample.secret_class.value}] {r.sample.label!r}")
        if len(report.leaked_samples) > 10:
            print(f"    ... and {len(report.leaked_samples) - 10} more")

    if report.fp_samples:
        print(f"\n  FALSE POSITIVES ({len(report.fp_samples)}):")
        for r in report.fp_samples[:10]:
            print(f"    - {r.sample.label!r}: {r.sample.reason}")
        if len(report.fp_samples) > 10:
            print(f"    ... and {len(report.fp_samples) - 10} more")


def main() -> int:
    """CLI entry point for standalone harness runs."""
    parser = argparse.ArgumentParser(description="Nexus Brain redaction fuzz harness (spike 0.1)")
    parser.add_argument(
        "--sink",
        choices=[s.value for s in Sink],
        default=None,
        help="Run for a specific sink only (default: all three)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-sample results")
    parser.add_argument(
        "--recall-floor",
        type=float,
        default=PROPOSED_RECALL_FLOOR,
        help=f"Recall floor gate (default: {PROPOSED_RECALL_FLOOR})",
    )
    parser.add_argument(
        "--fp-ceiling",
        type=float,
        default=PROPOSED_FP_CEILING,
        help=f"FP ceiling gate (default: {PROPOSED_FP_CEILING})",
    )
    args = parser.parse_args()

    from .stub_redactor import stub_redact

    sinks = [Sink(args.sink)] if args.sink else list(Sink)
    reports = run_harness(stub_redact, sinks=sinks, verbose=args.verbose)

    all_pass = True
    for sink in sinks:
        report = reports[sink]
        print_report(report, args.recall_floor, args.fp_ceiling)
        if not report.gate_pass(args.recall_floor, args.fp_ceiling):
            all_pass = False

    print(f"\n{'ALL SINKS PASS' if all_pass else 'GATE FAILURE — see leaks above'}")
    print(f"  Proposed recall floor: {args.recall_floor:.0%}  |  Proposed FP ceiling: {args.fp_ceiling:.0%}")
    print(
        "\n  NOTE: Results shown use the REFERENCE STUB REDACTOR (spike 0.1 harness validation only).\n"
        "  The real Phase-2.3 engine must meet the proposed envelope above.\n"
        "  The stub intentionally misses high-entropy KV and base64 cases — see stub_redactor.py."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
