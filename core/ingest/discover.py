"""Source-agnostic file discovery — the front of the §8 ingest pipeline (ARCHITECTURE.md §8).

`discover(root)` walks a repo root and returns every regular file as a deterministic, sorted tuple
of `DiscoveredFile` (relative POSIX paths). It honors a root-level `.gitignore` AND `.brainignore`
(git wildmatch semantics via `pathspec`), ALWAYS excludes the VCS dir + the brain's own output dir,
is source-agnostic about other dotfile dirs (`.github/` is discovered), and NEVER follows symlinks
(no escape outside `root`, no traversal cycles).

v0 scope (design Q2): root-level `.gitignore`/`.brainignore` only; nested per-directory `.gitignore`
aggregation is a bounded future TODO. The output is the input the `add` pipeline (Task 2.4) folds
into chunks; `discover` performs NO filesystem mutation (the HostPort write chokepoint is Task 2.S).
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from pathspec import PathSpec
from pydantic import BaseModel, ConfigDict

from _types import IdentityStr

# Directory NAMES excluded unconditionally, anywhere in the tree, regardless of ignore files: the
# VCS dir (incl. nested submodule `.git`s) and the brain's own on-disk output dir. This is the
# always-exclude floor — it is not user-overridable via an ignore file.
ALWAYS_EXCLUDE_DIRS = frozenset({".git", ".project-brain"})

# Root-level ignore files honored, in git's precedence order (later files refine earlier ones).
IGNORE_FILES = (".gitignore", ".brainignore")

# Cap on a single ignore file read. A `.gitignore`/`.brainignore` beyond this is pathological (or
# hostile); skip it rather than exhaust memory. discover() is the front of every ingest, so one
# malformed root file must never deny indexing of the whole repo.
IGNORE_FILE_MAX_BYTES = 1_048_576  # 1 MiB


class DiscoveredFile(BaseModel):
    """One discovered regular file. Immutable + closed; `path` is relative to `root` (POSIX)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: IdentityStr


def _load_ignore_spec(root: Path, extra_ignores: Iterable[str]) -> PathSpec:
    """Build a gitwildmatch PathSpec from the root ignore files + any caller-supplied patterns."""
    lines: list[str] = []
    for name in IGNORE_FILES:
        ignore_file = root / name
        # Only a regular file is read; a symlinked ignore file is skipped (containment posture).
        if not (ignore_file.is_file() and not ignore_file.is_symlink()):
            continue
        try:
            if ignore_file.stat().st_size > IGNORE_FILE_MAX_BYTES:
                continue  # oversized → skip (don't read an unbounded attacker-controlled file)
            # errors="replace": a non-UTF-8/binary file masquerading as an ignore file must not
            # crash the whole discovery pass with UnicodeDecodeError.
            text = ignore_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue  # unreadable (perms/race) → skip, don't abort discovery
        lines.extend(text.splitlines())
    lines.extend(extra_ignores)
    return PathSpec.from_lines("gitwildmatch", lines)


def discover(root: Path | str, *, extra_ignores: Iterable[str] = ()) -> tuple[DiscoveredFile, ...]:
    """Return every non-ignored regular file under `root`, sorted, as `DiscoveredFile`s.

    `extra_ignores` are additional gitwildmatch patterns layered on top of the root ignore files
    (used by the pipeline to inject portfolio-level excludes); empty by default.
    """
    root = Path(root)
    # A non-existent / non-directory root is a caller error: fail loud rather than silently return
    # () (os.walk yields nothing for a non-dir, which would masquerade as "empty repo").
    if not root.is_dir():
        raise NotADirectoryError(f"discover() root is not a directory: {root}")
    spec = _load_ignore_spec(root, extra_ignores)
    found: list[DiscoveredFile] = []

    # followlinks=False keeps os.walk from descending symlinked dirs; we additionally prune them
    # (and any symlinked file) by name so a symlink to an out-of-root target can never be returned.
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)

        kept_dirs: list[str] = []
        for d in dirnames:
            if d in ALWAYS_EXCLUDE_DIRS:
                continue
            sub = current / d
            if sub.is_symlink():
                continue  # never traverse a symlinked directory (no escape / no cycles)
            rel_dir = sub.relative_to(root).as_posix()
            # A gitignore dir pattern (e.g. `node_modules/`) matched here prunes the whole subtree;
            # git semantics forbid re-including a file under an ignored dir, so this is safe.
            if spec.match_file(rel_dir + "/"):
                continue
            kept_dirs.append(d)
        dirnames[:] = kept_dirs

        for name in filenames:
            file_path = current / name
            if file_path.is_symlink():
                continue  # never return a symlinked file
            rel = file_path.relative_to(root).as_posix()
            if spec.match_file(rel):
                continue
            found.append(DiscoveredFile(path=rel))

    found.sort(key=lambda df: df.path)
    return tuple(found)
