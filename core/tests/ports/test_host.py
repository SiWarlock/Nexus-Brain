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
    StandaloneHost,
    StoreWritePayload,
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
    # spec(§7): §2.5-seam ★ freeze — the proposed-mutation shape. 2.S GROWS `payload` (Option C,
    # owner-locked) additively; absent → None so existing contentless intents still validate.
    assert set(HostIntent.model_fields) == {"capability", "summary", "payload"}
    assert HostIntent(capability=WRITE, summary="s").payload is None


def test_host_action_schema_snapshot() -> None:
    # spec(§7): §2.5-seam ★ freeze — the authorized-mutation shape (carries the `authorized` stamp +
    # the Option-C `payload`, which rides through from the authorized intent).
    assert set(HostAction.model_fields) == {"capability", "summary", "authorized", "payload"}


def test_store_write_payload_schema_snapshot() -> None:
    # spec(§7): the owner-locked Option-C payload shape — frozen + extra-forbid; content is `bytes`.
    assert set(StoreWritePayload.model_fields) == {"rel_path", "content"}
    payload = StoreWritePayload(rel_path=".project-brain/manifest.json", content=b"{}")
    with pytest.raises(ValidationError):  # frozen — no post-construct mutation
        payload.rel_path = "other"
    bad: dict[str, Any] = {"rel_path": "x", "content": b"y", "extra": 1}
    with pytest.raises(ValidationError):  # extra="forbid"
        StoreWritePayload(**bad)


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


# ── StandaloneHost — the real adapter (2.S; §7) ────────────────────────────────────────────────


def _payload(rel_path: str = "out.json", content: bytes = b"hello") -> StoreWritePayload:
    return StoreWritePayload(rel_path=rel_path, content=content)


class _RecordingStandaloneHost(StandaloneHost):
    """A StandaloneHost that records every action that reaches `perform` — the runtime-proof spy."""

    def __init__(self, root: Path, capabilities: Any = ()) -> None:
        super().__init__(root, capabilities)
        self.performed: list[HostAction] = []

    def perform(self, action: HostAction) -> HostResult:
        result = super().perform(action)
        self.performed.append(action)  # only on success — a denied/raised perform records nothing
        return result


def test_standalone_host_conforms_to_protocol(tmp_path: Path) -> None:
    # spec(§7): LESSON 1 fidelity on the safety seam — the REAL host satisfies the runtime_checkable
    # HostPort Protocol, exactly like the FakeHost.
    assert isinstance(StandaloneHost(tmp_path, [WRITE]), HostPort)


def test_standalone_host_authorize_fail_closed(tmp_path: Path) -> None:
    # spec(§4): Key-safety-#4 fail-closed ON THE REAL HOST — capability ∉ allowlist → HostDenied;
    # an EXPLICIT empty allowlist denies all (1.4a pinned this only on FakeHost).
    host = StandaloneHost(tmp_path, [WRITE])
    with pytest.raises(HostDenied):
        host.authorize(_intent(cap=HostCapability.CONSENTED_HOST_CONFIG))
    with pytest.raises(HostDenied):
        StandaloneHost(tmp_path, []).authorize(_intent())  # explicit empty allowlist denies all


def test_standalone_host_perform_capability_recheck(tmp_path: Path) -> None:
    # spec(§7): LESSON 9 defense-in-depth ON THE REAL HOST — a forged authorized=True for a
    # non-allowlisted capability is still denied at perform (1.4a residual: only FakeHost pinned).
    host = StandaloneHost(tmp_path, [WRITE])  # only own_store_write allowed
    forged = HostAction(
        capability=HostCapability.CONSENTED_HOST_CONFIG, summary="forge", authorized=True
    )
    with pytest.raises(HostDenied):
        host.perform(forged)
    # a hand-built (unauthorized) action is rejected too.
    with pytest.raises(HostDenied):
        host.perform(HostAction(capability=WRITE, summary="sneak", payload=_payload()))


def test_standalone_host_own_store_write_atomic(tmp_path: Path) -> None:
    # spec(§5): the OWN_STORE_WRITE handler writes content to <root>/rel_path atomically (temp +
    # os.replace) and returns HostResult(ok=True); a nested dir is created; no temp left behind.
    host = StandaloneHost(tmp_path, [WRITE])
    intent = HostIntent(capability=WRITE, summary="w", payload=_payload("a/b/c.json", b'{"k":1}'))
    result = host.perform(host.authorize(intent))
    assert isinstance(result, HostResult) and result.ok is True
    written = tmp_path / "a" / "b" / "c.json"
    assert written.read_bytes() == b'{"k":1}'
    assert list((tmp_path / "a" / "b").glob(".*tmp")) == []  # no leftover temp


