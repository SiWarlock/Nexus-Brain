"""The `add` ingest orchestration — Task 2.4 (ARCHITECTURE.md §8, §5, §14).

`add(root, …)` runs the §8 pipeline end-to-end against the frozen Phase-1 contracts + injected
`Fake*`/real seams:

    discover → classify → chunk (docs heading-split / code AST) → **redact** (persist sink, BEFORE
    embed — forbidden-#2 / Key-safety-#2) → embed → assemble frozen `Chunk` + `Anchor` → build the
    derived `ProjectManifest` → **write it via `HostPort.perform`** (the §14 chokepoint).

It is **idempotent** (re-adding an unchanged repo yields a byte-identical manifest; a changed file
updates exactly its artifact — keyed on the raw source unit's content hash) and **R-PARTIAL**: a
doc-less repo yields an empty-artifacts manifest, and a single malformed/binary/unreadable file
trips a per-file error boundary (skip/quarantine) rather than aborting the whole repo. CONTENT
sanitization is the consuming phase's job (LESSON 16): Trojan-Source bidi/zero-width chars (valid
per `TextStr`, so they would otherwise survive into a chunk) are STRIPPED before chunking;
NUL/C0/DEL content self-rejects at the `TextStr` boundary in the chunker and is caught + skipped.

The manifest write is the FIRST real FS mutation any `core/` module performs — it routes ONLY
through `HostPort.perform` (never a raw FS primitive), so the §14 INV-allowlist static tripwire
staying GREEN over this module IS the runtime per-mutator proof (Task 2.S; pinned by
`test_add_routes_all_mutation_via_perform`).

Phase-2 scope (against `Fake*`): assembles the records + writes the manifest. The LanceDB
embed/persist + `optimize()` + the real git-SHA version tag are Phase 3.1; here `ingested_from_sha`/
`lance_version_tag`/`last_resolved_sha` carry a deterministic v0 `recipe_sha` placeholder
(content-derived, host-mediated — no git shell-out). Context-augment (the `register="deep"` blurb)
is reserved for the Phase-3 embedding path.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import NamedTuple

from ingest.chunk import ChunkDraft, chunk_code, chunk_docs
from ingest.classify import FileClassification, classify
from ingest.discover import discover
from model.anchor import Anchor, AnchorState
from model.chunk import Chunk
from model.manifest import ManifestArtifact, ProjectManifest
from model.redactor_iface import Redactor, Sink
from ports.clock import Clock
from ports.host import HostCapability, HostIntent, HostPort, StoreWritePayload
from ports.idgen import IdGen
from ports.providers import EmbeddingProvider

# The derived manifest's on-disk location (project-brain-owned; §5). Written via HostPort.perform.
MANIFEST_REL_PATH = ".project-brain/manifest.json"
# Reproducibility-recipe stamps (§4 inv 1). Manifest schema baseline is 1 (the 1.2d migrator).
SCHEMA_VERSION = 1
CHUNKER_VERSION = "spine-chunker-2.2"
# v0 free-form manifest fields (tighten in their consuming phases — §16 policy / §12 sync).
_DOC_FORMAT_SPEC_RANGE = "v0"
_STALENESS_POINTER = "v0"
_POLICY_PATH = "policy.yaml"

# The Trojan-Source / invisible-injection class STRIPPED before chunking (LESSON 16). VALID per
# TextStr (Cf is permitted in content), so they would survive into a chunk unless removed here:
# bidi embeddings/overrides (U+202A-E), bidi isolates (U+2066-9), zero-width + LRM/RLM (U+200B-F),
# line/para seps (U+2028-9), BOM/ZWNBSP (U+FEFF). NUL/C0/DEL are NOT stripped — they self-reject
# at the TextStr boundary, so a file carrying them trips the per-file boundary → skipped instead.
_TROJAN_SOURCE_RE = re.compile("[\u202a-\u202e\u2066-\u2069\u200b-\u200f\u2028\u2029\ufeff]")


class _Ingested(NamedTuple):
    """One ingested file: its path, raw-content hash, classification, and chunk drafts."""

    path: str
    content_hash: str  # sha256 of the RAW source bytes — the per-file idempotency key
    classification: FileClassification
    drafts: tuple[ChunkDraft, ...]


class AddResult(NamedTuple):
    """The result of `add`: the assembled frozen records + the derived manifest that was written."""

    chunks: tuple[Chunk, ...]
    anchors: tuple[Anchor, ...]
    manifest: ProjectManifest


def _sanitize_content(text: str) -> str:
    """Strip the Trojan-Source / invisible-injection char class (LESSON 16, the consuming phase)."""
    return _TROJAN_SOURCE_RE.sub("", text)


def _ingest_file(root: Path, rel: str) -> _Ingested | None:
    """Read+sanitize+classify+chunk ONE file; None if the per-file boundary skips it (R-PARTIAL).

    A single malformed/binary/unreadable file must NEVER abort the whole repo. NUL/C0/DEL content
    self-rejects at the chunker `TextStr` boundary (the carry-forward pin) → caught → the file is
    skipped/quarantined; a binary file fails the strict UTF-8 decode and is likewise skipped. A
    file that yields no chunks (empty / all-whitespace / all-stripped) contributes no artifact.
    """
    try:
        raw = (root / rel).read_bytes()
        text = _sanitize_content(raw.decode("utf-8"))  # strict decode: binary → skip via except
        classification = classify(rel)
        if classification.doc_or_code == "doc":
            drafts = chunk_docs(text, classification, rel)
        else:
            drafts = chunk_code(text, classification, rel)
    except Exception:
        # Broad by design (R-PARTIAL): a UnicodeDecodeError (binary), a TextStr ValidationError
        # (NUL/control content), or any chunker fault on a hostile file degrades to skip — never
        # aborts the repo. Narrowing this is a resilience regression.
        return None
    if not drafts:
        return None  # no content → no artifact, no chunks
    return _Ingested(
        path=rel,
        content_hash=hashlib.sha256(raw).hexdigest(),
        classification=classification,
        drafts=drafts,
    )


def _recipe_sha(ingested: list[_Ingested]) -> str:
    """A deterministic v0 generation marker = sha256 over the sorted (path, raw-content-hash) pairs.

    Stands in for the §5 LanceDB git-SHA version tag (Phase-3) without a git shell-out (an
    un-host-mediated external read). Stable across unchanged re-adds (idempotency); moves when any
    file changes — so it tracks the generation deterministically. Real version-tag = Phase-3 carry.
    """
    h = hashlib.sha256()
    for item in sorted(ingested, key=lambda r: r.path):
        h.update(item.path.encode("utf-8"))
        h.update(b"\x00")
        h.update(item.content_hash.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _build_manifest(
    root: Path,
    project_id: str,
    ingested: list[_Ingested],
    embedder: EmbeddingProvider,
    recipe_sha: str,
) -> ProjectManifest:
    """Build the DERIVED projection: one artifact per ingested file (sorted) + the recipe stamps."""
    artifacts = tuple(
        ManifestArtifact(
            path=item.path,
            content_hash=item.content_hash,
            doc_type=item.classification.doc_type,
            producer=item.classification.producer,
            ownership=item.classification.ownership,
        )
        for item in sorted(ingested, key=lambda r: r.path)
    )
    return ProjectManifest(
        # camelCase here is the field ALIAS (the on-disk key) — pydantic's dataclass_transform keys
        # the init param on the alias for these two; validate_by_name accepts both at runtime.
        schemaVersion=SCHEMA_VERSION,
        project_id=project_id,
        source_repo=str(root.resolve()),
        ingestedFromSha=recipe_sha,  # v0 placeholder (mirrors the version tag; Phase-3 real SHA)
        embedding_model=embedder.model_version,
        dimension=embedder.dimension,
        chunker_version=CHUNKER_VERSION,
        doc_format_spec_range=_DOC_FORMAT_SPEC_RANGE,
        artifacts=artifacts,
        staleness_pointer=_STALENESS_POINTER,
        policy_path=_POLICY_PATH,
        lance_version_tag=recipe_sha,  # v0 placeholder (Phase-3 real LanceDB git-SHA tag)
    )


def _write_manifest(host: HostPort, manifest: ProjectManifest, project_id: str) -> None:
    """Serialize the manifest (on-disk camelCase aliases) and write it ONLY via the chokepoint."""
    content = manifest.model_dump_json(by_alias=True, indent=2).encode("utf-8")
    intent = HostIntent(
        capability=HostCapability.OWN_STORE_WRITE,
        summary=f"write project manifest for {project_id}",
        payload=StoreWritePayload(rel_path=MANIFEST_REL_PATH, content=content),
    )
    host.perform(host.authorize(intent))  # authorize→perform: the sole FS-mutation path (§14)


def add(
    root: Path | str,
    *,
    project_id: str,
    host: HostPort,
    embedder: EmbeddingProvider,
    clock: Clock,
    idgen: IdGen,
    redactor: Redactor,
) -> AddResult:
    """Ingest `root` → redacted, anchored chunks + a manifest written via `HostPort` (idempotent).

    Seams are injected (DI, LESSON 1): `host` (mutation chokepoint), `embedder`, `clock`, `idgen`,
    `redactor`. Returns the assembled `Chunk`/`Anchor` records + the manifest that was written.
    """
    root = Path(root)
    ingested: list[_Ingested] = []
    for discovered in discover(root):
        record = _ingest_file(root, discovered.path)
        if record is not None:
            ingested.append(record)

    # Flatten to (file, draft) pairs, then REDACT every draft's text at persist sink BEFORE embed
    # (forbidden-#2 / Key-safety-#2): the stored chunk text AND its vector are of the redacted text.
    flat = [(item, draft) for item in ingested for draft in item.drafts]
    redacted_texts = [redactor.redact(draft.text, Sink.PERSIST) for _, draft in flat]
    vectors = embedder.embed(redacted_texts)  # batch; a provider failure propagates (no half-swap)

    recipe_sha = _recipe_sha(ingested)
    chunks: list[Chunk] = []
    anchors: list[Anchor] = []
    for (item, draft), text, vector in zip(flat, redacted_texts, vectors, strict=True):
        chunks.append(
            Chunk(
                chunk_id=idgen.new_id("chunk"),
                project_id=project_id,
                source_path=item.path,
                doc_or_code=draft.doc_or_code,
                producer=draft.producer,
                doc_type=draft.doc_type,
                ownership=draft.ownership,
                register=draft.register,
                text=text,
                vector=vector,
                anchor=draft.anchor,
                # per-chunk identity = hash of the REDACTED chunk text — distinct from the manifest
                # artifact's raw-file content_hash (the file-level idempotency key). Chunk-level
                # tombstone+replace keying is a Phase-3 (§12) concern.
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                last_resolved_sha=recipe_sha,
                ingested_from_sha=recipe_sha,
                embedding_model_version=embedder.model_version,
                context_blurb=None,
                generation=0,
                tombstone=False,
                created_at=clock.now(),
            )
        )
        anchors.append(
            Anchor(
                anchor_id=idgen.new_id("anchor"),
                project_id=project_id,
                source_file=item.path,
                source_span=draft.anchor,
                target_path=item.path,
                target_line_start=draft.target_line_start,
                target_line_end=draft.target_line_end,
                target_symbol=draft.target_symbol,
                state=AnchorState.LIVE,  # freshly ingested → live (§10); revalidation is Phase-3+
                last_resolved_sha=recipe_sha,
                confidence=1.0,
            )
        )

    manifest = _build_manifest(root, project_id, ingested, embedder, recipe_sha)
    _write_manifest(host, manifest, project_id)
    return AddResult(chunks=tuple(chunks), anchors=tuple(anchors), manifest=manifest)
