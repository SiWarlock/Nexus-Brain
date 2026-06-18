"""The CodeGraphPort — the read-only structural-graph seam (ARCHITECTURE.md §7, Appendix A:220).

Behavioral port (LESSON 1) over the external CodeGraph (=1.0.1): `query(kind, sym)` over a closed
`CodeGraphQueryKind` set. This slice freezes the Protocol + the enum (+ `cli_command` mapping) + the
pure `CODEGRAPH_DIR` resolver + the schema-gate helper + `FakeCodeGraph`. The real CLI shell-out
adapter is Phase-3 (it needs a seeded fixture to verify populated-index output, spike Risk-4).

Bakes the Phase-0 spike-0.2 / D-A4 corrections to the stale plan values:
  - Risk-1: the schema gate asserts MAX(schema_versions.version) >= 5 (NOT = 1) — forward-safe.
  - Risk-2: the `search` kind maps to the 1.0.1 CLI verb `query` (no `codegraph search` exists).
  - Risk-3 (Phase-3 adapter): require codegraph >= 1.0.1 (the system binary is 0.9.7 and lacks
    `explore`/`node`) — fail-fast on `--version`, or route via the 1.0.1 MCP daemon.

Forbidden-rule 5 / D-27: this module hardcodes no path-with-slash literal for the index dir (it
resolves via the `CODEGRAPH_DIR` resolver) and references none of the deleted MCP graph tools.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, StringConstraints

# LESSON 7: symbol identity strings strip surrounding whitespace + reject empty / whitespace-only.
_StrippedStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# spike §1/§5: the default per-project index directory name (NO trailing slash — forbidden-rule 5
# bans a hardcoded path-with-slash literal; the resolver owns the name).
_DEFAULT_CODEGRAPH_DIR = ".codegraph"
# §14 ingress ALLOW-LIST: a CODEGRAPH_DIR override must fully match this safe single-segment charset
# (alnum + dot/underscore/hyphen). Anything else — separators, leading `-`, null bytes, unicode
# separators, `~`/`$`/globs, whitespace, absolute/drive paths — is rejected → the default.
_SAFE_DIR_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")
# spike-0.2 Risk-1: 1.0.1's CURRENT_SCHEMA_VERSION is 5 (the live store is already at 5).
_MIN_SCHEMA_VERSION = 5


class CodeGraphSchemaError(RuntimeError):
    """Raised when a CodeGraph store's schema version is below the required minimum (Risk-1)."""


class CodeGraphQueryKind(StrEnum):
    """The closed read-only query-kind set (§7 / Appendix A:220) — pinned by a snapshot."""

    EXPLORE = "explore"
    NODE = "node"
    CALLERS = "callers"
    CALLEES = "callees"
    SEARCH = "search"

    @property
    def cli_command(self) -> str:
        """The 1.0.1 CLI verb for this kind.

        spike-0.2 Risk-2: `search` maps to `query` (there is no `codegraph search` command); the
        other four kinds map to their own verb.
        """
        return "query" if self is CodeGraphQueryKind.SEARCH else self.value


class CodeGraphResult(BaseModel):
    """A read-only graph query result — frozen. Minimal shape: the query `kind` + the returned
    `symbols` (qualified names / node ids). Structured per-kind parsing is Phase-3-deferred (the
    populated-index output shape is unverified — spike Risk-4); `symbols` enriches additively.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: CodeGraphQueryKind
    symbols: tuple[_StrippedStr, ...]  # LESSON 8: a frozen-contract collection field is a tuple


def resolve_codegraph_dir(env_value: str | None) -> str:
    """Resolve the CodeGraph index directory NAME from a `CODEGRAPH_DIR` override (spike §5).

    Default `.codegraph`. A valid override is a single SAFE path segment (ALLOW-LIST, §14 ingress
    validation): it must fully match `[A-Za-z0-9._-]+`, must not be `.`/`..`, and must not start
    with `-` (a Phase-3 CLI argv would read a leading `-` as a flag). Everything else — separators,
    null bytes, unicode separators, `~`/`$`/globs, whitespace, absolute/drive paths — is rejected
    (falls back to the default), matching codegraph's own ignore-bad-value behavior. Surrounding
    whitespace is stripped. Freezing an allow-list (not a deny-list) keeps the seam tight.
    """
    if env_value is None:
        return _DEFAULT_CODEGRAPH_DIR
    value = env_value.strip()
    if (
        not value
        or value in (".", "..")
        or value.startswith("-")
        or _SAFE_DIR_SEGMENT.fullmatch(value) is None
    ):
        return _DEFAULT_CODEGRAPH_DIR
    return value


def assert_schema_compatible(max_schema_version: int) -> None:
    """Gate a CodeGraph store's schema version (spike-0.2 Risk-1).

    Asserts `MAX(schema_versions.version) >= 5` — forward-safe (6+ accepted). A store below 5 (the
    plan's stale `=1` expectation, or a pre-1.0.1 store) is incompatible and raises.
    """
    if max_schema_version < _MIN_SCHEMA_VERSION:
        raise CodeGraphSchemaError(
            f"CodeGraph schema_version {max_schema_version} < required {_MIN_SCHEMA_VERSION} "
            "(needs @colbymchenry/codegraph 1.0.1+)"
        )


@runtime_checkable
class CodeGraphPort(Protocol):
    """Read-only structural-graph seam over the external CodeGraph (=1.0.1), §7.

    The real Phase-3 adapter additionally: resolves `CODEGRAPH_DIR`, asserts `schema_versions >= 5`,
    version-gates (>= 1.0.1 fail-fast or MCP-route — spike Risk-3), and tree-sitter-falls-back when
    CodeGraph is down. This port freezes the query seam; `FakeCodeGraph` is the injected double.
    """

    def query(self, kind: CodeGraphQueryKind, sym: str) -> CodeGraphResult:
        """Query the graph by `kind` for symbol `sym` → a read-only `CodeGraphResult`."""
        ...
