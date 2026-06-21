"""
Property generator for secret-shaped inputs and non-secret look-alikes.

Covers all catchable-set classes from ARCHITECTURE.md §18 / THREAT_MODEL.md §Redaction engine:
  - PREFIX_TOKEN: ghp_, github_pat_, sk-, xox*, AKIA, PEM headers, JWT
  - HIGH_ENTROPY_KV: KEY=value / export KEY=value with high-entropy values
  - JSON_SENSITIVE_VALUE: "password"/"token"/"secret"/"api_key": "<value>"
  - ENV_DUMP: multi-line shell env blobs

Also generates non-secret look-alikes for FP measurement.

SAFETY: All generated values are SYNTHETIC. No real credentials are produced.
NETWORK: Zero network egress.
"""

from __future__ import annotations

import base64
import hashlib
import random
import string
from typing import Iterator

from .types import NonSecretSample, SecretClass, SecretSample

# ---------------------------------------------------------------------------
# Entropy helpers (synthetic high-entropy strings, NOT real secrets)
# ---------------------------------------------------------------------------

_ALPHANUMERIC = string.ascii_letters + string.digits
_HEX = string.hexdigits[:16]  # 0-9a-f

# Deterministic RNG — seeded for reproducibility; NEVER use for crypto
_RNG = random.Random(0xDEADBEEF_CAFEFACE)


def _rand_alphanum(length: int, rng: random.Random | None = None) -> str:
    r = rng or _RNG
    return "".join(r.choice(_ALPHANUMERIC) for _ in range(length))


def _rand_hex(length: int, rng: random.Random | None = None) -> str:
    r = rng or _RNG
    return "".join(r.choice(_HEX) for _ in range(length))


def _rand_base64(byte_len: int, rng: random.Random | None = None) -> str:
    r = rng or _RNG
    raw = bytes(r.randint(0, 255) for _ in range(byte_len))
    return base64.b64encode(raw).decode()


def _rand_base64url(byte_len: int, rng: random.Random | None = None) -> str:
    r = rng or _RNG
    raw = bytes(r.randint(0, 255) for _ in range(byte_len))
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# ---------------------------------------------------------------------------
# §18 class: PREFIX_TOKEN
# Prefixes from THREAT_MODEL.md: ghp_, github_pat_, sk-, xox*, AKIA, PEM, JWT
# ---------------------------------------------------------------------------

def _github_pat_classic() -> Iterator[SecretSample]:
    """GitHub classic PAT: ghp_ + 36 alphanumeric chars."""
    for i in range(8):
        token = f"ghp_{''.join(_rand_alphanum(36))}"
        context = f"Authorization: token {token}"
        yield SecretSample(
            label=f"github-pat-classic-{i}",
            plaintext=token,
            secret_class=SecretClass.PREFIX_TOKEN,
            context=context,
        )


def _github_pat_fine_grained() -> Iterator[SecretSample]:
    """GitHub fine-grained PAT: github_pat_ + 82 chars."""
    for i in range(4):
        token = f"github_pat_{''.join(_rand_alphanum(82))}"
        context = f"git remote set-url origin https://{token}@github.com/org/repo.git"
        yield SecretSample(
            label=f"github-pat-fine-{i}",
            plaintext=token,
            secret_class=SecretClass.PREFIX_TOKEN,
            context=context,
        )


def _openai_api_key() -> Iterator[SecretSample]:
    """OpenAI / Anthropic-style sk- keys."""
    for i in range(6):
        key = f"sk-{''.join(_rand_alphanum(48))}"
        for ctx_label, ctx in [
            ("env", f"OPENAI_API_KEY={key}"),
            ("python", f'client = openai.OpenAI(api_key="{key}")'),
            ("dotenv", f"ANTHROPIC_API_KEY={key}"),
        ]:
            yield SecretSample(
                label=f"sk-key-{i}-{ctx_label}",
                plaintext=key,
                secret_class=SecretClass.PREFIX_TOKEN,
                context=ctx,
            )


def _slack_tokens() -> Iterator[SecretSample]:
    """Slack bot/user tokens: xoxb-/xoxp-/xoxa-."""
    prefixes = [("xoxb", "bot"), ("xoxp", "user"), ("xoxa", "app")]
    for prefix, kind in prefixes:
        token = f"{prefix}-{''.join(_rand_alphanum(11))}-{''.join(_rand_alphanum(12))}-{''.join(_rand_alphanum(24))}"
        yield SecretSample(
            label=f"slack-token-{kind}",
            plaintext=token,
            secret_class=SecretClass.PREFIX_TOKEN,
            context=f"SLACK_TOKEN={token}",
        )


