"""
Shared record schemas + the `MaintenanceTarget` Protocol for the spike-0.4 rig.

Anchored to ARCHITECTURE.md §6: the LanceDB maintenance contract —
`optimize()` after each upsert batch + monitor `index_stats().num_unindexed_rows ≈ 0`;
scheduled `cleanup_old_versions()`; git-SHA version tags GC-exempt; RAM-bounded builds.

These are bench-local record schemas (NOT Appendix-A `core/` contract models) — like
spike 0.1's `types.py`. `ci/` must never be imported BY `core/` (the one-way import rule).
"""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


class MaintenanceMetric(enum.StrEnum):
    """The three §6 maintenance metrics the bake-off measures (the "invisible" budget axes)."""

    OPTIMIZE_LATENCY_MS = "optimize_latency_ms"
    """Wall-clock latency of `optimize()` after an upsert batch."""

    INDEX_BUILD_PEAK_RAM_BYTES = "index_build_peak_ram_bytes"
    """Peak Python-heap RAM during the batched index build (§6 RAM-bounded builds)."""

    STEADY_STATE_DISK_BYTES = "steady_state_disk_bytes"
    """On-disk bytes of the dataset dir (versions + transactions) after the run."""


@dataclass(frozen=True)
class CorpusChunk:
    """One synthetic chunk in the bake-off corpus (ASCII text → `size_bytes` is exact)."""

    repo_id: str
    chunk_id: str
    text: str

    @property
    def size_bytes(self) -> int:
        return len(self.text.encode("utf-8"))


@dataclass(frozen=True)
class Corpus:
    """A reproducible synthetic multi-repo corpus (the bake-off input)."""

    chunks: tuple[CorpusChunk, ...]
    n_repos: int
    seed: int

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)

    @property
    def repo_ids(self) -> tuple[str, ...]:
        """Distinct repo ids in first-seen order."""
        return tuple(dict.fromkeys(c.repo_id for c in self.chunks))


@dataclass(frozen=True)
class IndexStats:
    """The §6 `index_stats()` monitor surface — `num_unindexed_rows` is the load-bearing one."""

    num_unindexed_rows: int
    num_indexed_rows: int


@dataclass(frozen=True)
class BakeoffReport:
    """Aggregate metrics from one bake-off run."""

    optimize_latency_ms: float
    index_build_peak_ram_bytes: int
    steady_state_disk_bytes: int
    num_unindexed_rows_after_optimize: int
    num_versions: int
    corpus_total_chunks: int
    n_repos: int

    def metric(self, m: MaintenanceMetric) -> float:
        """Read a metric by its enum key (used by the CLI report printer)."""
        return {
            MaintenanceMetric.OPTIMIZE_LATENCY_MS: self.optimize_latency_ms,
            MaintenanceMetric.INDEX_BUILD_PEAK_RAM_BYTES: float(self.index_build_peak_ram_bytes),
            MaintenanceMetric.STEADY_STATE_DISK_BYTES: float(self.steady_state_disk_bytes),
        }[m]


@dataclass(frozen=True)
class BudgetEnvelope:
    """
    The PROPOSED "maintenance-contract invisible" budget — the rig's gate.

    Ceilings are PROPOSED-pending the Phase-3 real reference-Mac run (D-A17); the
    authoritative numbers are set there. `gate_pass` also folds in the §6 post-optimize
    monitor (`num_unindexed_rows == 0`): leaving rows on a flat scan IS a contract failure.
    """

    optimize_latency_ceiling_ms: float
    index_build_ram_ceiling_bytes: int
    steady_state_disk_ceiling_bytes: int

    def gate_pass(self, report: BakeoffReport) -> bool:
        return (
            report.optimize_latency_ms <= self.optimize_latency_ceiling_ms
            and report.index_build_peak_ram_bytes <= self.index_build_ram_ceiling_bytes
            and report.steady_state_disk_bytes <= self.steady_state_disk_ceiling_bytes
            and report.num_unindexed_rows_after_optimize == 0
        )


@runtime_checkable
class MaintenanceTarget(Protocol):
    """
    The §6 maintenance surface the rig drives — the contract the Phase-3 real
    `lancedb`-backed adapter implements (swap the Fake for it, set the real budget).

    Minimal by design: exactly the §6 maintenance operations + the two accessors the
    disk/version meters need. `sha_tag` on `upsert_batch` models §6 git-SHA version
    tagging at version-creation (those tags are GC-exempt in `cleanup_old_versions`).
    """

    def upsert_batch(self, rows: Sequence[CorpusChunk], sha_tag: str | None = None) -> None: ...

    def optimize(self) -> None: ...

    def index_stats(self) -> IndexStats: ...

    def cleanup_old_versions(self, keep: int) -> int: ...

    def dataset_path(self) -> Path: ...

    def num_versions(self) -> int: ...