def test_standalone_host_rejects_path_escape(tmp_path: Path) -> None:
    # spec(§14): LESSON 14 write-boundary containment on the realpath — absolute / ..-segment /
    # root-escaping rel_path → HostDenied; nothing is written.
    host = StandaloneHost(tmp_path, [WRITE])
    for bad in ("/etc/passwd", "../escape.json", "a/../../escape.json"):
        with pytest.raises(HostDenied):
            host.perform(
                host.authorize(HostIntent(capability=WRITE, summary="x", payload=_payload(bad)))
            )
    # a symlinked component pointing outside the root is caught on the resolved realpath.
    outside = tmp_path.parent / "outside_root"
    outside.mkdir(exist_ok=True)
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(HostDenied):
        host.perform(
            host.authorize(
                HostIntent(capability=WRITE, summary="x", payload=_payload("link/f.json"))
            )
        )
    assert not (outside / "f.json").exists()


def test_standalone_host_runtime_proof(tmp_path: Path) -> None:
    # spec(§14): the runtime upgrade of the 1.4a static tripwire — a recording host shows
    # the file landed AND that the only path to the write was perform (the action it captured).
    host = _RecordingStandaloneHost(tmp_path, [WRITE])
    payload = _payload("gen/manifest.json", b'{"v":1}')
    host.perform(host.authorize(HostIntent(capability=WRITE, summary="w", payload=payload)))
    assert (tmp_path / "gen" / "manifest.json").read_bytes() == b'{"v":1}'
    assert len(host.performed) == 1
    assert host.performed[0].capability is WRITE
    assert host.performed[0].payload == payload


def test_standalone_host_perform_unhandled_allowlisted_cap_fails_closed(tmp_path: Path) -> None:
    # spec(§7 / §4 #3): the Phase-2 StandaloneHost DEFAULT allowlist is {OWN_STORE_WRITE} only — it
    # offers only the cap it handles (authorize+perform stay consistent). Defense-in-depth for
    # the configurable path: a host given an EXTRA, unhandled capability authorizes it but `perform`
    # fails CLOSED (HostDenied "no handler") — never a silent ok=True, never an uncaught KeyError.
    assert StandaloneHost(tmp_path).capabilities() == frozenset({WRITE})  # production default
    host = StandaloneHost(tmp_path, [WRITE, HostCapability.OWNED_DOC_REFRESH])
    action = host.authorize(_intent(cap=HostCapability.OWNED_DOC_REFRESH, summary="refresh"))
    assert action.authorized is True  # authorize succeeds (it IS allowlisted)
    with pytest.raises(HostDenied):
        host.perform(action)  # but perform has no handler → fail closed (defense in depth)


# ── INV-allowlist tripwire (architecture-invariant; §14 / §4 #3) ──────────────────────────────
# Lead safety ask (1.4a, HARDENED at 2.S): scan every core/ module (excl. tests/, __pycache__, and
# dot-dirs like .venv/.mypy_cache) for FS/git/SESSION mutation primitives and assert NONE appear
# outside the allowlisted host-adapter path. The first mutation-capable module (2.4's add pipeline)
# now exists and routes through HostPort.perform — so the scan staying GREEN over it IS the runtime
# INV-allowlist proof. AST-based (robust over regex). Catches: qualified os/shutil/subprocess
# mutators, bare Path-mutator methods, write-mode open() (bare AND attribute form), any subprocess
# import, and `from os/shutil import <mutator>`. 2.S RESOLVES the residuals: (a) module aliasing
# (`import os as _os; _os.remove`), (b) getattr/dynamic dispatch (`getattr(os, "remove")`), and
# (c) SESSION-state writes (`os.environ[...]=`, `.update/.pop/...`, `os.putenv`/`os.unsetenv`).
_CORE_ROOT = Path(__file__).resolve().parents[2]
_ALLOWLISTED_FILE = (_CORE_ROOT / "ports" / "host.py").resolve()
_EXCLUDED_DIRS = {"tests", "__pycache__"}

# Modules whose mutators are watched — and whose import aliases we resolve (residual a).
_WATCHED_MODULES = {"os", "shutil", "subprocess"}

