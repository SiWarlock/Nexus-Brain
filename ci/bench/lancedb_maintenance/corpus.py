"""
Seeded synthetic multi-repo corpus generator for the spike-0.4 bake-off rig.

Reproducible by construction: a `random.Random(seed)` drives every choice, so the
same seed yields a byte-identical `Corpus` and a different seed a different one
(Task 1.1 determinism posture). Standalone — no `core/` import (0.1 precedent).

The default profile is a deliberate judgement call for a "representative portfolio";
scale it up for the Phase-3 real run against a real portfolio.
"""

from __future__ import annotations

import random
import string

from .types import Corpus, CorpusChunk

# --- The documented default "representative portfolio" profile -------------
DEFAULT_N_REPOS = 5
"""Several synthetic repos — a small multi-repo portfolio, not one degenerate repo."""

DEFAULT_CHUNKS_PER_REPO = 200
"""A realistic per-repo chunk count for a mid-size codebase + docs."""

DEFAULT_MIN_CHUNK_BYTES = 128
"""Lower bound of the chunk-size distribution (a small doc/code chunk)."""

DEFAULT_MAX_CHUNK_BYTES = 2048
"""Upper bound of the chunk-size distribution (a large code chunk / file section)."""

# ASCII-only alphabet → each character is exactly one UTF-8 byte, so a chunk's
# `size_bytes` equals its requested character length (keeps the profile bounds exact).
_ALPHABET = string.ascii_letters + string.digits + " \n\t"


def generate_corpus(
    seed: int,
    n_repos: int = DEFAULT_N_REPOS,
    chunks_per_repo: int = DEFAULT_CHUNKS_PER_REPO,
    min_chunk_bytes: int = DEFAULT_MIN_CHUNK_BYTES,
    max_chunk_bytes: int = DEFAULT_MAX_CHUNK_BYTES,
) -> Corpus:
    """
    Build a reproducible synthetic multi-repo corpus.

    Args:
        seed: drives the RNG — same seed → byte-identical corpus.
        n_repos: number of synthetic repos.
        chunks_per_repo: chunks generated per repo.
        min_chunk_bytes / max_chunk_bytes: inclusive chunk-size distribution bounds.

    Returns:
        A frozen `Corpus` of `n_repos * chunks_per_repo` chunks.
    """
    rng = random.Random(seed)
    chunks: list[CorpusChunk] = []
    for r in range(n_repos):
        repo_id = f"repo_{r:03d}"
        for c in range(chunks_per_repo):
            size = rng.randint(min_chunk_bytes, max_chunk_bytes)
            text = "".join(rng.choices(_ALPHABET, k=size))
            chunks.append(
                CorpusChunk(repo_id=repo_id, chunk_id=f"{repo_id}:chunk_{c:05d}", text=text)
            )
    return Corpus(chunks=tuple(chunks), n_repos=n_repos, seed=seed)