def _aws_access_keys() -> Iterator[SecretSample]:
    """AWS AKIA access key IDs."""
    suffixes = [
        "FAKEAKEYID0001",
        "SYNTHKEYABCD12",
        "TESTFAKEKEY0099",
        "MOCKAWSKEYID99",
    ]
    for i, suffix in enumerate(suffixes):
        # AKIA + 16 uppercase alphanumeric = 20 chars total (canonical AWS format)
        key_id = f"AKIA{suffix[:16].upper()}"
        secret_part = _rand_alphanum(40)
        yield SecretSample(
            label=f"aws-access-key-{i}",
            plaintext=key_id,
            secret_class=SecretClass.PREFIX_TOKEN,
            context=f"aws_access_key_id = {key_id}\naws_secret_access_key = {secret_part}",
        )
        # Also emit the secret as a separate sample
        yield SecretSample(
            label=f"aws-secret-key-{i}",
            plaintext=secret_part,
            secret_class=SecretClass.HIGH_ENTROPY_KV,
            context=f"aws_secret_access_key = {secret_part}",
        )


def _pem_keys() -> Iterator[SecretSample]:
    """PEM private key headers."""
    pem_types = [
        ("RSA PRIVATE KEY", 64),
        ("EC PRIVATE KEY", 48),
        ("PRIVATE KEY", 56),
        ("OPENSSH PRIVATE KEY", 70),
    ]
    for key_type, body_len in pem_types:
        body = _rand_base64(body_len)
        pem = f"-----BEGIN {key_type}-----\n{body}\n-----END {key_type}-----"
        yield SecretSample(
            label=f"pem-{key_type.lower().replace(' ', '-')}",
            plaintext=pem,
            secret_class=SecretClass.PREFIX_TOKEN,
            context=f"# SSH key for deployment\n{pem}",
        )


def _jwt_tokens() -> Iterator[SecretSample]:
    """Synthetic JWT-shaped tokens (header.payload.signature)."""
    for i in range(4):
        header = _rand_base64url(20)
        payload = _rand_base64url(40)
        sig = _rand_base64url(32)
        jwt = f"{header}.{payload}.{sig}"
        yield SecretSample(
            label=f"jwt-{i}",
            plaintext=jwt,
            secret_class=SecretClass.PREFIX_TOKEN,
            context=f"Authorization: Bearer {jwt}",
        )


# ---------------------------------------------------------------------------
# §18 class: HIGH_ENTROPY_KV
# KEY=value or export KEY=value with high-entropy values
# ---------------------------------------------------------------------------

def _high_entropy_kv() -> Iterator[SecretSample]:
    """KEY=value pairs where value has high Shannon entropy (>3.5 bits/char)."""
    key_names = [
        "DATABASE_URL", "SECRET_KEY", "WEBHOOK_SECRET", "SIGNING_KEY",
        "ENCRYPTION_KEY", "MASTER_KEY", "SERVICE_ACCOUNT_KEY",
        "PRIVATE_KEY_DATA", "AUTH_TOKEN", "SESSION_SECRET",
    ]
    for i, key_name in enumerate(key_names):
        value = _rand_alphanum(32 + i * 2)
        for fmt in [f"{key_name}={value}", f"export {key_name}={value}", f"{key_name}=\"{value}\""]:
            yield SecretSample(
                label=f"high-entropy-kv-{key_name.lower()}-{fmt[:3]}",
                plaintext=value,
                secret_class=SecretClass.HIGH_ENTROPY_KV,
                context=fmt,
            )


def _base64_encoded_secrets() -> Iterator[SecretSample]:
    """Base64-encoded secrets in KEY=value context."""
    for i in range(6):
        raw_secret = _rand_alphanum(24 + i * 4)
        encoded = base64.b64encode(raw_secret.encode()).decode()
        key = f"B64_SECRET_{i}"
        context = f"{key}={encoded}"
        # The plaintext to detect is the encoded form (what appears in the file)
        yield SecretSample(
            label=f"base64-kv-{i}",
            plaintext=encoded,
            secret_class=SecretClass.HIGH_ENTROPY_KV,
            context=context,
        )


# ---------------------------------------------------------------------------
# §18 class: JSON_SENSITIVE_VALUE
# "password"/"token"/"secret"/"api_key": "<value>"
# ---------------------------------------------------------------------------

_JSON_SENSITIVE_KEYS = ["password", "token", "secret", "api_key", "access_key", "private_key", "auth_token"]


def _json_sensitive_values() -> Iterator[SecretSample]:
    """JSON fields with sensitive key names and high-entropy values (>= 20 chars)."""
    for i, key in enumerate(_JSON_SENSITIVE_KEYS):
        value = _rand_alphanum(24 + i)
        for fmt in [
            f'{{"{key}": "{value}"}}',
            f'  "{key}": "{value}",',
            f"'{key}': '{value}'",
        ]:
            yield SecretSample(
                label=f"json-{key}-{fmt[:3]}",
                plaintext=value,
                secret_class=SecretClass.JSON_SENSITIVE_VALUE,
                context=fmt,
            )


