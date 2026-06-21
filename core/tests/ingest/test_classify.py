"""Unit tests for file classification (ARCHITECTURE.md §8; vocab guard §5).

classify(file) maps a discovered file onto the four ingest axes the frozen Chunk contract consumes:
doc_or_code ∈ {doc, code}, ownership ∈ {owned, foreign, supplemental}, and the open-ended
producer / doc_type identities. The closed sets MUST mirror the frozen Chunk contract — a get_args
drift test pins that alignment (anti-drift; mirrors test_chunk_closed_set_fields_reject_unknown).
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest
from pydantic import ValidationError

from ingest.classify import FileClassification, classify
from model.chunk import Chunk

pytestmark = pytest.mark.unit


def test_classify_doc_vs_code() -> None:
    # spec(§8): doc_or_code split — known doc extension → doc, source → code.
    assert classify("docs/intro.md").doc_or_code == "doc"
    assert classify("src/app.py").doc_or_code == "code"


def test_classify_doc_or_code_fallback_unknown_ext() -> None:
    # spec(§8): source-agnostic fallback (design Q4) — anything not a known doc ext → code.
    assert classify("config/settings.toml").doc_or_code == "code"
    assert classify("data/weird.xyz").doc_or_code == "code"


def test_classify_ownership_owned_default() -> None:
    # spec(§8): ownership default — first-party source → owned.
    assert classify("src/foo.py").ownership == "owned"


def test_classify_ownership_foreign_vendored() -> None:
    # spec(§8): a path under a known-vendor dir → foreign.
    assert classify("node_modules/x/y.js").ownership == "foreign"
    assert classify("vendor/lib/util.go").ownership == "foreign"


def test_classify_ownership_supplemental_generated() -> None:
    # spec(§8): a generated/auxiliary file (lockfile) → supplemental.
    assert classify("uv.lock").ownership == "supplemental"


def test_classify_producer_human_default() -> None:
    # spec(§8): producer default — ordinary source is human-authored.
    assert classify("src/app.py").producer == "human"


def test_classify_producer_generated_marker() -> None:
    # spec(§8): producer detection v0 — name/path-based generated markers.
    assert classify("uv.lock").producer == "generated"
    assert classify("proto/foo_pb2.py").producer == "generated"


def test_classify_doc_type_known_names() -> None:
    # spec(§8): doc_type filename mapping; code → source.
    assert classify("README.md").doc_type == "readme"
    assert classify("ARCHITECTURE.md").doc_type == "architecture"
    assert classify("CHANGELOG.md").doc_type == "changelog"
    assert classify("docs/guide.md").doc_type == "guide"
    assert classify("src/app.py").doc_type == "source"


def test_classify_doc_type_adr() -> None:
    # spec(§8): ADR-shaped docs → adr — a path segment `adr`/`decisions` (case-insensitive)
    # OR a filename starting `adr-`/`adr_`. A non-ADR doc stays guide; a code file stays source.
    assert classify("docs/adr/0001-choose-db.md").doc_type == "adr"
    assert classify("docs/decisions/0002-routing.md").doc_type == "adr"
    assert classify("docs/ADR/0003-caps.md").doc_type == "adr"  # case-insensitive segment
    assert classify("notes/adr-0004-policy.md").doc_type == "adr"  # filename prefix
    assert classify("docs/guide.md").doc_type == "guide"  # non-ADR doc
    assert classify("src/adr/helper.py").doc_type == "source"  # code is always source


def test_classify_doc_type_readme_precedence_in_adr_dir() -> None:
    # spec(§8): filename mapping wins over the dir-segment ADR rule (README in adr/ → readme).
    assert classify("docs/adr/README.md").doc_type == "readme"


def test_classify_absolute_path_with_root() -> None:
    # spec(§8): an absolute file is relativized against `root`, so a vendor-dir segment in root's
    # OWN ancestry does not falsely mark the file foreign (the documented `root=` use case).
    root = Path("/tmp/vendor/myproject")  # 'vendor' is in root's ancestry, not the file's subtree
    fc = classify(root / "src" / "app.py", root=root)
    assert fc.ownership == "owned"
    # without root=, the vendor segment in the absolute path would (wrongly) read as foreign:
    assert classify(root / "src" / "app.py").ownership == "foreign"


def test_classify_returns_non_empty_identities() -> None:
    # spec(§8): producer / doc_type are non-empty IdentityStr for every file.
    fc = classify("src/app.py")
    assert fc.producer and fc.doc_type


def test_classification_vocab_matches_chunk_contract() -> None:
    # spec(§5): frozen-Chunk closed-set alignment — the classifier's doc_or_code/ownership Literals
    # are EXACTLY Chunk's (anti-drift; mirrors test_chunk_closed_set_fields_reject_unknown).
    for field in ("doc_or_code", "ownership"):
        assert get_args(FileClassification.model_fields[field].annotation) == get_args(
            Chunk.model_fields[field].annotation
        )


def test_classification_rejects_unknown_closed_set() -> None:
    # spec(§5): closed-set integrity / parse-don't-trust — an out-of-set value raises.
    with pytest.raises(ValidationError):
        FileClassification(
            doc_or_code="image",  # type: ignore[arg-type]
            producer="human",
            doc_type="guide",
            ownership="owned",
        )
