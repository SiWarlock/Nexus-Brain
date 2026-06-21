"""Tests for the `add` ingest orchestration — Task 2.4 (ARCHITECTURE.md §8, §5, §14).

`add(root, …)` runs the §8 pipeline (discover→classify→chunk→redact-before-embed→assemble frozen
Chunk+Anchor→write the manifest via HostPort.perform): idempotent, R-PARTIAL with a per-file
malformed-content boundary + Trojan-Source/NUL sanitization, atomic no-half-swap manifest write.
The manifest write is the FIRST real FS mutation in core/ — it routes through the §14 chokepoint, so
these tests + the hardened static tripwire (test_host.py) are the runtime INV-allowlist proof.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ingest.pipeline import AddResult, add
from ingest.redactor import CatchableSetRedactor
from model.anchor import Anchor
from model.chunk import Chunk
from model.manifest import ProjectManifest
from model.redactor_iface import Redactor
from ports.host import HostAction, HostCapability, HostPort, HostResult, StandaloneHost
from ports.providers import EmbeddingProvider
from testing.fakes import FakeClock, FakeEmbeddingProvider, FakeIdGen, FakeRedactor

pytestmark = pytest.mark.unit

WRITE = HostCapability.OWN_STORE_WRITE
MANIFEST_REL = ".project-brain/manifest.json"


def _clock() -> FakeClock:
    return FakeClock(datetime(2026, 6, 21, tzinfo=UTC))


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


class _RecordingHost(StandaloneHost):
    """A real StandaloneHost that records every action reaching perform (the runtime-proof spy)."""

    def __init__(self, root: Path) -> None:
        super().__init__(root, [WRITE])
        self.performed: list[HostAction] = []

    def perform(self, action: HostAction) -> HostResult:
        result = super().perform(action)
        self.performed.append(action)
        return result


def _add(
    root: Path,
    *,
    host: HostPort | None = None,
    embedder: EmbeddingProvider | None = None,
    clock: FakeClock | None = None,
    idgen: FakeIdGen | None = None,
    redactor: Redactor | None = None,
    project_id: str = "proj",
) -> AddResult:
    return add(
        root,
        project_id=project_id,
        host=host or StandaloneHost(root, [WRITE]),
        embedder=embedder or FakeEmbeddingProvider(),
        clock=clock or _clock(),
        idgen=idgen or FakeIdGen(),
        redactor=redactor or FakeRedactor(),
    )


def test_add_empty_repo_writes_empty_manifest(tmp_path: Path) -> None:
    # spec(§8): R-PARTIAL — a doc-less repo ingests to an empty-artifacts manifest, no crash.
    result = _add(tmp_path)
    assert result.chunks == ()
    assert result.anchors == ()
    assert result.manifest.artifacts == ()
    assert (tmp_path / ".project-brain" / "manifest.json").is_file()


def test_add_full_pipeline_assembles_chunks(tmp_path: Path) -> None:
    # spec(§8): the full discover→classify→chunk→assemble path yields frozen Chunk+Anchor records
    # (Fake vector/ids/clock), one anchor per chunk, dispatched doc vs code.
    _write(tmp_path, "README.md", "# Title\n\nSome prose about the project.\n")
    _write(tmp_path, "foo.py", "def f(x):\n    return x + 1\n")
    clock = _clock()
    result = _add(tmp_path, clock=clock)
    assert result.chunks and all(isinstance(c, Chunk) for c in result.chunks)
    assert result.anchors and all(isinstance(a, Anchor) for a in result.anchors)
    assert len(result.anchors) == len(result.chunks)
    assert all(len(c.vector) == 8 for c in result.chunks)  # FakeEmbeddingProvider default dim
    assert all(c.created_at == clock.now() for c in result.chunks)  # Clock seam
    assert len({c.chunk_id for c in result.chunks}) == len(result.chunks)  # unique IdGen ids
    assert {c.source_path for c in result.chunks} == {"README.md", "foo.py"}


def test_add_redacts_before_embed(tmp_path: Path) -> None:
    # spec(§18): forbidden-#2 / Key-safety-#2 — redact runs at the persist sink BEFORE embed; the
    # stored chunk text is redacted AND its vector is the embedding of the REDACTED text.
    _write(tmp_path, "secrets.md", "# Keys\n\ntoken ghp_aaaaaaaaaaaaaaaaaaaa lives here.\n")
    embedder = FakeEmbeddingProvider()
    result = _add(tmp_path, embedder=embedder, redactor=CatchableSetRedactor())
    secret_chunks = [c for c in result.chunks if c.source_path == "secrets.md"]
    assert secret_chunks
    for c in secret_chunks:
        assert "ghp_aaaa" not in c.text  # the secret is gone
        assert "[REDACTED" in c.text  # replaced by a marker
        # FP-exact compare is safe here because FakeEmbeddingProvider is deterministic per text.
        assert embedder.embed([c.text])[0] == c.vector  # vector is of the REDACTED text


def test_add_writes_manifest_via_hostport(tmp_path: Path) -> None:
    # spec(§5): the manifest lands at <root>/.project-brain/manifest.json, written ONLY through
    # host.perform(OWN_STORE_WRITE); the on-disk bytes round-trip to the returned manifest.
    _write(tmp_path, "README.md", "# T\n\nbody\n")
    host = _RecordingHost(tmp_path)
    result = _add(tmp_path, host=host)
    manifest_path = tmp_path / ".project-brain" / "manifest.json"
    assert manifest_path.is_file()
    assert [a.capability for a in host.performed] == [WRITE]
    payload = host.performed[0].payload
    assert payload is not None and payload.rel_path == MANIFEST_REL
    # round-trip exercises the manifest's by-alias read path (on-disk camelCase keys → model).
    assert ProjectManifest.model_validate_json(manifest_path.read_text()) == result.manifest


def test_add_manifest_artifacts_derive_from_files(tmp_path: Path) -> None:
    # spec(§5): the manifest is a DERIVED projection — one artifact per ingested file with its
    # classification axes + raw-content hash; recipe fields (model/dim/chunker) stamped.
    _write(tmp_path, "README.md", "# T\n\nbody\n")
    _write(tmp_path, "foo.py", "def f():\n    return 1\n")
    embedder = FakeEmbeddingProvider()
    result = _add(tmp_path, embedder=embedder)
    arts = {a.path: a for a in result.manifest.artifacts}
    assert set(arts) == {"README.md", "foo.py"}
    assert arts["README.md"].doc_type == "readme"
    assert arts["README.md"].ownership == "owned"
    assert arts["foo.py"].doc_type == "source"
    raw = (tmp_path / "README.md").read_bytes()
    assert arts["README.md"].content_hash == hashlib.sha256(raw).hexdigest()
    assert result.manifest.embedding_model == embedder.model_version
    assert result.manifest.dimension == embedder.dimension
    assert result.manifest.chunker_version  # stamped, non-empty


def test_add_idempotent_reingest(tmp_path: Path) -> None:
    # spec(§8): `add` is idempotent — re-adding an unchanged repo yields an identical manifest.
    _write(tmp_path, "README.md", "# T\n\nbody\n")
    _write(tmp_path, "foo.py", "def f():\n    return 1\n")
    first = _add(tmp_path).manifest
    second = _add(tmp_path).manifest
    assert first == second
    assert len(second.artifacts) == 2  # no duplicate artifacts


def test_add_idempotent_after_change(tmp_path: Path) -> None:
    # spec(§8): a changed file updates exactly its artifact's content_hash — update, never append.
    _write(tmp_path, "README.md", "# T\n\nbody\n")
    before = _add(tmp_path).manifest
    _write(tmp_path, "README.md", "# T\n\nbody CHANGED\n")
    after = _add(tmp_path).manifest
    assert len(after.artifacts) == len(before.artifacts) == 1  # no append-duplicate
    assert after.artifacts[0].content_hash != before.artifacts[0].content_hash
    assert after.ingested_from_sha != before.ingested_from_sha  # generation marker moved


def test_add_partial_skips_malformed_file(tmp_path: Path) -> None:
    # spec(§8): R-PARTIAL — a NUL/control file trips the per-file boundary (the TextStr raise is
    # caught) and is skipped/quarantined; the rest of the repo still ingests; add does not raise.
    _write(tmp_path, "good.md", "# Good\n\nclean content.\n")
    (tmp_path / "bad.md").write_bytes(b"# Bad\n\nx\x00y has a NUL.\n")
    result = _add(tmp_path)  # must not raise
    paths = {c.source_path for c in result.chunks}
    assert "good.md" in paths
    assert "bad.md" not in paths  # skipped
    assert {a.path for a in result.manifest.artifacts} == {"good.md"}


def test_add_sanitizes_trojan_source_bidi(tmp_path: Path) -> None:
    # spec(§8 / LESSON 16): Trojan-Source bidi/zero-width chars (valid per TextStr, so they would
    # survive) are stripped at the ingest boundary before chunking — they never reach a chunk.
    _write(tmp_path, "doc.md", "# H\n\nvisible ‮ hidden ​ text\n")
    result = _add(tmp_path)
    doc_chunks = [c for c in result.chunks if c.source_path == "doc.md"]
    assert doc_chunks
    for c in doc_chunks:
        assert "‮" not in c.text  # bidi RLO stripped
        assert "​" not in c.text  # zero-width space stripped


def test_add_atomic_no_half_swap_on_failure(tmp_path: Path) -> None:
    # spec(§8): temp-generation / no-half-swap — a failure mid-add leaves no partial manifest; a
    # pre-existing manifest is retained unchanged (the write is the last, atomic step).
    _write(tmp_path, "README.md", "# T\n\nbody\n")
    manifest_path = tmp_path / ".project-brain" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text('{"prior": true}', encoding="utf-8")

    class _BoomEmbedder(FakeEmbeddingProvider):
        def embed(self, texts: Sequence[str]) -> list[list[float]]:
            raise RuntimeError("embed boom")

    with pytest.raises(RuntimeError):
        _add(tmp_path, embedder=_BoomEmbedder())
    assert manifest_path.read_text() == '{"prior": true}'  # retained, not half-swapped


def test_add_routes_all_mutation_via_perform(tmp_path: Path) -> None:
    # spec(§14): the runtime INV-allowlist proof via the real first mutator — running add, the
    # manifest write is the ONLY FS mutation and it goes through host.perform.
    _write(tmp_path, "README.md", "# T\n\nbody\n")
    _write(tmp_path, "foo.py", "def f():\n    return 1\n")
    host = _RecordingHost(tmp_path)
    _add(tmp_path, host=host)
    assert len(host.performed) == 1  # exactly one mutation
    assert host.performed[0].capability is WRITE
    payload = host.performed[0].payload
    assert payload is not None and payload.rel_path == MANIFEST_REL
