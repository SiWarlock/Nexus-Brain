"""The catchable-set secret-redaction engine — the §18 redaction gate (Key safety rule #2).

`CatchableSetRedactor` implements the frozen `core.model.redactor_iface.Redactor` Protocol: it
removes the four catchable secret classes (prefix-token incl. JWT/PEM, high-entropy KV,
JSON-sensitive-value, env-dump) before a payload reaches any sink, and PASSES THROUGH the three §18
accepted residuals — git-SHA hex (ZERO-TOLERANCE: redacting one breaks LanceDB version tagging /
`last_resolved_sha`, the cardinal failure), the adversarial <20-char split, and sub-20-char JSON.

Defense-in-depth, NOT the primary control (keychain-refs-only is, §18). The envelope (recall ≥
floor, fp ≤ ceiling, git-SHA fp = 0%) is ENFORCED by the `ci/eval/redaction_fuzz/` CI gate — this
module references neither the constants nor `ci/` (core ⊥ ci/); the gate imports the engine, never
the reverse.

Pipeline (each pass replaces matches with a fixed `[REDACTED…]` marker that re-triggers nothing):
  1. PEM block · 2. prefix tokens (ghp_/github_pat_/sk-/xox*/AKIA/JWT) · 3. URL credential
  (`://user:PASS@`) · 4. assignment values (`KEY=value`/`KEY: value`/JSON) — the ALLOWLIST
  (git-SHA/UUID/ULID) runs BEFORE the entropy detector, never after (the cardinal §18 ordering).

Behavioral contract (frozen iface): idempotent · never-raises (fails CLOSED — never returns the
original on an internal error) · pure (stdlib `re`/`math`; no network/file I/O) · `str` per `Sink`.
v0 is UNIFORM across sinks (D-A5/D-A6 owner-deferred: the signature accommodates a later
cloud-stricter branch additively). CONTENT sanitization (Trojan-Source bidi, NUL/control) is a
separate concern (the 2.4 pipeline / a sibling), not this secret engine.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from model.redactor_iface import Sink

# --- markers (fixed, secret-free; all start "[REDACTED" so the assignment pass skips them) -------
_M_TOKEN = "[REDACTED_TOKEN]"
_M_PEM = "[REDACTED_PEM_KEY]"
_M_CREDENTIAL = "[REDACTED_CREDENTIAL]"
_M_SECRET = "[REDACTED_SECRET]"
_M_FAILCLOSED = "[REDACTED]"  # whole-payload fail-closed sentinel (never leak on internal error)

# --- detection thresholds ------------------------------------------------------------------------
_MIN_VALUE_LEN = 20  # the §18 detection floor (below this, sub-20 residuals + FP dominate)
_ENTROPY_MIN_BITS = 4.0  # Shannon bits/char; real random secrets ~4.7+, structured paths/words <4

# --- PEM block (pass 1): a whole private-key block, removed wholesale -----------------------------
_PEM_RE = re.compile(r"-----BEGIN [^\n-]+-----.*?-----END [^\n-]+-----", re.DOTALL)

# --- prefix tokens (pass 2): well-known credential shapes ----------------------------------------
# Every body is min-length anchored so a deliberately-split sub-20 fragment (`ghp_SYNTH`, bare
# `AKIA`/`sk-`) passes through as the §18 ACCEPTED RESIDUAL while the full credential is caught.
# AKIA uses a lower body floor (the `AKIA` prefix is itself diagnostic; real AWS key IDs run ~16-20
# chars total). `xox[baprs]` = the five Slack token sub-types (bot/app/user/refresh/socket). JWT =
# three dot-joined base64url segments (each >=16, bounded by non-base64url chars). sk-/xox/AKIA are
# word-boundary anchored so they cannot fire inside ordinary words (e.g. "task-force").
_PREFIX_RE = re.compile(
    r"github_pat_[A-Za-z0-9_]{12,}"
    r"|ghp_[A-Za-z0-9]{16,}"
    r"|\bsk-[A-Za-z0-9]{20,}"
    r"|\bxox[baprs]-[A-Za-z0-9-]{15,}"
    r"|\bAKIA[A-Z0-9]{12,}"
    # Segments bounded {16,512}: real JWT segments are short, and an UNbounded {16,} makes the
    # engine O(n^2)-backtrack on a long separator-less blob (a ReDoS/perf trap on 100KB inputs).
    r"|(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{16,512}\.[A-Za-z0-9_-]{16,512}\.[A-Za-z0-9_-]{16,512}(?![A-Za-z0-9_-])"
)

# --- URL credential (pass 3): the password in scheme://user:PASS@host ----------------------------
_URL_CRED_RE = re.compile(r"(://[^:/?#\s@]+:)(?P<pw>[^@/?#\s]+)(@)")

# --- assignment (pass 4): KEY=value / KEY: value / "key": "value" / 'key': 'value' ----------------
# The separator is `=` OR `:` NOT followed by `//` (so a `scheme://…` URL is never read as an
# assignment, but `token=…` *inside* a URL's query string still is). The whitespace around it is
# NON-newline (`[ \t]*`) so a YAML mapping header (`data:` then an indented block on the NEXT line)
# can't swallow the next line as its value. The raw value is the whole non-whitespace run (bounded
# {1,4096} for DoS); `_effective_value` trims it per quoting/sensitivity. Capturing the FULL run
# (not stopping at , / & / { / }) is what lets a sensitive value with an embedded delimiter
# (`API_KEY=ab,cd…`) be redacted whole instead of leaking the tail. Key bounded {0,80}: an UNbounded
# `*` greedily eats a long alnum blob then backtracks for the separator → O(n^2) on a 100KB input.
_ASSIGN_RE = re.compile(
    r"""["']?(?P<key>[A-Za-z_][\w.\-]{0,80})["']?[ \t]*(?:=|:(?!//))[ \t]*"""
    r"""(?P<oq>["']?)(?P<val>[^\s]{1,4096})"""
)

