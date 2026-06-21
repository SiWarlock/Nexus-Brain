"""
Measurement harness — drives a `MaintenanceTarget` over a corpus and reports the §6
maintenance metrics. The instrumentation is REAL stdlib (latency = monotonic-clock
delta; RAM = `tracemalloc` peak; disk = dir-walk byte sum) so it is ready to read real
`optimize()` latency / build RAM / on-disk bytes when swapped onto real `lancedb` in Phase 3.

Usage (as a script):
    cd project-brain-contract
    python -m ci.bench.lancedb_maintenance.harness [--verbose] [--seed N]
        [--n-repos N] [--chunks-per-repo N]

Or import and call `run_bakeoff(target, corpus)` programmatically (e.g. from Phase 3,
passing a real `lancedb`-backed `MaintenanceTarget`).

NETWORK: zero egress. DEP: stdlib only (no new runtime dependency — scope B, D-A17).
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from .corpus import DEFAULT_CHUNKS_PER_REPO, DEFAULT_N_REPOS, generate_corpus
from .fake_store import FakeMaintenanceStore
from .types import (
    BakeoffReport,
    BudgetEnvelope,
    Corpus,
    MaintenanceMetric,
    MaintenanceTarget,
)

DEFAULT_BATCH_SIZE = 128
"""Default ingest batch size — upserts accumulate as on-disk versions (steady-state disk)."""

DEFAULT_SEED = 1337
"""Default corpus seed for the CLI Fake-baseline run."""

# ---------------------------------------------------------------------------
# PROPOSED budget envelope (the deliverable of spike 0.4) — the "invisible" ceilings.
#
# ⚠ PROPOSED, pending the Phase-3 real reference-Mac run (Apple-Silicon, 16–32 GB).
#   These are conservative PLACEHOLDERS chosen agent-side to make the rig's gate
#   meaningful against the Fake baseline. The AUTHORITATIVE ceilings are set from the
#   real `lancedb` + real-embedding + real-multi-repo-corpus run (D-A17) and folded
#   into ARCHITECTURE.md §6 / the perf baseline there — exactly like spike 0.1's
#   PROPOSED_RECALL_FLOOR. Do NOT treat these as a frozen hardware budget.
# ---------------------------------------------------------------------------

PROPOSED_OPTIMIZE_LATENCY_CEILING_MS: float = 5_000.0
"""`optimize()` after a batch should be "invisible" — PROPOSED 5s ceiling pending Phase-3."""

PROPOSED_INDEX_BUILD_RAM_CEILING_BYTES: int = 2 * 1024**3
"""§6 RAM-bounded index builds — PROPOSED 2 GB peak ceiling on a 16–32 GB Mac, pending Phase-3."""

PROPOSED_STEADY_STATE_DISK_CEILING_BYTES: int = 5 * 1024**3
"""Steady-state versions + transactions — PROPOSED 5 GB ceiling, pending Phase-3."""

DEFAULT_ENVELOPE = BudgetEnvelope(
    optimize_latency_ceiling_ms=PROPOSED_OPTIMIZE_LATENCY_CEILING_MS,
    index_build_ram_ceiling_bytes=PROPOSED_INDEX_BUILD_RAM_CEILING_BYTES,
    steady_state_disk_ceiling_bytes=PROPOSED_STEADY_STATE_DISK_CEILING_BYTES,
)


# ---------------------------------------------------------------------------
# REAL measurement instrumentation (stdlib; each is unit-tested against a known quantity)
# ---------------------------------------------------------------------------

def measure_latency_ms[T](
    fn: Callable[[], T], clock: Callable[[], float] = time.monotonic
) -> tuple[T, float]:
    """Run `fn`, returning (result, elapsed_ms) from a monotonic-clock delta.

    `clock` is injectable (returns seconds) so the meter is deterministically testable.
    """
    start = clock()
    result = fn()
    end = clock()
    return result, (end - start) * 1000.0


def measure_peak_ram_bytes[T](fn: Callable[[], T]) -> tuple[T, int]:
    """Run `fn` under `tracemalloc`, returning (result, peak_python_heap_bytes).

    Nesting-safe: if `tracemalloc` is already tracing (an outer session), we measure
    against a reset peak but do NOT stop that outer session on exit.
    """
    started_here = not tracemalloc.is_tracing()
    if started_here:
        tracemalloc.start()
    try:
        tracemalloc.reset_peak()
        result = fn()
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        if started_here:
            tracemalloc.stop()
    return result, peak


def measure_dir_bytes(path: Path) -> int:
    """Sum the on-disk byte size of every regular file under `path` (versions + transactions).

    Symlinks are skipped so a real dataset dir that symlinks version files is not
    double-counted (the meter reports the dataset's own on-disk footprint).
    """
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total


# ---------------------------------------------------------------------------
# The bake-off
# ---------------------------------------------------------------------------

def run_bakeoff(
    target: MaintenanceTarget,
    corpus: Corpus,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    clock: Callable[[], float] = time.monotonic,
) -> BakeoffReport:
    """
    Drive `target` over `corpus` and return a populated `BakeoffReport`.

    Sequence (mirrors the §6 maintenance contract):
      1. ingest the corpus in batches (accumulating on-disk versions) AND run `optimize()`
         under the RAM meter — the real `lancedb` index build happens in `optimize()`, so
         the peak build RAM must span the whole ingest+optimize window, not just ingest,
      2. time `optimize()` (inside that window) for its latency,
      3. read the post-optimize `index_stats()` monitor (`num_unindexed_rows` must be 0),
      4. measure steady-state on-disk bytes of the dataset dir.
    """
    chunks = list(corpus.chunks)
    batches = [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]
    latencies: dict[str, float] = {}

    def _build_and_index() -> None:
        for batch in batches:
            target.upsert_batch(batch)
        _opt_result, latency_ms = measure_latency_ms(target.optimize, clock=clock)
        latencies["optimize_ms"] = latency_ms

    _build_result, peak_ram = measure_peak_ram_bytes(_build_and_index)
    latency_ms = latencies["optimize_ms"]
    stats = target.index_stats()
    disk = measure_dir_bytes(target.dataset_path())

    return BakeoffReport(
        optimize_latency_ms=latency_ms,
        index_build_peak_ram_bytes=peak_ram,
        steady_state_disk_bytes=disk,
        num_unindexed_rows_after_optimize=stats.num_unindexed_rows,
        num_versions=target.num_versions(),
        corpus_total_chunks=corpus.total_chunks,
        n_repos=corpus.n_repos,
    )


def print_report(
    report: BakeoffReport,
    envelope: BudgetEnvelope,
    *,
    target_label: str = "Fake baseline",
    verbose: bool = False,
) -> None:
    """Print a human-readable bake-off report to stdout (`target_label` names the target)."""
    gate = "PASS" if envelope.gate_pass(report) else "FAIL"
    print(f"\n=== LanceDB maintenance bake-off ({target_label}) — {gate} ===")
    print(
        f"  corpus: {report.n_repos} repos, {report.corpus_total_chunks} chunks, "
        f"{report.num_versions} versions"
    )
    ceilings = {
        MaintenanceMetric.OPTIMIZE_LATENCY_MS: float(envelope.optimize_latency_ceiling_ms),
        MaintenanceMetric.INDEX_BUILD_PEAK_RAM_BYTES: float(envelope.index_build_ram_ceiling_bytes),
        MaintenanceMetric.STEADY_STATE_DISK_BYTES: float(envelope.steady_state_disk_ceiling_bytes),
    }
    for metric in MaintenanceMetric:
        value = report.metric(metric)
        ceil = ceilings[metric]
        mark = "ok" if value <= ceil else "OVER"
        print(f"  {metric.value:<32} {value:>18,.1f}  (PROPOSED ≤ {ceil:,.0f})  [{mark}]")
    print(
        f"  {'num_unindexed_rows_after_optimize':<32} "
        f"{report.num_unindexed_rows_after_optimize:>18}  (§6 monitor; must be 0)"
    )
    if verbose:
        print(
            "\n  NOTE: numbers above are the REFERENCE FAKE baseline (rig validation only).\n"
            "  The PROPOSED ceilings are placeholders pending the Phase-3 real reference-Mac run."
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — runs the bake-off end-to-end against the reference Fake."""
    parser = argparse.ArgumentParser(
        description="Nexus Brain LanceDB maintenance-contract bake-off rig (spike 0.4)"
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="corpus seed")
    parser.add_argument("--n-repos", type=int, default=DEFAULT_N_REPOS, help="synthetic repo count")
    parser.add_argument(
        "--chunks-per-repo", type=int, default=DEFAULT_CHUNKS_PER_REPO, help="chunks per repo"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="print the methodology note")
    args = parser.parse_args(argv)

    corpus = generate_corpus(
        seed=args.seed, n_repos=args.n_repos, chunks_per_repo=args.chunks_per_repo
    )
    with tempfile.TemporaryDirectory() as td:
        target = FakeMaintenanceStore(Path(td))
        report = run_bakeoff(target, corpus)
        gate_pass = DEFAULT_ENVELOPE.gate_pass(report)
        print_report(report, DEFAULT_ENVELOPE, verbose=args.verbose)

    print(
        "\n  This is the spike-0.4 RIG run against the REFERENCE FAKE — NOT the authoritative\n"
        "  bake-off. The real reference-Mac run (real lancedb + embedding model + multi-repo\n"
        "  corpus) is a Phase-3 carry (deferred, not dropped — D-A17); it reuses this rig and\n"
        "  sets the authoritative budget numbers."
    )
    return 0 if gate_pass else 1


if __name__ == "__main__":
    sys.exit(main())
