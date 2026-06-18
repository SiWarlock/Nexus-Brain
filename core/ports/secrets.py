"""The SecretStore port — keychain-backed secret access (ARCHITECTURE.md §7, §18).

★ Key safety rule #3: secrets live ONLY in the OS keychain; a `SecretRef` carries keychain
COORDINATES (`{service, account}`) and NEVER any secret material — the ref is what flows through
config / events / logs, while the plaintext exists only transiently as `resolve`'s return (the
caller must never persist or log it). `resolve` of an unknown ref fails CLOSED
(`SecretNotFoundError`, §25) — never a silent empty string. The real macOS-Keychain adapter + the
no-plaintext-in-logs enforcement are Phase-2; this slice freezes the interface + `SecretRef`.
"""

from __future__ import annotations

from typing import Annotated, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, StringConstraints

# LESSON 7: identity strings strip surrounding whitespace + reject empty / whitespace-only.
_StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SecretNotFoundError(KeyError):
    """Raised by `resolve` when no secret exists for the ref (fail-closed, §25 — never empty)."""


class SecretRef(BaseModel):
    """A keychain coordinate — frozen. Carries ONLY `{service, account}`; `extra="forbid"` rejects
    any secret/value/password/token field (Key safety rule #3 — the ref never holds plaintext).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    service: _StrippedStr
    account: _StrippedStr


@runtime_checkable
class SecretStore(Protocol):
    """Keychain-backed secret access (§7/§18). `FakeSecretStore` is the test double."""

    def get_ref(self, name: str) -> SecretRef:
        """Return the keychain coordinate for `name` (a ref, NOT the secret)."""
        ...

    def resolve(self, ref: SecretRef) -> str:
        """Return the transient plaintext for `ref` — the ONLY plaintext path (never persist/log);
        fails closed with `SecretNotFoundError` if the ref has no secret."""
        ...
