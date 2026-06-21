"""Cross-cutting hardened string aliases — the ONE identity/content type pair (1.6a).

A foundational, CROSS-CUTTING module: importable by BOTH `model/` and `ports/` without a forbidden
`ports`→`model` cross-sibling import (§2.5 DAG — cross-cutting layers import from anywhere). It
consolidates the 11 duplicated `_StrippedStr`/`IdentityStr` aliases into ONE shared definition and
HARDENS it (extends LESSON 7): strip + non-empty + reject control/format/bidi chars + a length cap.

- `IdentityStr` — ids / paths / SHAs / names / markers / dict-keys / symbols. TIGHT: strips
  surrounding whitespace, rejects empty / whitespace-only, rejects the whole Unicode control /
  format / bidi / zero-width / line+para-separator set (categories Cc [C0 + DEL + C1] / Cf [bidi,
  zero-width, BOM] / Zl / Zp) — the homoglyph/bidi/invisible-char injection class — while ALLOWING
  legitimate unicode letters/digits/punctuation/spaces (an identity may be a non-ASCII filename).
  Caps at `IDENTITY_MAX_LEN`.
- `TextStr` — human prose / model output / cited spans. Same strip + non-empty + cap, but ALLOWS
  inline `\t`/`\n`/`\r` (legitimately multi-line) AND legitimate multilingual unicode (INCLUDING
  format chars — content is rich text); rejects only NUL + the other C0 controls + DEL + C1
  (`\x80`-`\x9f`, incl NEL) for basic control hygiene. Larger cap (`TEXT_MAX_LEN`).

SCOPE: identities are security-sensitive references that never legitimately carry invisible/bidi/
control chars, so IdentityStr rejects the full Cc/Cf/Zl/Zp set (the reversible "freeze tight, widen
additively" direction — LESSON 14). The bidi/format CONTENT sanitization (Trojan-Source in
`chunk.text`, which is source code) is a Phase-2 ingest/redactor concern — flag/strip at ingest, NOT
a frozen-contract hard-reject that would refuse legitimate multilingual content (LESSON 14).

The `pattern` is applied AFTER `strip_whitespace` (StringConstraints order: strip → length →
pattern; pinned by `test_text_str_allows_inline_whitespace_rejects_nul`): a middle control char is
rejected; everything outside the permitted set is denied (the dangerous ranges/categories negated).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

# Bounded well above any real id/path/SHA/cited-span, below a DoS-sized payload. A future raise of a
# cap is a visible, deliberate change.
IDENTITY_MAX_LEN = 1024
TEXT_MAX_LEN = 8192

# Identity: reject Unicode control (Cc = C0 + DEL + C1) + format (Cf = bidi U+202A-E·U+2066-9,
# zero-width U+200B-D, BOM U+FEFF) + line-sep (Zl = U+2028) + para-sep (Zp = U+2029). Unicode
# letters/digits/punctuation/spaces still pass (a non-ASCII filename is a legitimate identity).
IdentityStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=IDENTITY_MAX_LEN,
        pattern=r"^[^\p{Cc}\p{Cf}\p{Zl}\p{Zp}]+$",
    ),
]

# Content: allow inline `\t`/`\n`/`\r` + multilingual unicode (incl format chars); reject NUL + the
# other C0 controls + DEL + C1 (`\x80`-`\x9f`, incl NEL `\x85`).
TextStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=TEXT_MAX_LEN,
        pattern=r"^[^\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f]+$",
    ),
]
