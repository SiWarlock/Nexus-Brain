"""File classification — the §8 ingest axes (ARCHITECTURE.md §8; closed-set vocab §5).

`classify(file)` maps a discovered file onto the four axes the frozen `Chunk` contract consumes:

- `doc_or_code` ∈ {doc, code}  — known doc extension → doc; everything else → code (source-agnostic
  total-map: schemas/config are structured source, not prose).
- `ownership`   ∈ {owned, foreign, supplemental}  — path under a known-vendor dir → foreign;
  generated/auxiliary (lockfiles) → supplemental; otherwise → owned. `owned` is the class the
  sync-phase drift radar may later refresh, so the v0 rule is load-bearing (see §8 doc-note).
- `producer`   (open-ended IdentityStr)  — name/path generated markers (lockfiles, `*_pb2.py`) →
  generated; otherwise → human. v0 is deterministic + name-based only (no content sniffing).
- `doc_type`   (open-ended IdentityStr)  — filename-mapped for docs (readme/architecture/changelog/
  adr/guide); code → source.

The `doc_or_code` and `ownership` CLOSED sets MUST stay identical to the frozen `Chunk` Literals —
`test_classification_vocab_matches_chunk_contract` (`typing.get_args`) fails on any drift. The
`Literal` declaration order below mirrors `core/model/chunk.py` exactly so that pin holds.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from _types import IdentityStr

# Known prose/doc extensions → `doc`; the source-agnostic fallback is `code` (design Q4).
DOC_EXTENSIONS = frozenset({".md", ".rst", ".txt", ".adoc"})

# Directory names that mark a vendored / third-party subtree → `foreign` ownership (design Q6).
VENDOR_DIRS = frozenset({"node_modules", "vendor", ".venv", "venv", "site-packages", "third_party"})

# Exact lockfile names treated as generated + supplemental (design Q5/Q6). Augmented by the
# `*.lock` suffix and the `*_pb2.py(i)` protobuf-stub markers below.
LOCKFILE_NAMES = frozenset(
    {
        "uv.lock",
        "poetry.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "Cargo.lock",
        "Pipfile.lock",
        "composer.lock",
        "Gemfile.lock",
    }
)

# Directory names (case-insensitive) that mark an Architecture-Decision-Record subtree → `adr`.
_ADR_DIRS = frozenset({"adr", "adrs", "decisions"})


def _is_generated(name: str) -> bool:
    """True for name/path-based generated markers (lockfiles, protobuf stubs)."""
    return (
        name in LOCKFILE_NAMES
        or name.endswith(".lock")
        or name.endswith("_pb2.py")
        or name.endswith("_pb2.pyi")
        or name.endswith("_pb2_grpc.py")
    )


def _doc_type(name: str, dir_parts: tuple[str, ...]) -> str:
    """Map a doc filename (+ its DIRECTORY segments, filename excluded) to a doc_type identity."""
    upper = name.upper()
    if upper.startswith("README"):
        return "readme"
    if upper.startswith("ARCHITECTURE"):
        return "architecture"
    if upper.startswith("CHANGELOG"):
        return "changelog"
    lower_name = name.lower()
    lower_dirs = {p.lower() for p in dir_parts}
    if lower_dirs & _ADR_DIRS or lower_name.startswith(("adr-", "adr_")):
        return "adr"
    return "guide"


class FileClassification(BaseModel):
    """The four §8 ingest axes for one file. Immutable + closed; closed sets mirror `Chunk`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_or_code: Literal["doc", "code"]
    producer: IdentityStr
    doc_type: IdentityStr
    ownership: Literal["owned", "foreign", "supplemental"]


def classify(file: Path | str, *, root: Path | None = None) -> FileClassification:
    """Classify a single file onto the four §8 ingest axes.

    `file` may be absolute or relative; if `root` is given an absolute `file` is made relative to it
    first, so a vendor-dir segment in `root`'s own ancestry can't falsely mark the file `foreign`.
    """
    path = Path(file)
    if root is not None and path.is_absolute():
        root = Path(root)
        try:
            path = path.relative_to(root)
        except ValueError:
            pass  # outside root → classify on the path as given
    parts = path.parts
    name = path.name

    doc_or_code: Literal["doc", "code"] = "doc" if path.suffix.lower() in DOC_EXTENSIONS else "code"

    producer = "generated" if _is_generated(name) else "human"

    ownership: Literal["owned", "foreign", "supplemental"]
    if any(part in VENDOR_DIRS for part in parts):
        ownership = "foreign"
    elif producer == "generated":
        ownership = "supplemental"
    else:
        ownership = "owned"

    doc_type = _doc_type(name, parts[:-1]) if doc_or_code == "doc" else "source"

    return FileClassification(
        doc_or_code=doc_or_code,
        producer=producer,
        doc_type=doc_type,
        ownership=ownership,
    )
