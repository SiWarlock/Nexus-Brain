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

The real `StandaloneHost` (Task 2.S) lands here: the `OWN_STORE_WRITE` `perform` handler does the
actual atomic FS write (temp-write + `os.replace` — the no-half-swap primitive), contained to the
project-brain root. Phase-1 froze the Protocol + allowlist + Intent/Action/Result + `HostDenied` +
the `FakeHost`; 2.S adds the optional per-capability `StoreWritePayload` (Option C, owner-locked —
`OWN_STORE_WRITE` only, widens additively into a per-capability union at 3.x), the real adapter, and
the runtime per-mutator INV-allowlist proof. The `HostCapability` set is pinned by a membership
snapshot; Intent/Action/Result/payload by `spec(§7)` snapshots — drift is a cross-track Finding.

★ This module is the SOLE allowlisted file for FS mutation primitives — the §14 INV-allowlist
tripwire (`test_host.py`) scans every OTHER `core/` module and fails on any mutator outside here.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, StrictBool

from _types import IdentityStr, TextStr


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


class StoreWritePayload(BaseModel):
    """The `OWN_STORE_WRITE` payload — WHAT to write (`content`) and WHERE (`rel_path`) — frozen.

    Owner-locked Option C: ONE optional payload on `HostIntent`/`HostAction`, covering
    `OWN_STORE_WRITE` only; it widens additively into a per-capability discriminated union when
    `owned_doc_refresh`/`consented_host_config` grow handlers (3.x). Keeping the payload on the
    action keeps the mutation self-describing (faithful to §7 + the §23 NexusOps `ActionPlan`
    serialization) WITHOUT weakening Key-safety-#4 (`perform` still re-validates the allowlist AND
    re-contains the path on the resolved realpath).

    `rel_path` is project-root-relative (`IdentityStr` — rejects control/bidi/zero-width injection,
    LESSON 16); `content` is raw `bytes` (a file IS bytes — no `TextStr` cap clips a large manifest,
    and the LanceDB-fragment write at 3.1 is binary, so no later str→bytes widen).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rel_path: IdentityStr
    content: bytes


class HostIntent(BaseModel):
    """A PROPOSED mutation the core asks the host to authorize — frozen + closed.

    Carries the requested `capability` + a human-readable `summary` + an OPTIONAL per-capability
    `payload` (Option C: `StoreWritePayload` for `OWN_STORE_WRITE`; absent → `None` so contentless
    intents still validate). The payload widens to a per-capability union additively at 3.x.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: HostCapability
    summary: TextStr
    payload: StoreWritePayload | None = None


class HostAction(BaseModel):
    """An AUTHORIZED mutation — the type `authorize()` produces and `perform()` executes — frozen.

    `authorized` is the fail-closed authorization stamp (default False): `authorize()` returns it
    True; a hand-built action defaults to False and is rejected by `perform`. The stamp is forgeable
    (no private constructor in Python), so `perform` ALSO re-checks the capability allowlist. The
    `payload` (Option C) rides through from the authorized intent; `perform` re-contains it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    capability: HostCapability
    summary: TextStr
    authorized: StrictBool = False
    payload: StoreWritePayload | None = None


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


class StandaloneHost:
    """The real standalone `HostPort` adapter — the SOLE FS-mutation executor (Key safety rule #4).

    Constructed with a project-brain `root` (the containment boundary every write is held inside)
    and a `HostCapability` allowlist that DEFAULTS to `{OWN_STORE_WRITE}` — the one capability this
    Phase-2 host handles, so `authorize` + `perform` stay consistent (it offers only what it
    can do). `authorize` is fail-closed (capability ∉ allowlist → `HostDenied`, an explicit empty
    allowlist denies all). `perform` is defense-in-depth: it re-validates the `authorized` stamp AND
    the capability allowlist (a forged `authorized=True` for a non-allowlisted capability is still
    denied — LESSON 9), then dispatches to a per-capability handler.

    Phase-2 implements ONLY the `OWN_STORE_WRITE` handler (the manifest write); the other two
    capabilities have no handler until 3.x — if a host is configured with one and an action reaches
    `perform`, it fails CLOSED (`HostDenied`) rather than silently no-op'ing a requested mutation.
    """

    def __init__(
        self,
        root: Path | str,
        capabilities: Iterable[HostCapability] = (HostCapability.OWN_STORE_WRITE,),
    ) -> None:
        # Resolve the root ONCE (realpath) — every write target is contained against this resolved
        # boundary, so a symlinked ancestor can't smuggle a write outside it.
        self._root = Path(root).resolve()
        self._capabilities = frozenset(capabilities)

    def capabilities(self) -> frozenset[HostCapability]:
        return self._capabilities

    def authorize(self, intent: HostIntent) -> HostAction:
        if intent.capability not in self._capabilities:
            raise HostDenied(f"capability {intent.capability.value!r} not in host allowlist")
        return HostAction(
            capability=intent.capability,
            summary=intent.summary,
            authorized=True,
            payload=intent.payload,
        )

    def perform(self, action: HostAction) -> HostResult:
        if not action.authorized:
            raise HostDenied("perform requires an action produced by authorize (forged rejected)")
        # defense in depth: never run a non-allowlisted capability even if `authorized` is forged.
        if action.capability not in self._capabilities:
            raise HostDenied(f"capability {action.capability.value!r} not in host allowlist")
        if action.capability is HostCapability.OWN_STORE_WRITE:
            return self._perform_own_store_write(action)
        # Allowlisted but no handler yet (3.x) — fail CLOSED, never a silent no-op on a mutation.
        raise HostDenied(f"no perform handler for {action.capability.value!r} (Phase 3+)")

    def _perform_own_store_write(self, action: HostAction) -> HostResult:
        payload = action.payload
        if payload is None:
            raise HostDenied("own_store_write requires a StoreWritePayload")
        target = self._resolve_within_root(payload.rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic no-half-swap: write to an UNPREDICTABLE temp in the target dir (mkstemp opens with
        # O_CREAT|O_EXCL, so it never follows a pre-planted symlink at the temp name), then replace
        # (atomic rename). On ANY failure the temp is removed — never a half-written target, never a
        # leaked temp. (Residual: a parent-dir symlink swap between resolve and write — a same-uid
        # TOCTOU — is NOT closed here; tracked as a §14 Finding for dir_fd/O_NOFOLLOW hardening.)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload.content)
            os.replace(tmp, target)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return HostResult(ok=True, detail=f"wrote {payload.rel_path}")

    def _resolve_within_root(self, rel_path: str) -> Path:
        """Resolve `rel_path` to an absolute target PROVEN inside the root, else `HostDenied`.

        Containment runs on the resolved realpath (LESSON 14): reject an absolute path or any `..`
        segment up front, then resolve (follow symlinks) and assert the result is under the root —
        so a symlinked path component pointing outside is caught, not just lexical `..`.
        """
        rel = Path(rel_path)
        if rel.is_absolute():
            raise HostDenied(f"write rel_path must be relative, not absolute: {rel_path!r}")
        if ".." in rel.parts:
            raise HostDenied(f"write rel_path must not contain a '..' segment: {rel_path!r}")
        resolved = (self._root / rel).resolve()
        try:
            resolved.relative_to(self._root)
        except ValueError:
            raise HostDenied(f"write target escapes the host root: {rel_path!r}") from None
        return resolved