# (module, attr) pairs for `os.remove(...)` / `shutil.rmtree(...)` / `subprocess.run(...)` forms.
# `os.putenv`/`os.unsetenv` are SESSION-state mutators (residual c, Key-safety-#4 external/session).
_QUALIFIED_MUTATORS = {
    ("os", "remove"),
    ("os", "rename"),
    ("os", "replace"),
    ("os", "mkdir"),
    ("os", "rmdir"),
    ("os", "unlink"),
    ("os", "makedirs"),
    ("os", "removedirs"),
    ("os", "putenv"),
    ("os", "unsetenv"),
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
# `os.environ` mutating methods (residual c — session-state via the mapping API).
_ENVIRON_MUTATOR_METHODS = {"update", "pop", "popitem", "setdefault", "clear"}
# bare os/shutil mutator names, for the `from os import remove` import form.
_BARE_MUTATOR_NAMES = {attr for mod, attr in _QUALIFIED_MUTATORS if mod in ("os", "shutil")}
_WRITE_MODE_CHARS = set("wax+")


def _module_aliases(tree: ast.AST) -> dict[str, str]:
    """Map each local name bound to a watched module → its real module (`import os as _os`).

    Resolving aliases is residual (a): a mutator reached through `_os.remove` must scan the same as
    `os.remove`. Only an exact watched-module import is aliased (`import os.path as p` is NOT os).
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name in _WATCHED_MODULES:
                    aliases[a.asname or a.name] = a.name
    return aliases


def _resolve_module(name: str, aliases: dict[str, str]) -> str | None:
    """The watched module `name` refers to (via alias or directly), or None."""
    if name in aliases:
        return aliases[name]
    return name if name in _WATCHED_MODULES else None


def _environ_names(tree: ast.AST) -> frozenset[str]:
    """Local names bound to `os.environ` via `from os import environ [as X]` (residual c)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            for a in node.names:
                if a.name == "environ":
                    names.add(a.asname or "environ")
    return frozenset(names)


def _is_environ(expr: ast.expr, aliases: dict[str, str], environ_names: frozenset[str]) -> bool:
    """True for `os.environ` — the alias-resolved attribute OR a `from os import environ` name."""
    if isinstance(expr, ast.Name) and expr.id in environ_names:
        return True
    return (
        isinstance(expr, ast.Attribute)
        and expr.attr == "environ"
        and isinstance(expr.value, ast.Name)
        and _resolve_module(expr.value.id, aliases) == "os"
    )


def _is_environ_subscript(
    target: ast.expr, aliases: dict[str, str], environ_names: frozenset[str]
) -> bool:
    """True for an `os.environ[...]` subscript (the `=`/`del` session-state target)."""
    return isinstance(target, ast.Subscript) and _is_environ(target.value, aliases, environ_names)


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


def _getattr_hit(node: ast.Call, label: str, aliases: dict[str, str]) -> list[str]:
    """Residual (b): `getattr(<watched module>, "mutator")` / `getattr(os, <dynamic>)` dispatch.

    A constant attr is flagged only when it names a known mutator (so `getattr(os, "getpid")` is not
    a false positive); a NON-constant attr on a watched module can't be proven safe → flagged.
    """
    if not (isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2):
        return []
    arg0, arg1 = node.args[0], node.args[1]
    if not (isinstance(arg0, ast.Name) and (mod := _resolve_module(arg0.id, aliases)) is not None):
        return []
    if isinstance(arg1, ast.Constant) and isinstance(arg1.value, str):
        if (mod, arg1.value) in _QUALIFIED_MUTATORS or arg1.value in _PATH_MUTATOR_METHODS:
            return [f"{label}:{node.lineno} getattr({arg0.id}, {arg1.value!r})"]
        return []  # constant non-mutator attr — a read, not a mutation
    return [
        f"{label}:{node.lineno} getattr({arg0.id}, <dynamic>)"
    ]  # dynamic dispatch — can't prove


def _call_hits(
    node: ast.Call, label: str, aliases: dict[str, str], environ_names: frozenset[str]
) -> list[str]:
    """FS/session-mutation hits for one Call node (qualified mutator / getattr / environ method /
    Path method / write-mode open) — alias-resolved (residual a)."""
    hits = _getattr_hit(node, label, aliases)
    if hits:
        return hits
    func = node.func
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            mod = _resolve_module(func.value.id, aliases)
            if mod is not None and (mod, func.attr) in _QUALIFIED_MUTATORS:
                return [f"{label}:{node.lineno} {func.value.id}.{func.attr}()"]
        if func.attr in _ENVIRON_MUTATOR_METHODS and _is_environ(
            func.value, aliases, environ_names
        ):
            return [f"{label}:{node.lineno} os.environ.{func.attr}()"]  # residual c
        if func.attr in _PATH_MUTATOR_METHODS:
            return [f"{label}:{node.lineno} .{func.attr}()"]
        if func.attr == "open" and _open_write_mode(node, 0) is not None:  # Path.open(mode) → arg 0
            return [f"{label}:{node.lineno} .open(write-mode)"]
    elif isinstance(func, ast.Name) and func.id == "open" and _open_write_mode(node, 1) is not None:
        return [f"{label}:{node.lineno} open(write-mode)"]
    return []


def _session_state_hits(
    node: ast.stmt, label: str, aliases: dict[str, str], environ_names: frozenset[str]
) -> list[str]:
    """Residual (c): `os.environ[...] = ` / `del os.environ[...]` subscript session-state writes."""
    if isinstance(node, ast.Assign):
        targets: list[ast.expr] = list(node.targets)
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        targets = [node.target]
    elif isinstance(node, ast.Delete):
        targets = list(node.targets)
    else:
        return []
    return [
        f"{label}:{node.lineno} os.environ[...] {'del' if isinstance(node, ast.Delete) else '='}"
        for t in targets
        if _is_environ_subscript(t, aliases, environ_names)
    ]


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


def _scan_source(source: str, label: str) -> list[str]:
    """AST-scan one module's source; return FS/git/session-mutation hits (empty list = clean).

    Takes a source STRING (not a path) so the hardening tests can scan inline snippets. Resolves
    import aliases once, then walks: imports, calls (qualified/getattr/environ-method/Path/open),
    and assignment/delete statements (os.environ subscript writes).
    """
    tree = ast.parse(source, filename=label)
    aliases = _module_aliases(tree)
    environ_names = _environ_names(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            hits.extend(_import_hits(node, label))
        elif isinstance(node, ast.Call):
            hits.extend(_call_hits(node, label, aliases, environ_names))
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            hits.extend(_session_state_hits(node, label, aliases, environ_names))
    return hits


def _scan_file_for_mutations(path: Path, label: str) -> list[str]:
    """AST-scan one module file; return FS/git/session-mutation hit descriptions (empty = clean)."""
    return _scan_source(path.read_text(encoding="utf-8"), label)


def test_inv_allowlist_no_mutation_outside_hostport() -> None:
    # spec(§4): Key safety rule #4 — the single mutation chokepoint (`HostPort`, §4 #3).
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


def test_inv_allowlist_tripwire_catches_module_aliasing() -> None:
    # spec(§14): residual (a) — a mutator reached through an import alias is caught, not evaded.
    assert "remove" in "".join(_scan_source("import os as _o\n_o.remove('f')\n", "snip"))
    assert "rmtree" in "".join(_scan_source("import shutil as _sh\n_sh.rmtree('d')\n", "snip"))
    # a non-mutator call through an alias is NOT flagged (no false positive).
    assert _scan_source("import os as _o\n_o.getcwd()\n", "snip") == []


def test_inv_allowlist_tripwire_catches_getattr_dispatch() -> None:
    # spec(§14): residual (b) — getattr/dynamic-dispatch resolution of a mutator is caught.
    assert "getattr" in "".join(_scan_source("import os\ngetattr(os, 'remove')('f')\n", "snip"))
    assert "getattr" in "".join(_scan_source("import os as _o\ngetattr(_o, name)('f')\n", "snip"))
    # a constant non-mutator attr is NOT flagged (no false positive).
    assert _scan_source("import os\ngetattr(os, 'getpid')()\n", "snip") == []


def test_inv_allowlist_tripwire_scans_session_state() -> None:
    # spec(§14): Key-safety-#4 covers external/SESSION state — os.environ writes (via os.environ, an
    # import alias, AND a `from os import environ` bare name) + putenv/unsetenv.
    for snippet in (
        "import os\nos.environ['X'] = '1'\n",
        "import os\nos.environ.update({'X': '1'})\n",
        "import os\nos.environ.pop('X')\n",
        "import os as _o\ndel _o.environ['X']\n",
        "from os import environ\nenviron['X'] = '1'\n",
        "from os import environ as e\ne.update({'X': '1'})\n",
    ):
        assert _scan_source(snippet, "snip"), snippet
    assert "putenv" in "".join(_scan_source("import os\nos.putenv('X', '1')\n", "snip"))
    assert "unsetenv" in "".join(_scan_source("import os\nos.unsetenv('X')\n", "snip"))
    # a session-state READ is NOT flagged (no false positive), incl. the from-import form.
    assert _scan_source("import os\nv = os.environ.get('X')\n", "snip") == []
    assert _scan_source("from os import environ\nv = environ.get('X')\n", "snip") == []


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
