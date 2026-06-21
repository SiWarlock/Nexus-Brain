"""The HostPort — the sole mutation chokepoint (ARCHITECTURE.md §7, §4 #3, §14, Appendix A:218).

★ Freeze-before-fork SAFETY-CRITICAL port. KEY SAFETY RULE #4: no core module reaches an
fs/git/external/session mutation except via the active `HostPort.perform`. The core only *proposes*
a `HostIntent`; the host `authorize()`s it against the closed `HostCapability` allowlist
(fail-closed → `HostDenied`) and returns a `HostAction`; `perform()` runs only an authorized one.

`authorize(intent) -> HostAction` is the type-shaped chokepoint: you obtain a `HostAction` (the only
thing `perform` accepts) by going through `authorize`, so a forged mutation can't reach `perform`
through the normal path. Python can't enforce a private constructor, so the `authorized` stamp is
forgeable — `perform` therefore ALSO re-validates the capability against the allowlist (defense in
depth), and the §14 INV-allowlist architecture test (a static tripwire seeded now, matured in
Phase 2 when mutation-capable callers exist) proves no module mutates outside this chokepoint.

The real `StandaloneHost` (per-capability `perform` handlers doing the actual LanceDB write /
owned-doc refresh / host-config) is Phase-2. This slice freezes the Protocol + allowlist +
Intent/Action/Result + `HostDenied` + the `FakeHost`. The `HostCapability` set is pinned by a
membership snapshot; Intent/Action/Result by `spec(§7)` snapshots — drift is a cross-track Finding.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, StrictBool

from _types import TextStr


class HostCapability(StrEnum):
    """The CLOSED mutation allowlist (§7) — the only side-effects a StandaloneHost authorizes.

    A named, load-bearing domain enum (LESSON 6): pinned by a membership snapshot, so a value
    add/remove to the *mutation allowlist* is a loud test failure. Most-restrictive default —
    anything not in this set is denied. (NexusOpsHost is propose-only: it serializes intents to
    ActionPlans, Phase-2.)
    """

    OWN_STORE_WRITE = "own_store_write"
    OWNED_DOC_REFRESH = "owned_doc_refresh"
    CONSENTED_HOST_CONFIG = "consented_host_config"


class HostDenied(Exception):
    """Raised fail-closed when a capability is not in the host's allowlist (authorize + perform)."""


class HostIntent(BaseModel):
    """A PROPOSED mutation the core asks the host to authorize — frozen + closed.

    Carries the requested `capability` + a human-readable `summary`. Concrete per-capability
    payloads (what `own_store_write` writes) are Phase-2-deferred; this is the frozen seam shape.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: HostCapability
    summary: TextStr


class HostAction(BaseModel):
    """An AUTHORIZED mutation — the type `authorize()` produces and `perform()` executes — frozen.

    `authorized` is the fail-closed authorization stamp (default False): `authorize()` returns it
    True; a hand-built action defaults to False and is rejected by `perform`. The stamp is forgeable
    (no private constructor in Python), so `perform` ALSO re-checks the capability allowlist.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: HostCapability
    summary: TextStr
    authorized: StrictBool = False


class HostResult(BaseModel):
    """The outcome of `perform` — frozen. Minimal `{ok, detail?}`; richer per-capability results
    land in Phase-2 with the payloads."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ok: StrictBool
    detail: TextStr | None = None


@runtime_checkable
class HostPort(Protocol):
    """The mutation chokepoint port (§7). Real `StandaloneHost` (Phase-2) + `FakeHost` conform."""

    def capabilities(self) -> frozenset[HostCapability]:
        """The closed set of mutations this host authorizes."""
        ...

    def authorize(self, intent: HostIntent) -> HostAction:
        """Authorize a proposed intent → an authorized action; raise `HostDenied` fail-closed."""
        ...

    def perform(self, action: HostAction) -> HostResult:
        """Execute ONLY an authorized, allowlisted action; raise `HostDenied` otherwise."""
        ...
