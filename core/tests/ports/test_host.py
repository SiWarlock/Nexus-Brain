"""Unit tests for the HostPort safety chokepoint (ARCHITECTURE.md §7, §4 #3, §14, Appendix A:218).

★ Freeze-before-fork SAFETY-CRITICAL port (Key safety rule #4): the sole mutation chokepoint. The
core proposes a HostIntent; the host authorize()s it against the closed HostCapability allowlist
(fail-closed → HostDenied) and returns a HostAction; perform() executes ONLY an authorized action.
This pins the Protocol + the 3-value allowlist + Intent/Action/Result + HostDenied + the FakeHost.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ports.host import (
    HostAction,
    HostCapability,
    HostDenied,
    HostIntent,
    HostPort,
    HostResult,
)
from testing.fakes import FakeHost

pytestmark = pytest.mark.unit

WRITE = HostCapability.OWN_STORE_WRITE  # the most-used allowlisted capability, for terse fixtures


def _intent(cap: HostCapability = WRITE, summary: str = "write a chunk") -> HostIntent:
    """A valid proposed-mutation intent."""
    return HostIntent(capability=cap, summary=summary)


def test_host_capability_values() -> None:
    # LESSON 6: the closed mutation allowlist is a frozen contract — a value add/remove is loud.
    assert {c.value for c in HostCapability} == {
        "own_store_write",
        "owned_doc_refresh",
        "consented_host_config",
    }


def test_hostport_protocol_conformance() -> None:
    # LESSON 1: the Fake satisfies the port (runtime_checkable structural conformance).
    assert isinstance(FakeHost([WRITE]), HostPort)


def test_host_intent_schema_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — the proposed-mutation shape.
    assert set(HostIntent.model_fields) == {"capability", "summary"}


def test_host_action_schema_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — the authorized-mutation shape (carries the `authorized` stamp).
    assert set(HostAction.model_fields) == {"capability", "summary", "authorized"}


def test_host_result_schema_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — the perform-result shape.
    assert set(HostResult.model_fields) == {"ok", "detail"}


def test_intent_action_result_frozen_extra_forbid() -> None:
    # spec(§7): §4 parse-don't-trust — each rejects an unknown kwarg + post-construct mutation.
    intent = _intent()
    action = HostAction(capability=WRITE, summary="write a chunk", authorized=True)
    result = HostResult(ok=True)
    # unknown-kwarg rejection — dict[str, Any] unpack so the extra key isn't a static call-arg err.
    bad_intent: dict[str, Any] = {"capability": WRITE, "summary": "x", "forged": "nope"}
    bad_action: dict[str, Any] = {"capability": WRITE, "summary": "x", "authorized": True, "z": 1}
    bad_result: dict[str, Any] = {"ok": True, "forged": "nope"}
    with pytest.raises(ValidationError):
        HostIntent(**bad_intent)
    with pytest.raises(ValidationError):
        HostAction(**bad_action)
    with pytest.raises(ValidationError):
        HostResult(**bad_result)
    with pytest.raises(ValidationError):
        intent.summary = "mutated"
    with pytest.raises(ValidationError):
        action.authorized = False
    with pytest.raises(ValidationError):
        result.ok = False


def test_authorize_allows_allowlisted_capability() -> None:
    # spec(§7): authorize returns a HostAction for an allowlisted intent (happy path).
    host = FakeHost([WRITE])
    action = host.authorize(_intent())
    assert isinstance(action, HostAction)
    assert action.capability is WRITE
    assert action.authorized is True


def test_authorize_denies_unallowlisted_capability() -> None:
    # spec(§7): FAIL-CLOSED (Key safety rule #4 / §4 #3) — capability ∉ capabilities() → HostDenied.
    host = FakeHost([WRITE])  # only own_store_write allowed
    with pytest.raises(HostDenied):
        host.authorize(_intent(cap=HostCapability.CONSENTED_HOST_CONFIG))
    # an empty allowlist denies everything (most-restrictive default).
    with pytest.raises(HostDenied):
        FakeHost().authorize(_intent())


def test_perform_executes_authorized_action() -> None:
    # spec(§7): the authorize→perform happy path; the chokepoint is observable (recorded).
    host = FakeHost([WRITE])
    result = host.perform(host.authorize(_intent()))
    assert isinstance(result, HostResult)
    assert result.ok is True
    assert len(host.performed) == 1
    assert host.performed[0].capability is WRITE


def test_perform_rejects_unauthorized_action() -> None:
    # spec(§7): the chokepoint is not bypassable — a forged/hand-built action (NOT from authorize,
    # so authorized defaults False) is rejected by perform (fail-closed).
    host = FakeHost([WRITE])
    forged = HostAction(capability=WRITE, summary="sneak a write")  # authorized defaults False
    assert forged.authorized is False
    with pytest.raises(HostDenied):
        host.perform(forged)
    assert host.performed == []


def test_perform_denies_unallowlisted_capability_even_if_authorized() -> None:
    # spec(§7 / Key safety rule #4): defense-in-depth — perform re-validates capability ∈
    # capabilities() and raises HostDenied even if `authorized` is FORGED True, so the chokepoint
    # never executes a non-allowlisted capability. The authorized bool is forgeable (no private
    # ctor in Python); the recheck makes "perform only ever runs an allowlisted capability" a
    # perform-local invariant, not a trust in a forgeable flag.
    host = FakeHost([WRITE])  # only own_store_write allowed
    forged = HostAction(
        capability=HostCapability.CONSENTED_HOST_CONFIG, summary="forge", authorized=True
    )
    with pytest.raises(HostDenied):
        host.perform(forged)
    assert host.performed == []


def test_fakehost_fidelity() -> None:
    # LESSON 1: the Fake upholds the SAME fail-closed contract a real host must (no looser fake on a
    # safety seam) — configurable allowlist, deny outside, record performed.
    host = FakeHost([WRITE, HostCapability.OWNED_DOC_REFRESH])
    assert host.capabilities() == frozenset({WRITE, HostCapability.OWNED_DOC_REFRESH})
    host.perform(host.authorize(_intent(cap=HostCapability.OWNED_DOC_REFRESH, summary="refresh")))
    assert len(host.performed) == 1
    with pytest.raises(HostDenied):
        host.authorize(_intent(cap=HostCapability.CONSENTED_HOST_CONFIG))


def test_host_intent_strip_identity() -> None:
    # LESSON 7: Intent/Action string fields strip + reject empty/whitespace.
    for bad in ("", "   "):
        with pytest.raises(ValidationError):
            HostIntent(capability=WRITE, summary=bad)
        with pytest.raises(ValidationError):
            HostAction(capability=WRITE, summary=bad, authorized=True)
    assert HostIntent(capability=WRITE, summary="  write  ").summary == "write"


# ── INV-allowlist tripwire (architecture-invariant; §14 / §4 #3) ──────────────────────────────
# Lead safety ask (1.4a): scan every core/ module (excl. tests/, __pycache__, and dot-dirs like
# .venv/.mypy_cache) for FS/git mutation primitives and assert NONE appear outside the allowlisted
# host-adapter path. Passes now (nothing in core/ mutates); the first Phase-2 module that mutates
# outside the chokepoint trips it — Key-safety-rule-#4 enforcement on the record from Phase 1.
# AST-based (robust over regex). Catches: qualified os/shutil/subprocess mutators, bare Path-mutator
# methods, write-mode open() (bare AND attribute form), any subprocess import, and
# `from os/shutil import <mutator>`. NOT YET resolved (Phase-2 hardening, flagged at Step 9):
# module aliasing (`import os as _os`) + getattr/dynamic dispatch — non-idiomatic here.
_CORE_ROOT = Path(__file__).resolve().parents[2]
_ALLOWLISTED_FILE = (_CORE_ROOT / "ports" / "host.py").resolve()
_EXCLUDED_DIRS = {"tests", "__pycache__"}

# (module, attr) pairs for `os.remove(...)` / `shutil.rmtree(...)` / `subprocess.run(...)` forms.
_QUALIFIED_MUTATORS = {
    ("os", "remove"),
    ("os", "rename"),
    ("os", "replace"),
    ("os", "mkdir"),
    ("os", "rmdir"),
    ("os", "unlink"),
    ("os", "makedirs"),
    ("os", "removedirs"),
    ("shutil", "rmtree"),
    ("shutil", "move"),
    ("shutil", "copy"),
    ("shutil", "copy2"),
    ("shutil", "copyfile"),
    ("shutil", "copytree"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
}
# Path mutator methods (any receiver) — none are common str methods, so receiver-agnostic is safe.
_PATH_MUTATOR_METHODS = {"write_text", "write_bytes", "unlink", "mkdir", "rmdir", "touch", "rename"}
# bare os/shutil mutator names, for the `from os import remove` import form.
_BARE_MUTATOR_NAMES = {attr for mod, attr in _QUALIFIED_MUTATORS if mod in ("os", "shutil")}
_WRITE_MODE_CHARS = set("wax+")


def _open_write_mode(call: ast.Call, pos: int) -> str | None:
    """open()'s mode string if it is a literal write/append/exclusive mode, else None.

    `pos` is the positional index of `mode`: 1 for builtin `open(file, mode)`, 0 for the bound
    `Path.open(mode)` / file-object `.open(mode)` form. The `mode=` keyword overrides either.
    """
    mode_node: ast.expr | None = call.args[pos] if len(call.args) > pos else None
    for kw in call.keywords:
        if kw.arg == "mode":
            mode_node = kw.value
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        if set(mode_node.value) & _WRITE_MODE_CHARS:
            return mode_node.value
    return None


def _call_hits(node: ast.Call, label: str) -> list[str]:
    """FS-mutation hits for one Call node (qualified mutator / Path method / write-mode open)."""
    func = node.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name) and (func.value.id, func.attr) in _QUALIFIED_MUTATORS:
            return [f"{label}:{node.lineno} {func.value.id}.{func.attr}()"]
        if func.attr in _PATH_MUTATOR_METHODS:
            return [f"{label}:{node.lineno} .{func.attr}()"]
        if func.attr == "open" and _open_write_mode(node, 0) is not None:  # Path.open(mode) → arg 0
            return [f"{label}:{node.lineno} .open(write-mode)"]
    elif isinstance(func, ast.Name) and func.id == "open" and _open_write_mode(node, 1) is not None:
        return [f"{label}:{node.lineno} open(write-mode)"]
    return []


def _import_hits(node: ast.Import | ast.ImportFrom, label: str) -> list[str]:
    """Flag a subprocess import (any) or a `from os/shutil import <mutator>` form."""
    if isinstance(node, ast.Import):
        if any(a.name.split(".")[0] == "subprocess" for a in node.names):
            return [f"{label}:{node.lineno} import subprocess"]
        return []
    top = (node.module or "").split(".")[0]
    if top == "subprocess":
        return [f"{label}:{node.lineno} from subprocess import"]
    if top in ("os", "shutil"):
        names = [a.name for a in node.names if a.name in _BARE_MUTATOR_NAMES]
        if names:
            return [f"{label}:{node.lineno} from {top} import {','.join(names)}"]
    return []


def _scan_file_for_mutations(path: Path, label: str) -> list[str]:
    """AST-scan one module; return FS/git-mutation hit descriptions (empty list = clean)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            hits.extend(_import_hits(node, label))
        elif isinstance(node, ast.Call):
            hits.extend(_call_hits(node, label))
    return hits