def _json_nested_secrets() -> Iterator[SecretSample]:
    """Secrets nested inside larger JSON blobs."""
    for i in range(4):
        token = _rand_alphanum(32)
        blob = (
            f'{{\n  "user": "alice",\n  "role": "admin",\n'
            f'  "token": "{token}",\n  "expires": 9999999\n}}'
        )
        yield SecretSample(
            label=f"json-nested-{i}",
            plaintext=token,
            secret_class=SecretClass.JSON_SENSITIVE_VALUE,
            context=blob,
        )


# ---------------------------------------------------------------------------
# §18 class: ENV_DUMP
# Multi-line env blobs
# ---------------------------------------------------------------------------

def _env_dumps() -> Iterator[SecretSample]:
    """Multi-line shell env dumps with embedded secrets."""
    for i in range(4):
        secret = _rand_alphanum(40)
        key_id = f"AKIAFAKEID{i:06d}XXXX"
        dump = (
            f"PATH=/usr/local/bin:/usr/bin:/bin\n"
            f"HOME=/home/user\n"
            f"LANG=en_US.UTF-8\n"
            f"SECRET_KEY={secret}\n"
            f"AWS_ACCESS_KEY_ID={key_id}\n"
            f"TERM=xterm-256color\n"
            f"SHELL=/bin/zsh\n"
        )
        yield SecretSample(
            label=f"env-dump-{i}",
            plaintext=secret,
            secret_class=SecretClass.ENV_DUMP,
            context=dump,
        )


# ---------------------------------------------------------------------------
# Non-secret look-alikes (for FP measurement)
# ---------------------------------------------------------------------------

def generate_non_secrets() -> list[NonSecretSample]:
    """
    Non-secret look-alikes for false-positive rate measurement.
    These should NOT be redacted by a well-calibrated engine.
    """
    samples: list[NonSecretSample] = []

    # Git SHAs — explicitly listed as accepted residuals in §18
    for sha in [
        "a" * 40,
        "deadbeef" + "0" * 32,
        _rand_hex(40),
        _rand_hex(64),  # SHA-256
    ]:
        samples.append(NonSecretSample(
            label=f"git-sha-{sha[:8]}",
            plaintext=sha,
            reason="Git SHA hex — §18 accepted residual; LanceDB version tagging requires passthrough",
        ))

    # UUIDs
    import uuid
    for _ in range(4):
        u = str(uuid.UUID(int=_RNG.getrandbits(128)))
        samples.append(NonSecretSample(
            label=f"uuid-{u[:8]}",
            plaintext=u,
            reason="UUID — structured random ID, not a secret",
        ))

    # Short common words in JSON (sub-20-char JSON accepted residual)
    for word in ["changeme", "admin", "test", "password123", "letmein"]:
        ctx = f'{{"password": "{word}"}}'
        samples.append(NonSecretSample(
            label=f"json-short-{word}",
            plaintext=word,
            reason=f"Sub-20-char JSON value '{word}' — §18 accepted residual (C-11 literal-zero undeliverable at short lengths)",
        ))

    # Normal English words with moderate entropy (could trip entropy filter)
    for phrase in [
        "correcthorsebatterystaple",
        "thequickbrownfoxjumpsoverthelazydog",
        "SuperSecureButNotASecret",
    ]:
        samples.append(NonSecretSample(
            label=f"entropy-phrase-{phrase[:12]}",
            plaintext=phrase,
            reason="English phrase with moderate Shannon entropy — should not be flagged without a key= prefix context",
        ))

    # Source code content that looks entropy-rich
    for snippet in [
        "0x4f3d9a8b7c2e1f06",   # hex literal in code
        "1a2b3c4d5e6f7a8b9c0d",  # looks like entropy but is a hex constant
        "aGVsbG8gd29ybGQ=",      # "hello world" in base64 — low entropy content
    ]:
        samples.append(NonSecretSample(
            label=f"code-literal-{snippet[:12]}",
            plaintext=snippet,
            reason="Hex/base64 code literal — not a secret, just a numeric constant or test value",
        ))

    # Long but structured non-secret strings
    url = "https://api.example.com/v1/data?filter=active&limit=100&offset=200"
    samples.append(NonSecretSample(
        label="url-with-query-params",
        plaintext=url,
        reason="URL with query params — looks complex but not a secret",
    ))

    return samples


# ---------------------------------------------------------------------------
# Master generator
# ---------------------------------------------------------------------------

def generate_secret_samples() -> list[SecretSample]:
    """
    Generate all synthetic secret samples for the catchable set.
    Returns a flat list covering all §18 SecretClass values.
    """
    generators = [
        _github_pat_classic(),
        _github_pat_fine_grained(),
        _openai_api_key(),
        _slack_tokens(),
        _aws_access_keys(),
        _pem_keys(),
        _jwt_tokens(),
        _high_entropy_kv(),
        _base64_encoded_secrets(),
        _json_sensitive_values(),
        _json_nested_secrets(),
        _env_dumps(),
    ]
    samples: list[SecretSample] = []
    for gen in generators:
        samples.extend(gen)
    return samples
