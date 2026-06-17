"""Unit tests for the IdGen + Seed determinism-seam ports (ARCHITECTURE.md §7, C-15)."""

from __future__ import annotations

import pytest

from ports.idgen import IdGen, Seed, SystemSeed, UuidGen
from testing.fakes import FakeIdGen, FakeSeed

pytestmark = pytest.mark.unit


def test_uuidgen_new_id_unique() -> None:
    # spec(§7): chunk/anchor/session ids (§5/§10) must be globally unique.
    gen = UuidGen()
    ids = [gen.new_id("chunk") for _ in range(1000)]
    assert len(set(ids)) == len(ids)


def test_uuidgen_new_id_nonempty_str() -> None:
    # spec(§7): id-minting contract shape.
    value = UuidGen().new_id("anchor")
    assert isinstance(value, str)
    assert value != ""


def test_fake_idgen_reproducible_sequence() -> None:
    # spec(§7): C-15 determinism seam — reproducible ids under test (golden-set stability).
    gen_a = FakeIdGen()
    gen_b = FakeIdGen()
    seq_a = [gen_a.new_id("chunk") for _ in range(5)]
    seq_b = [gen_b.new_id("chunk") for _ in range(5)]
    assert seq_a == seq_b
    assert len(set(seq_a)) == 5


def test_fake_idgen_distinct_kinds_no_collision() -> None:
    # spec(§7): typed-id separation (precursor to the 1.3 IdKind enum).
    gen = FakeIdGen()
    chunk_ids = {gen.new_id("chunk") for _ in range(5)}
    anchor_ids = {gen.new_id("anchor") for _ in range(5)}
    assert chunk_ids.isdisjoint(anchor_ids)


def test_fake_seed_reproducible_rng() -> None:
    # spec(§7): future sampling/jitter draws from Seed.rng() must be reproducible.
    rng_a = FakeSeed(42).rng()
    rng_b = FakeSeed(42).rng()
    seq_a = [rng_a.random() for _ in range(10)]
    seq_b = [rng_b.random() for _ in range(10)]
    assert seq_a == seq_b


def test_system_seed_varies() -> None:
    # spec(§7): real randomness is non-deterministic; fake is the deterministic counterpart.
    # Probabilistic entropy-wiring smoke (flake ~negligible); the deterministic guarantee
    # is pinned by test_fake_seed_reproducible_rng, not this absence-of-equality check.
    rng_a = SystemSeed().rng()
    rng_b = SystemSeed().rng()
    seq_a = [rng_a.random() for _ in range(10)]
    seq_b = [rng_b.random() for _ in range(10)]
    assert seq_a != seq_b


def test_idgen_seed_real_and_fake_conform() -> None:
    # spec(§7): DI substitutability — real + fake satisfy IdGen / Seed.
    assert isinstance(UuidGen(), IdGen)
    assert isinstance(FakeIdGen(), IdGen)
    assert isinstance(SystemSeed(), Seed)
    assert isinstance(FakeSeed(0), Seed)
