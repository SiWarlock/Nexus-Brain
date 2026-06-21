"""
Tests for the LanceDB maintenance-contract bake-off rig INFRASTRUCTURE (spike 0.4).

These tests verify the rig components (types, corpus generator, measurement
instrumentation, the reference Fake) work end-to-end — they do NOT run the real
`lancedb` backend (that is the Phase-3 authoritative reference-Mac carry, D-A17).

The Fake baseline validates wiring only; its numbers are tiny by construction and
sit well inside the conservative PROPOSED envelope — proving the rig measures REAL
quantities (latency / RAM / disk) ready to swap onto a real `MaintenanceTarget`.

Run: cd core && uv run python -m pytest ../ci/bench/lancedb_maintenance/test_harness_infra.py -v
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

import pytest

from .corpus import (
    DEFAULT_CHUNKS_PER_REPO,
    DEFAULT_N_REPOS,
    generate_corpus,
)
from .fake_store import FakeMaintenanceStore
from .harness import (
    DEFAULT_ENVELOPE,
    PROPOSED_INDEX_BUILD_RAM_CEILING_BYTES,
    PROPOSED_OPTIMIZE_LATENCY_CEILING_MS,
    PROPOSED_STEADY_STATE_DISK_CEILING_BYTES,
    measure_dir_bytes,
    measure_latency_ms,
    measure_peak_ram_bytes,
    run_bakeoff,
)
from .types import (
    BakeoffReport,
    BudgetEnvelope,
    MaintenanceTarget,
)

_SHA40 = "a" * 40  # synthetic 40-char git-SHA-1 hex version tag


def _report(
    optimize_latency_ms: float = 50.0,
    index_build_peak_ram_bytes: int = 1_000_000,
    steady_state_disk_bytes: int = 1_000_000,
    num_unindexed_rows_after_optimize: int = 0,
) -> BakeoffReport:
    """A within-envelope baseline report; override one field to push it over a ceiling."""
    return BakeoffReport(
        optimize_latency_ms=optimize_latency_ms,
        index_build_peak_ram_bytes=index_build_peak_ram_bytes,
        steady_state_disk_bytes=steady_state_disk_bytes,
        num_unindexed_rows_after_optimize=num_unindexed_rows_after_optimize,
        num_versions=1,
        corpus_total_chunks=10,
        n_repos=1,
    )


# ---------------------------------------------------------------------------
# 1. MaintenanceTarget Protocol conformance (LESSON 1)
# ---------------------------------------------------------------------------

def test_maintenance_target_protocol_conformance(tmp_path: Path) -> None:
    # The Fake structurally satisfies the runtime_checkable target the Phase-3
    # real `lancedb`-backed store must also satisfy.
    store = FakeMaintenanceStore(tmp_path)
    assert isinstance(store, MaintenanceTarget)


# ---------------------------------------------------------------------------
# 2 + 3. Corpus generator — reproducible + representative-profile shape
# ---------------------------------------------------------------------------

def test_corpus_reproducible_with_seed() -> None:
    # Task 1.1 determinism posture — a bench input must be reproducible run-to-run.
    a = generate_corpus(seed=42)
    b = generate_corpus(seed=42)
    c = generate_corpus(seed=43)
    assert a == b, "same seed must yield a byte-identical corpus"
    assert a != c, "a different seed must yield a different corpus"


def test_corpus_profile_shape() -> None:
    # A *representative multi-repo* corpus, not a degenerate one (§6 / the 0.4 task).
    corpus = generate_corpus(
        seed=1, n_repos=3, chunks_per_repo=10, min_chunk_bytes=64, max_chunk_bytes=256
    )
    assert len(corpus.repo_ids) == 3
    assert corpus.total_chunks == 30
    for chunk in corpus.chunks:
        assert 64 <= chunk.size_bytes <= 256
    # the documented defaults exist + are honored when unspecified
    default = generate_corpus(seed=1)
    assert len(default.repo_ids) == DEFAULT_N_REPOS
    assert default.total_chunks == DEFAULT_N_REPOS * DEFAULT_CHUNKS_PER_REPO


# ---------------------------------------------------------------------------
# 4 + 5 + 6. Measurement instrumentation is REAL (ready to read real numbers)
# ---------------------------------------------------------------------------

def test_latency_meter_captures_elapsed() -> None:
    # The meter must measure REAL `optimize()` latency in Phase 3, not fake it.
    ticks = iter([10.0, 10.25])  # monotonic seconds: a 0.25s == 250ms delta
    result, ms = measure_latency_ms(lambda: "ok", clock=lambda: next(ticks))
    assert result == "ok"
    assert abs(ms - 250.0) < 1.0


def test_ram_meter_captures_allocation() -> None:
    # §6 RAM-bounded index builds — the rig must really measure peak build RAM.
    def alloc() -> int:
        data = bytearray(10_000_000)  # ~10 MB; the peak is recorded during this allocation
        return len(data)

    _, peak = measure_peak_ram_bytes(alloc)
    assert peak >= 8_000_000, f"tracemalloc peak {peak} did not capture the ~10MB allocation"


def test_ram_meter_preserves_outer_tracemalloc_session() -> None:
    # The meter must NOT tear down an outer tracemalloc session it didn't start.
    tracemalloc.start()
    try:
        assert tracemalloc.is_tracing()
        measure_peak_ram_bytes(lambda: bytearray(1_000_000))
        assert tracemalloc.is_tracing(), "meter stopped an outer tracemalloc session"
    finally:
        tracemalloc.stop()


def test_disk_meter_matches_on_disk_bytes(tmp_path: Path) -> None:
    # §6 steady-state disk (versions + transactions) must be really measured.
    (tmp_path / "a.bin").write_bytes(b"x" * 1000)
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.bin").write_bytes(b"y" * 500)
    assert measure_dir_bytes(tmp_path) == 1500


def test_disk_meter_skips_symlinks(tmp_path: Path) -> None:
    # On-disk footprint must not double-count a symlinked version file.
    (tmp_path / "real.bin").write_bytes(b"z" * 800)
    (tmp_path / "link.bin").symlink_to(tmp_path / "real.bin")
    assert measure_dir_bytes(tmp_path) == 800


# ---------------------------------------------------------------------------
# 7. run_bakeoff returns a populated BakeoffReport (+ the §6 num_unindexed monitor)
# ---------------------------------------------------------------------------

def test_run_bakeoff_report_fields(tmp_path: Path) -> None:
    # §6 maintenance contract — `optimize()` after the batch + the
    # `num_unindexed_rows ≈ 0` monitor; all metric fields populated.
    store = FakeMaintenanceStore(tmp_path)
    corpus = generate_corpus(seed=7, n_repos=2, chunks_per_repo=20)
    report = run_bakeoff(store, corpus)
    assert isinstance(report, BakeoffReport)
    assert report.optimize_latency_ms >= 0.0
    assert report.index_build_peak_ram_bytes > 0
    assert report.steady_state_disk_bytes > 0
    assert report.num_unindexed_rows_after_optimize == 0
    assert report.num_versions >= 1
    assert report.corpus_total_chunks == 40


# ---------------------------------------------------------------------------
# 8. Budget envelope gate — pass within ceilings, fail when any metric exceeds one
# ---------------------------------------------------------------------------

def test_budget_gate_pass_and_fail() -> None:
    # The "maintenance-contract invisible" envelope evaluation (the rig's gate).
    env = BudgetEnvelope(
        optimize_latency_ceiling_ms=100.0,
        index_build_ram_ceiling_bytes=10_000_000,
        steady_state_disk_ceiling_bytes=10_000_000,
    )
    assert env.gate_pass(_report()) is True
    assert env.gate_pass(_report(optimize_latency_ms=200.0)) is False
    assert env.gate_pass(_report(index_build_peak_ram_bytes=20_000_000)) is False
    assert env.gate_pass(_report(steady_state_disk_bytes=20_000_000)) is False
    # the §6 post-optimize monitor is part of the gate: unindexed rows left behind fails.
    assert env.gate_pass(_report(num_unindexed_rows_after_optimize=5)) is False


def test_default_envelope_passes_fake_baseline(tmp_path: Path) -> None:
    # The Fake baseline must sit inside the conservative PROPOSED envelope (proves the
    # rig runs end-to-end + the PROPOSED ceilings are sane). Ceilings are PROPOSED-pending-Phase-3.
    assert PROPOSED_OPTIMIZE_LATENCY_CEILING_MS > 0
    assert PROPOSED_INDEX_BUILD_RAM_CEILING_BYTES > 0
    assert PROPOSED_STEADY_STATE_DISK_CEILING_BYTES > 0
    store = FakeMaintenanceStore(tmp_path)
    report = run_bakeoff(store, generate_corpus(seed=9, n_repos=2, chunks_per_repo=10))
    assert DEFAULT_ENVELOPE.gate_pass(report) is True


# ---------------------------------------------------------------------------
# 9. cleanup_old_versions GC-exempts git-SHA version tags (§6 sub-rule)
# ---------------------------------------------------------------------------

def test_cleanup_old_versions_gc_exempts_sha_tags(tmp_path: Path) -> None:
    # "git-SHA version tags GC-exempt → double as the canonical SHA" — cleanup removes
    # old plain versions but retains SHA-tagged ones regardless of age.
    store = FakeMaintenanceStore(tmp_path)
    corpus = generate_corpus(seed=3, n_repos=1, chunks_per_repo=4)
    batch = list(corpus.chunks)
    store.upsert_batch(batch)                    # v1 plain (oldest)
    store.upsert_batch(batch, sha_tag=_SHA40)    # v2 SHA-tagged (old)
    store.upsert_batch(batch)                    # v3 plain
    store.upsert_batch(batch)                    # v4 plain (newest)
    assert store.num_versions() == 4

    removed = store.cleanup_old_versions(keep=1)  # keep newest 1 plain + all SHA-tagged
    assert removed == 2                            # v1, v3 removed
    assert store.num_versions() == 2              # v4 (kept) + v2 (SHA-exempt)
    assert _SHA40 in store.sha_tags(), "the SHA-tagged version must survive GC even when old"


def test_cleanup_keep_zero_removes_all_plain_keeps_sha(tmp_path: Path) -> None:
    # keep=0 retains zero plain versions but SHA-tagged versions are still GC-exempt.
    store = FakeMaintenanceStore(tmp_path)
    batch = list(generate_corpus(seed=3, n_repos=1, chunks_per_repo=2).chunks)
    store.upsert_batch(batch)                    # v1 plain
    store.upsert_batch(batch, sha_tag=_SHA40)    # v2 SHA-tagged
    store.upsert_batch(batch)                    # v3 plain
    removed = store.cleanup_old_versions(keep=0)
    assert removed == 2                           # both plain versions removed
    assert store.num_versions() == 1             # only the SHA-tagged survives
    assert store.sha_tags() == (_SHA40,)


def test_cleanup_negative_keep_rejected(tmp_path: Path) -> None:
    # A negative keep can't be allowed to invert the contract — reject it.
    store = FakeMaintenanceStore(tmp_path)
    store.upsert_batch(list(generate_corpus(seed=3, n_repos=1, chunks_per_repo=2).chunks))
    with pytest.raises(ValueError):
        store.cleanup_old_versions(keep=-1)


# ---------------------------------------------------------------------------
# Behavioral invariant the Phase-3 real target must also honor
# ---------------------------------------------------------------------------

def test_fake_unindexed_rows_nonzero_before_optimize(tmp_path: Path) -> None:
    # Post-write rows fall to a flat scan until `optimize()` clears them — the monitor
    # must observe a NON-zero before optimize (else the rig can't catch a regression).
    store = FakeMaintenanceStore(tmp_path)
    corpus = generate_corpus(seed=5, n_repos=1, chunks_per_repo=8)
    store.upsert_batch(list(corpus.chunks))
    assert store.index_stats().num_unindexed_rows > 0
    store.optimize()
    assert store.index_stats().num_unindexed_rows == 0
