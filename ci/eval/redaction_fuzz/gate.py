"""Hard CI gate — runs the redaction fuzz harness against the REAL Phase-2.3 engine.

Unlike `harness.main()` (which runs the reference `stub_redact` for spike-0.1 self-validation), this
runner targets `core.ingest.redactor.CatchableSetRedactor` and EXITS NON-ZERO if any sink misses the
proposed envelope (recall >= floor, fp <= ceiling) or if the git-SHA false-positive subclass is not
exactly 0%. This is the §18 zero-leak-on-catchable hard gate.

Direction of dependency: ci/ imports core (never the reverse — core stays import-clean of ci/). The
core engine's flat package root is `<repo>/core`, so this runner puts it on `sys.path` before
importing `ingest.redactor`. Run from the repo root under the core uv env:

    uv --project core run python -m ci.eval.redaction_fuzz.gate

NETWORK: zero egress. SAFETY: synthetic secrets only.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .harness import PROPOSED_FP_CEILING, PROPOSED_RECALL_FLOOR, print_report, run_harness
from .types import Sink

# Put the core flat-package root (<repo>/core) on the path so `ingest.redactor` resolves.
_CORE_ROOT = Path(__file__).resolve().parents[3] / "core"
if str(_CORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_CORE_ROOT))


def main() -> int:
    from ingest.redactor import CatchableSetRedactor  # noqa: E402 (after the sys.path bootstrap)

    engine = CatchableSetRedactor()
    reports = run_harness(engine.redact)

    all_pass = True
    for sink in Sink:
        report = reports[sink]
        print_report(report, PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING)
        git_sha_fps = [fp for fp in report.fp_samples if fp.sample.label.startswith("git-sha")]
        if not report.gate_pass(PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING) or git_sha_fps:
            all_pass = False
            if git_sha_fps:
                print(f"  GIT-SHA FALSE POSITIVES (zero-tolerance): {len(git_sha_fps)}")

    print(f"\n{'ALL SINKS PASS — gate green' if all_pass else 'GATE FAILURE'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