# Structural delimiters that end an UNQUOTED, non-sensitive value (so a `key=val&other=…` URL query
# or `{k: v, …}` flow map isn't over-consumed — the FP guard for the entropy branch).
_VALUE_DELIMITERS = re.compile(r"[,&{}]")

# A URL scheme prefix — a value that IS a URL passes through (any embedded credential was already
# handled by the URL-credential pass); avoids over-redacting public endpoints under keys like
# `token_url` / `auth_endpoint` (a false-positive class the all-alnum fuzz corpus can't surface).
_URL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://")

# Sensitive key fragments (key normalized lower + '-'→'_', substring match) → redact value >= floor
# regardless of entropy (a "password"/"token" value need not be high-entropy to be a secret). Kept
# tight (e.g. `auth_token`, not bare `auth`) so it doesn't fire on `oauth`/`author`/`authority`.
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
    "auth_token",
    "client_secret",
)

# The complete set of fixed markers — idempotence skips a value EQUAL to one of these (exact match,
# never a `startswith` prefix: ingested content can contain the literal text "[REDACTED…" and must
# not be able to suppress redaction of a real secret fused to that prefix).
_MARKERS = frozenset({_M_TOKEN, _M_PEM, _M_CREDENTIAL, _M_SECRET, _M_FAILCLOSED})

# Allowlist shapes — pass through UNREDACTED, checked BEFORE entropy (the cardinal §18 ordering).
_GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")
_HEX = "[0-9a-fA-F]"
_UUID_RE = re.compile(rf"^{_HEX}{{8}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{12}}$")
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")  # Crockford base32 (no I/L/O/U)


def _shannon_bits(s: str) -> float:
    """Shannon entropy of `s` in bits/char (0.0 for empty)."""
    if not s:
        return 0.0
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in Counter(s).values())


def _is_allowlisted(value: str) -> bool:
    """True for a git-SHA / UUID / ULID shape — never redacted (the §18 accepted residuals)."""
    return bool(_GIT_SHA_RE.match(value) or _UUID_RE.match(value) or _ULID_RE.match(value))


