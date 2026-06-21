"""Unit tests for the cross-cutting identity / content string aliases (core/_types.py).

1.6a — the before-fork identity-hardening pass. `IdentityStr` (strip + min_length + control-char/NUL
reject + max_length cap) is the ONE shared alias every identity field across model/ + ports/ uses;
`TextStr` is its content counterpart (allows inline tab/newline; larger cap). It lives in the
cross-cutting core/_types.py so BOTH model/ and ports/ import it without a forbidden ports→model
cross-sibling import (§2.5 DAG).
"""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from _types import IDENTITY_MAX_LEN, TEXT_MAX_LEN, IdentityStr, TextStr

# spec(§2.5): this very import is the cross-sibling seam — core/_types.py is imported by BOTH
# model/ and ports/, which keeps the §2.5 subsystem DAG acyclic (no forbidden ports→model edge).

pytestmark = pytest.mark.unit

_ID: TypeAdapter[str] = TypeAdapter(IdentityStr)
_TX: TypeAdapter[str] = TypeAdapter(TextStr)


def test_identity_str_rejects_control_and_nul() -> None:
    # §4 parse-don't-trust + carry-forward (d): an identity admits NO control chars — NUL, any C0
    # control, DEL, and inline whitespace controls (\n/\t) are all rejected.
    for bad in ("a\x00b", "a\x01b", "a\x1fb", "a\x7fb", "line\nbreak", "tab\there"):
        with pytest.raises(ValidationError):
            _ID.validate_python(bad)


def test_identity_str_rejects_unicode_control_and_bidi() -> None:
    # 1.6a (extended before-fork): an identity rejects the FULL Unicode control/format/bidi/zero-
    # width/separator set (Cc incl C1, Cf, Zl, Zp) — the homoglyph/bidi/invisible-char injection
    # class on frozen cross-track references (paths, SHAs, citation tokens, SecretRef coords).
    # NOTE: \u escapes only — never embed a literal bidi/zero-width char in source (Trojan-Source).
    for bad in (
        "a\u202eb",  # RLO bidi-override (Cf)
        "a\u200bb",  # zero-width space (Cf)
        "a\ufeffb",  # BOM / ZWNBSP (Cf)
        "a\u0085b",  # NEL (Cc / C1)
        "a\u009fb",  # C1 control (Cc)
        "a\u2028b",  # line separator (Zl)
        "a\u2029b",  # paragraph separator (Zp)
    ):
        with pytest.raises(ValidationError):
            _ID.validate_python(bad)


def test_identity_str_allows_unicode_letters() -> None:
    # 1.6a: legitimate unicode letters/digits still validate — an identity may be a non-ASCII
    # filename (source_path/source_file). Only the invisible/bidi/control set is rejected.
    for good in ("пример.txt", "cafe-日本語", "src/app.py"):
        assert _ID.validate_python(good) == good


def test_identity_str_max_length() -> None:
    # bounded identity (carry-forward d): at the cap accepted, one over rejected.
    assert _ID.validate_python("x" * IDENTITY_MAX_LEN) == "x" * IDENTITY_MAX_LEN
    with pytest.raises(ValidationError):
        _ID.validate_python("x" * (IDENTITY_MAX_LEN + 1))


def test_identity_str_strips_and_rejects_whitespace_only() -> None:
    # LESSON 7: surrounding whitespace stripped; empty / whitespace-only rejected.
    assert _ID.validate_python("  abc  ") == "abc"
    for bad in ("", "   ", "\t\n"):
        with pytest.raises(ValidationError):
            _ID.validate_python(bad)


def test_text_str_allows_inline_whitespace_rejects_nul() -> None:
    # Q2/Q4: content ≠ identity — inline \t\n\r are legitimate (multi-line model output / cited
    # spans) AND legitimate multilingual unicode (INCL format chars) is KEPT (the bidi CONTENT
    # sanitization is Phase-2 ingest/redactor, LESSON 14); surrounding whitespace stripped; NUL /
    # other C0 controls / DEL / C1 (incl NEL) rejected; bounded.
    assert _TX.validate_python("line1\nline2\tend") == "line1\nline2\tend"
    assert _TX.validate_python("  hi\n") == "hi"
    assert _TX.validate_python("café 日本語 prose") == "café 日本語 prose"
    assert _TX.validate_python("a\u200bb") == "a\u200bb"  # zero-width Cf is KEPT in content
    assert _TX.validate_python("x" * TEXT_MAX_LEN) == "x" * TEXT_MAX_LEN
    for bad in ("", "   ", "a\x00b", "a\x0bb", "a\x85b", "a\x9fb", "x" * (TEXT_MAX_LEN + 1)):
        with pytest.raises(ValidationError):
            _TX.validate_python(bad)
