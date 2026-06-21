"""
REFERENCE FAKE for the spike-0.4 bake-off rig — harness validation only.

⚠️  THIS IS NOT REAL `lancedb`. ⚠️
A deterministic in-memory + temp-dir double that satisfies `MaintenanceTarget` and
performs real (if trivial) work — it writes real bytes to a real dataset dir and holds
a real (bounded) build buffer — so the rig's instrumentation produces REAL numbers.
The real `lancedb`-backed target lands in Phase 3 (D-A17) and runs through the SAME rig.

Models the §6 maintenance contract:
  - post-write rows are "unindexed" until `optimize()` clears them (the flat-scan monitor),
  - each upsert is a new on-disk version (versions + transactions = steady-state disk),
  - `cleanup_old_versions(keep)` GC-exempts git-SHA-tagged versions regardless of age.

NETWORK: none. SAFETY: synthetic corpus only.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .types import CorpusChunk, IndexStats


@dataclass
class _Version:
    """One on-disk dataset version (a `lancedb` version + its transaction file analogue)."""

    vid: int
    path: Path
    sha_tag: str | None


class FakeMaintenanceStore:
    """A deterministic `MaintenanceTarget` double — validates the rig wiring; NOT real lancedb."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._versions_dir = self._root / "versions"
        self._versions_dir.mkdir(exist_ok=True)
        self._counter = 0
        self._versions: list[_Version] = []
        self._total_rows = 0
        self._unindexed_rows = 0

    def upsert_batch(self, rows: Sequence[CorpusChunk], sha_tag: str | None = None) -> None:
        """Write the batch as a NEW on-disk version; rows stay unindexed until optimize()."""
        self._counter += 1
        vid = self._counter
        vpath = self._versions_dir / f"v{vid:06d}.dat"
        payload = b"".join(c.text.encode("utf-8") for c in rows)
        vpath.write_bytes(payload)
        self._versions.append(_Version(vid=vid, path=vpath, sha_tag=sha_tag))
        self._total_rows += len(rows)
        self._unindexed_rows += len(rows)

    def optimize(self) -> None:
        """Real (trivial) bounded build work; clears the unindexed-rows backlog (§6 monitor → 0)."""
        # A small, REAL allocation so the RAM meter observes a non-zero peak inside optimize().
        # Synthetic placeholder ONLY — it does NOT model real lancedb build-RAM scaling (that
        # is what the Phase-3 real run measures); it just proves the meter captures optimize().
        scratch = bytearray(max(self._unindexed_rows, 1) * 64)
        _ = len(scratch)
        self._unindexed_rows = 0

    def index_stats(self) -> IndexStats:
        return IndexStats(
            num_unindexed_rows=self._unindexed_rows,
            num_indexed_rows=self._total_rows - self._unindexed_rows,
        )

    def cleanup_old_versions(self, keep: int) -> int:
        """
        Remove old plain versions beyond the most-recent `keep`, but GC-EXEMPT every
        SHA-tagged version (§6: git-SHA version tags double as the canonical SHA).

        `keep` is the count of most-recent PLAIN versions to retain. `keep=0` removes ALL
        plain versions (SHA-tagged ones still survive); a negative `keep` is rejected so a
        caller can't accidentally invert the contract.

        Returns the number of versions actually removed.
        """
        if keep < 0:
            raise ValueError(f"keep must be >= 0, got {keep}")
        sha_tagged = [v for v in self._versions if v.sha_tag is not None]
        plain = [v for v in self._versions if v.sha_tag is None]
        if keep > 0:
            kept_plain = plain[-keep:]
            removed_plain = plain[:-keep]
        else:
            kept_plain = []
            removed_plain = list(plain)
        for v in removed_plain:
            v.path.unlink(missing_ok=True)
        self._versions = sorted(sha_tagged + kept_plain, key=lambda v: v.vid)
        return len(removed_plain)

    def dataset_path(self) -> Path:
        return self._root

    def num_versions(self) -> int:
        return len(self._versions)

    def sha_tags(self) -> tuple[str, ...]:
        """Surviving git-SHA version tags (a Fake-only accessor for the GC-exempt assertion)."""
        return tuple(v.sha_tag for v in self._versions if v.sha_tag is not None)