class CatchableSetRedactor:
    """The §18 catchable-set engine (Key safety rule #2). Implements the frozen `Redactor` Protocol.

    Stateless + pure; safe to share one instance. `redact` is the only public surface; the `_pass_*`
    methods are the ordered pipeline stages (kept as methods so the never-raises fail-closed
    boundary is observable + testable).
    """

    def redact(self, payload: str, sink: Sink) -> str:
        """Return `payload` with catchable-set secrets removed for delivery to `sink`.

        `sink` is accepted for the frozen signature; v0 applies uniform strictness across all three
        sinks (D-A5/D-A6 owner-deferred). On ANY internal error this fails CLOSED — it returns a
        secret-free marker, NEVER the original payload (a redactor must never leak on its own bug).
        """
        del sink  # uniform v0 — no per-sink branch yet (the param reserves the cloud-stricter seam)
        try:
            text = self._pass_pem(payload)
            text = self._pass_prefix(text)
            text = self._pass_url_credential(text)
            text = self._pass_assignment(text)
            return text
        except Exception:
            return _M_FAILCLOSED  # fail CLOSED — never return the (maybe secret-bearing) original

    def _pass_pem(self, payload: str) -> str:
        return _PEM_RE.sub(_M_PEM, payload)

    def _pass_prefix(self, payload: str) -> str:
        return _PREFIX_RE.sub(_M_TOKEN, payload)

    def _pass_url_credential(self, payload: str) -> str:
        return _URL_CRED_RE.sub(rf"\1{_M_CREDENTIAL}\3", payload)

    def _pass_assignment(self, payload: str) -> str:
        return _ASSIGN_RE.sub(self._redact_assignment, payload)

    @staticmethod
    def _redact_assignment(m: re.Match[str]) -> str:
        key, raw, quoted = m.group("key"), m.group("val"), bool(m.group("oq"))
        normalized_key = key.lower().replace("-", "_")
        sensitive = any(frag in normalized_key for frag in _SENSITIVE_KEY_FRAGMENTS)
        value = _effective_value(raw, quoted=quoted, sensitive=sensitive)
        if _keep_assignment_value(value, sensitive=sensitive):
            return m.group(0)
        # Replace only the effective value span; key, separator, and opening quote are preserved
        # (anything after `value` — a closing quote, a `,`/`&`/`}` and the next field — is kept).
        cut = m.start("val") - m.start(0)
        return m.group(0)[:cut] + _M_SECRET + m.group(0)[cut + len(value) :]


def _effective_value(raw: str, *, quoted: bool, sensitive: bool) -> str:
    """The portion of the matched run that IS the value to weigh for redaction.

    Quoted → up to the closing quote. Unquoted + sensitive key → the whole run (an embedded
    delimiter is part of the credential, so it is redacted whole — no leaking tail). Unquoted +
    non-sensitive → only up to the first structural delimiter (`, & { }`), so a `k=v&k2=v2` URL
    query / flow map isn't over-consumed (the entropy-branch FP guard).
    """
    if quoted:
        end = raw.find('"')
        end_sq = raw.find("'")
        candidates = [e for e in (end, end_sq) if e >= 0]
        return raw[: min(candidates)] if candidates else raw
    if sensitive:
        return raw
    return _VALUE_DELIMITERS.split(raw, 1)[0]


def _keep_assignment_value(value: str, *, sensitive: bool) -> bool:
    """True if an assignment value should pass through UNREDACTED."""
    if value in _MARKERS:
        return True  # already a marker — idempotence (EXACT match, never a startswith prefix)
    if _URL_SCHEME_RE.match(value):
        return True  # a URL value — embedded creds already handled by the URL-credential pass
    if _is_allowlisted(value):
        return True  # git-SHA / UUID / ULID — BEFORE entropy (cardinal §18 ordering)
    if len(value) < _MIN_VALUE_LEN:
        return True  # below the detection floor (sub-20 residual / FP zone)
    if sensitive:
        return False  # sensitive key + value >= floor → redact (entropy-independent)
    return _shannon_bits(value) < _ENTROPY_MIN_BITS  # else redact only if high-entropy
