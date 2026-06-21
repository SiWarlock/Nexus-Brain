"""
REFERENCE STUB REDACTOR — harness validation only.

⚠️  THIS IS NOT THE REAL REDACTION ENGINE. ⚠️
It is a minimal stub used ONLY to validate that the harness infrastructure
(generator, corpus, oracle, measurement loop) works end-to-end.

The real engine lands in Phase-2.3 (core/redactor/).
Do not use this stub in production. Do not benchmark against it.

Approach:
  - Detects well-known prefix-tokened secrets via simple prefix scan.
  - Detects JSON-sensitive key patterns with a crude regex.
  - Does NOT implement entropy scoring — high-entropy KV will largely be missed.
  - Does NOT handle base64-encoded secrets.
  - Intentionally conservative (some FP, not all classes covered).

Expected recall against the full corpus: ~45–60% (prefix class only).
Expected FP rate: ~5–15% (over-aggressive on some hash/UUID look-alikes).

These numbers prove the harness is calibrated — the stub is the baseline
that the real Phase-2.3 engine must BEAT.

NETWORK: Zero network egress.
SAFETY: Synthetic secrets only.
"""

from __future__ import annotations

import re

from .types import Sink

# Well-known token prefixes from THREAT_MODEL.md
_TOKEN_PREFIXES: list[str] = [
    "ghp_",
    "github_pat_",
    "sk-",
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "AKIA",
    "-----BEGIN ",
]

# JSON sensitive key names
_JSON_KEY_PATTERN: re.Pattern[str] = re.compile(
    r'"(?:password|token|secret|api_key|access_key|private_key|auth_token)"\s*:\s*"([^"]{20,})"',
    re.IGNORECASE,
)

# KEY=value pattern (env-style)
_KV_PATTERN: re.Pattern[str] = re.compile(
    r"(?:^|\n)(?:export\s+)?[A-Z_]{3,}(?:SECRET|KEY|TOKEN|PASSWORD|AUTH)[A-Z_]*\s*=\s*[\"']?([A-Za-z0-9+/=_\-]{20,})[\"']?",
    re.MULTILINE,
)

_REDACTED = "[REDACTED]"


def _redact_prefix_tokens(text: str) -> str:
    """Replace known-prefix tokens with [REDACTED]."""
    for prefix in _TOKEN_PREFIXES:
        if prefix not in text:
            continue
        idx = 0
        while True:
            pos = text.find(prefix, idx)
            if pos == -1:
                break
            # Find end of token: whitespace, quote, comma, or end of line
            end = pos + len(prefix)
            while end < len(text) and text[end] not in (' ', '\t', '\n', '"', "'", ',', ';', ')'):
                end += 1
            # Only redact if token body is >= 4 chars after the prefix
            body_len = end - pos - len(prefix)
            if body_len >= 4:
                text = text[:pos] + _REDACTED + text[end:]
                idx = pos + len(_REDACTED)
            else:
                idx = end
    return text


def _redact_pem_blocks(text: str) -> str:
    """Replace PEM key blocks."""
    pem_pattern = re.compile(
        r"-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----",
        re.MULTILINE,
    )
    return pem_pattern.sub(_REDACTED, text)


def _redact_json_sensitive(text: str) -> str:
    """Replace values of JSON keys with sensitive names (>= 20 chars)."""
    def replace_match(m: re.Match[str]) -> str:
        full = m.group(0)
        value = m.group(1)
        return full.replace(value, _REDACTED)
    return _JSON_KEY_PATTERN.sub(replace_match, text)


def _redact_kv_sensitive(text: str) -> str:
    """Replace values in KEY=value pairs where KEY contains a secret indicator."""
    def replace_match(m: re.Match[str]) -> str:
        full = m.group(0)
        value = m.group(1)
        return full.replace(value, _REDACTED, 1)
    return _KV_PATTERN.sub(replace_match, text)


def stub_redact(payload: str, sink: Sink) -> str:
    """
    Stub redact function. Validates the harness; NOT the real engine.

    All sinks receive the same treatment in this stub (the real engine
    may apply sink-specific policies — e.g. more aggressive on cloud_egress).
    """
    text = payload
    text = _redact_pem_blocks(text)
    text = _redact_prefix_tokens(text)
    text = _redact_json_sensitive(text)
    text = _redact_kv_sensitive(text)
    return text
