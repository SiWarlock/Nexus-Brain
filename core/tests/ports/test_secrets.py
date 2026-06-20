"""Unit tests for the SecretStore port (ARCHITECTURE.md §7, §18 Key safety rule #3).

★ Freeze-before-fork behavioral port. The cardinal pin: a `SecretRef` carries keychain COORDINATES
only — NO secret material (the ref flows through config/events/logs; the plaintext exists only
transiently as `resolve`'s return). Real macOS-Keychain adapter + log-scrub are Phase-2.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from ports.secrets import SecretNotFoundError, SecretRef, SecretStore
from testing.fakes import FakeSecretStore

pytestmark = pytest.mark.unit


def test_secretstore_conformance() -> None:
    # LESSON 1: the Fake structurally satisfies the port (runtime_checkable).
    assert isinstance(FakeSecretStore(), SecretStore)


def test_secretstore_get_ref_and_resolve() -> None:
    # §7: get_ref(name) → a SecretRef (coordinates); resolve(ref) → the stored test secret.
    store = FakeSecretStore(secrets={"api_key": "sk-123"})
    ref = store.get_ref("api_key")
    assert isinstance(ref, SecretRef)
    assert ref.account == "api_key"
    assert store.resolve(ref) == "sk-123"


def test_secret_ref_carries_no_secret() -> None:
    # ★ Key safety rule #3: SecretRef carries ONLY {service, account} — NO secret material; a
    # secret/value/password/token kwarg is rejected (extra="forbid").
    assert set(SecretRef.model_fields) == {"service", "account"}
    for leak in ("secret", "value", "password", "token"):
        bad: dict[str, Any] = {"service": "svc", "account": "acct", leak: "sk-LEAK"}
        with pytest.raises(ValidationError):
            SecretRef(**bad)


def test_fake_secretstore_no_leak() -> None:
    # §18: the plaintext is NOT exposed via SecretRef fields / repr / str / model_dump, nor via the
    # store's repr — only `resolve` returns it (the transient plaintext path).
    store = FakeSecretStore(secrets={"api_key": "sk-SUPERSECRET"})
    ref = store.get_ref("api_key")
    assert store.resolve(ref) == "sk-SUPERSECRET"
    assert "sk-SUPERSECRET" not in repr(ref)
    assert "sk-SUPERSECRET" not in str(ref)
    assert "sk-SUPERSECRET" not in str(ref.model_dump())
    assert "sk-SUPERSECRET" not in repr(store)


def test_resolve_missing_secret_raises() -> None:
    # §25 fail-closed-on-undefined + Key safety rule #3 spirit: resolve() for a ref with no stored
    # secret RAISES (keychain-not-found) — never silently returns ""/None (a subtle auth footgun).
    store = FakeSecretStore(secrets={"present": "sk-1"})
    missing = SecretRef(service="nexus-brain-test", account="absent")
    with pytest.raises(SecretNotFoundError, match="absent"):
        store.resolve(missing)


def test_secret_ref_snapshot_and_strip() -> None:
    # spec(§7): §2.5-seam ★ freeze — SecretRef frozen; LESSON 7 strip on service/account.
    ref = SecretRef(service="svc", account="acct")
    with pytest.raises(ValidationError):
        ref.service = "other"
    for badval in ("", "   "):
        with pytest.raises(ValidationError):
            SecretRef(service=badval, account="acct")
        with pytest.raises(ValidationError):
            SecretRef(service="svc", account=badval)
    assert SecretRef(service="  svc  ", account="acct").service == "svc"


def test_secret_ref_rejects_control_and_unicode_injection() -> None:
    # 1.6a: ports use the shared HARDENED IdentityStr (core/_types.py) — a representative identity
    # port field rejects ASCII control / NUL / DEL AND the unicode bidi / zero-width / BOM injection
    # set (the old strip+min_length-only alias admitted them all). \u escapes only (Trojan-Source).
    for bad in ("svc\x00x", "svc\x1fx", "svc\x7fx", "svc\u202ex", "svc\u200bx", "svc\ufeffx"):
        with pytest.raises(ValidationError):
            SecretRef(service=bad, account="acct")
        with pytest.raises(ValidationError):
            SecretRef(service="svc", account=bad)