def test_inv_allowlist_no_mutation_outside_hostport() -> None:
    # spec(§14 / §4 #3): the chokepoint tripwire — NO core/ module performs an FS/git mutation
    # outside the allowlisted host-adapter path (core/ports/host.py). Passes now (nothing mutates);
    # fails the first Phase-2 bypass — Key-safety-rule-#4 enforcement on the record from Phase 1.
    violations: list[str] = []
    for dirpath, dirnames, filenames in os.walk(_CORE_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS and not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = Path(dirpath) / fn
            if path.resolve() == _ALLOWLISTED_FILE:
                continue
            violations.extend(_scan_file_for_mutations(path, str(path.relative_to(_CORE_ROOT))))
    assert violations == [], f"FS/git mutation outside HostPort.perform: {violations}"


def test_host_authorized_strict() -> None:
    # §7 capability stamp (LESSON 9 defense-in-depth, 1.6c): authorized is StrictBool — a lax
    # authorized=1/"true" is rejected at parse, ON TOP of perform's capability re-validation.
    base = {"capability": "own_store_write", "summary": "write the store"}
    for lax in (1, 0, "yes", "true", "on", "false"):
        with pytest.raises(ValidationError):
            HostAction.model_validate({**base, "authorized": lax})
    assert HostAction.model_validate({**base, "authorized": True}).authorized is True
    # the stamp defaults fail-closed False (a hand-built action is not authorized)
    assert HostAction(capability=HostCapability.OWN_STORE_WRITE, summary="s").authorized is False


def test_host_result_ok_strict() -> None:
    # §7 (1.6c uniformity): HostResult.ok is StrictBool — a lax 1/"yes"/"true"/"on" can't coerce to
    # True; a real bool is accepted. The system-set perform() outcome flag, hardened uniformly.
    for lax in (1, 0, "yes", "true", "on", "false"):
        with pytest.raises(ValidationError):
            HostResult.model_validate({"ok": lax})
    assert HostResult.model_validate({"ok": True}).ok is True
    assert HostResult.model_validate({"ok": False}).ok is False
