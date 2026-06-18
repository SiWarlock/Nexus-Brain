# LESSONS.md — Nexus Brain (the Python engine (core))

> Full prose for every lesson logged during work in `core/`. The compact index lives in `core/CLAUDE.md` "Lessons logged" table.
>
> **Lesson numbers are stable IDs.** New lessons get the next sequential number. Numbers may be referenced from code comments, commit messages, and cross-references between lessons. **Don't reorder; don't reuse a deleted number's slot.**
>
> **Lessons start at §1.** Each code area has its own lesson sequence — lessons don't carry across code areas.

---

## Lesson format

```markdown
## <a id="N"></a>N. <Short topic> — <one-line rule>

**Date:** YYYY-MM-DD.
**Source slice:** <slice-id or commit hash>.

<2-5 paragraphs explaining: what was discovered, why it matters, how to
apply the rule, what edge cases are still open. Cite file:line references
where applicable.>

**Rule:** <one-sentence summary, same as the heading subtitle>.
```

---

## <a id="1"></a>1. Ports are `Protocol` + real adapter + named `Fake*` double — inject, never construct inline

**Date:** 2026-06-17.
**Source slice:** 1.1 (`61853b3`).

The first contract slice set the ports-and-adapters shape every later port (1.2–1.5) and every downstream track mirrors. A port is a `typing.Protocol` (decorate `@runtime_checkable` only where an `isinstance` conformance test needs it; structural typing otherwise). Each port ships **two** implementations: a real adapter (`SystemClock`, `UuidGen`, `SystemSeed`) in `core/ports/<port>.py`, and a deterministic `Fake*` double (`FakeClock`, `FakeIdGen`, `FakeSeed`) in `core/testing/fakes.py` — the canonical test-double home (1.4 extends it with the provider/CodeGraph fakes + cassettes). Consumers receive the port **by constructor injection**; they never construct a concrete adapter or read the underlying resource inline (that last rule is mechanically enforced by forbidden-pattern rule 4).

The `Fake*` double must enforce the **same contract the real adapter upholds**, not a looser one — otherwise a test that injects the fake passes while the real path fails (a fidelity trap that, on a frozen freeze-before-fork seam, silently propagates to every track). 1.1 hardened `FakeClock` to reject a naive (non-UTC) start and a negative `advance()` precisely because the real `Clock` contract is tz-aware-UTC + non-decreasing. Conformance is pinned by the `*_real_and_fake_conform` tests (`core/tests/ports/test_clock.py`, `test_idgen.py`): real + fake both satisfy the port type.

**Rule:** Every port is a `Protocol` with a real adapter + a contract-faithful `Fake*` double in `core/testing/fakes.py`; inject by constructor, never construct or read the resource inline.

---

## <a id="2"></a>2. Minted ids are opaque — `kind` is an input hint, never recoverable from the id

**Date:** 2026-06-17.
**Source slice:** 1.1 (`61853b3`).

`IdGen.new_id(kind: str) -> str` takes a `kind` label, but the returned id is **opaque**: nothing downstream may parse `kind` (or any structure) back out of an id. The real `UuidGen` ignores `kind` entirely (uniqueness comes from `uuid4`); `FakeIdGen` uses `kind` only as an **internal** device to produce deterministic, per-kind-separated sequences — not as a parseable `kind-N` format. If a consumer or test relied on id structure it would pass against the fake and break against the real adapter (the same fidelity trap as lesson §1). Typed model fields (`Chunk.chunk_id` vs `Anchor.anchor_id`, and the forthcoming 1.3 IdKind enum) carry the kind explicitly; the id string does not.

**Rule:** Treat minted ids as opaque tokens; carry `kind` in typed fields, never recover it from the id.

---

## <a id="3"></a>3. Contract-model field names can shadow BaseModel/ABCMeta attributes — silently optional + un-serializable

**Date:** 2026-06-17.
**Source slice:** 1.2a (`269b68e`).

A frozen Pydantic field whose name collides with an inherited attribute/method of `BaseModel` (or its `ABCMeta` metaclass) is a silent, high-severity trap. In 1.2a the `Chunk.register` field (`'plain'|'deep'` dual-register) shadowed `ABCMeta.register`; Pydantic emitted a `UserWarning` AND adopted the bound method as the field's DEFAULT — so `model_fields['register'].is_required()` was `False`, omitting it constructed a method-valued instance, and `model_dump_json()` crashed (`Unable to serialize unknown type: method`). The 19-field snapshot + happy-path tests all passed because callers always supplied `register`. It is also one CI flag (`python -W error`) away from a broken import (the `UserWarning` becomes an error).

Mitigation — do this for EVERY contract model: (1) declare required fields explicitly with `Field(...)` (Ellipsis) — kills any accidental attribute/method default; (2) pin required-ness for ALL non-optional fields with an **omit-each-field test** (`for f in non_optional_fields: assert constructing without f raises ValidationError`) — the generic guard that catches a shadow regardless of which name collides; (3) scope-suppress the shadow `UserWarning` at class creation *inside the model module* (`warnings.catch_warnings()` + `filterwarnings`), NOT a pytest-only `filterwarnings` (which misses the `-W error` import break). Reserved/shadowing names to watch: `register`, `copy`, `dict`, `json`, `validate`, `schema`, `construct`, `model_*`.

**Rule:** Declare required contract fields with `Field(...)`, pin all required-ness with an omit-each-field test, and scope-suppress any BaseModel/ABCMeta name-shadow warning in the model module.

---

## <a id="4"></a>4. Serialized-file contract models pin BOTH a Python field-name snapshot AND a by-alias on-disk-key snapshot

**Date:** 2026-06-17.
**Source slice:** 1.2c1 (`07c3cba`).

A contract model that is also a serialized on-disk file (e.g. `.project-brain/manifest.json`) carries TWO contracts: the Python field-name set AND the on-disk JSON-key set. When the on-disk format uses camelCase (or any alias) for some keys, the two diverge — so the §2.5-seam snapshot must pin BOTH: `set(Model.model_fields)` (Python names) AND `set(m.model_dump(by_alias=True))` (on-disk keys). The manifest's `schemaVersion`/`ingestedFromSha` are camelCase on disk but snake in Python; its other 10 keys are already snake — so put `serialization_alias`/`validation_alias` on exactly the aliased fields, not a blanket generator. Use Pydantic 2.11 `ConfigDict(validate_by_name=True, validate_by_alias=True)` — NOT the DEPRECATED `populate_by_name`, which emits a DeprecationWarning that breaks `-W error`. The model is a LENIENT reader (accepts snake or camel keys, because `validate_by_name` is required for the writer) + a STRICT writer (`by_alias` emits the canonical on-disk keys); strict on-disk key-shape rejection (wrong/duplicate keys) is the LOADER's job (startup-reconcile / migrator), not the frozen model.

**Rule:** Serialized-file contract models pin two snapshots (Python field names + by-alias on-disk keys); use `validate_by_name`/`validate_by_alias` (not deprecated `populate_by_name`); the model is lenient-read / strict-write, with on-disk key-shape strictness owned by the loader.

---

## <a id="5"></a>5. Never suppress a quality-gate command's output — a short-circuited failure ships silently

**Date:** 2026-06-17.
**Source slice:** 1.2c2 re-gate (found E501s shipped in 1.2b `4fab4ab` + 1.2c1 `07c3cba`).

A hand-rolled Step-8 gate command `uv run ruff check . >/dev/null 2>&1 && echo "ruff OK"` HIDES failures twice over: `>/dev/null 2>&1` discards ruff's findings, and `&&` short-circuits so a non-zero exit prints nothing — a failing gate looks byte-identical to a passing one. Three E501 line-length violations shipped undetected across two committed slices this way (impact was lint-only — mypy + pytest were never suppressed — but the same pattern would silently ship a type or test failure). Root enabler: the implementer hand-rolled the gate because the canonical `/preflight` can't be run verbatim — its Step-4 `mypy core` line is the stale D-A3 entry that errors on the flat `core/` layout — so hand-assembled, error-prone gate commands filled the gap.

**Rule:** Run the canonical `/preflight` as Step 8 (visible output by construction); never hand-roll a gate with `>/dev/null` / `&& echo OK`. If a step must be run by hand, show its output or assert its exit code explicitly. _(enforcement: use `/preflight`; the suppressed-command pattern lives in session behavior, not committed code, so it is not grep-enforceable — the control is "use the canonical gate.")_

---

## <a id="6"></a>6. A named domain state-machine alphabet is a `StrEnum` + a membership-snapshot test; one-off inline tags stay `Literal`

**Date:** 2026-06-17.
**Source slice:** 1.3a (`5b50b5f`).

Two kinds of closed string set show up in these contracts, and they want different tools. A **one-off inline tag** — a closed set that exists only as a single field's value space, with no behavior hanging off it (e.g. `Chunk.doc_or_code` `'doc'|'code'`, `ownership`, `register`) — stays a `Literal[...]`: it is just a typed constraint, and `extra="forbid"` + the field type are the whole contract. A **named domain state machine** — an alphabet that is itself a load-bearing concept reused across transition logic, revalidation, and downstream tracks (e.g. `AnchorState` `{live,stale,moved,unknown,orphaned}`, and the forthcoming index-generation / episode-card / worker / project machines) — is a `StrEnum`: it has a name, it is iterable, it serializes to its string value (JSON-roundtrip stable), and its **value membership is a frozen contract in its own right**, so it gets its own membership-snapshot test (`{s.value for s in AnchorState} == {…}`) ALONGSIDE the model's field-name `spec(§)` snapshot. The membership snapshot is what catches an accidental add/remove/rename of a state value — drift the field-name snapshot can't see (the field is still `state`). It is also where a cross-doc reconciliation gets pinned: `test_anchor_state_values` actively asserts `deleted` is NOT a member, encoding the §5↔Appendix-A decision (`deleted` = anchor-record lifecycle, not a `state` value) as an executable check.

A corollary for a **deferred / externally-owned** enum (e.g. the NexusOps-seam `EvidenceType`/`IdKind`, whose canonical membership lives in `MAIN_PLATFORM_INTERFACE.md` v0.2 and is parked under D-A11): freeze the *structure* but do NOT write a membership-snapshot test — a value snapshot would lock a set we are explicitly deferring. Pin only the field-name shape; the membership snapshot lands when the canonical set is resolved at first-consumption (Phase-4 grounding), additively.

**Rule:** A named domain state-machine alphabet is a `StrEnum` with a value-membership snapshot test; one-off inline closed tags stay `Literal`; a deferred/externally-owned enum freezes shape only (no membership snapshot until the canonical set resolves).

---

## <a id="7"></a>7. Every §5/§10 identity/path string field is `StringConstraints(strip_whitespace=True, min_length=1)`

**Date:** 2026-06-17.
**Source slice:** 1.3a (`5b50b5f`).

`min_length=1` alone admits `"   "` (a whitespace-only string is length ≥ 1), so an identity or path field constrained only by `min_length=1` still accepts a semantically-empty value. On a frozen freeze-before-fork contract that every track consumes, a whitespace-loose identity (`project_id`, `anchor_id`, `source_file`, `target_path`, a SHA, a model id, a registry key) is a latent cross-track Finding: two ids that differ only by surrounding whitespace would route, dedup, or gate differently across tracks. The fix is uniform — declare every such field `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]`: it strips surrounding whitespace AND rejects the now-empty result, so `" abc "` normalizes to `"abc"` and `"   "`/`""` both raise. This was banked as a standing rule from the start of 1.3 (baked into `Anchor`) and is the **before-fork sweep** to retrofit across the 1.2 §5 identity fields (stamp / manifest / registry) before `/phase-exit 1`. The §5 models that shipped with bare `min_length=1` (1.2b/1.2c1/1.2c2) are the retrofit set.

**Rule:** Every §5/§10 identity or path string field uses `StringConstraints(strip_whitespace=True, min_length=1)`; pin it with per-model empty/whitespace-rejection tests; retrofit the bare-`min_length` §5 fields before the fork gate.

---

## <a id="8"></a>8. A frozen contract that composes a sibling frozen contract extends parse-don't-trust AND deep immutability to the nested element

**Date:** 2026-06-17.
**Source slice:** 1.3b (`77276e3`).

`ProvenancePacket.evidence: list[EvidenceRef]` is the first frozen contract in this codebase that **composes another frozen contract by value**. Three things follow that a flat model doesn't need, and all three are test-pinned:

1. **Parse-don't-trust reaches the nested element.** A `list[EvidenceRef]` validates each element against the full `EvidenceRef` contract — so a non-`EvidenceRef` (an `int`, or a `dict` missing a required field like `label`) must raise at the boundary, not slip in. Pin it (`test_provenance_evidence_typed`): the outer model's `extra="forbid"` does NOT cover the *inner* element's validity — that's the child model's own validation, and it only fires because the field is typed `list[EvidenceRef]` (not `list[dict]` / `list[Any]`).

2. **The dict→model coercion path is the real JSON/MCP boundary.** When the packet is rehydrated from JSON (`model_validate_json`) or an MCP payload, the nested evidence arrives as JSON objects (dicts) that Pydantic coerces into validated `EvidenceRef`s. Pin a valid-dict-coerces assertion AND the nested JSON round-trip (`model_dump_json` → `model_validate_json` equality) — this is the path production actually uses, and a silently-wrong coercion would corrupt the trust record.

3. **`frozen=True` is shallow — pin deep immutability explicitly.** `frozen=True` on the outer model blocks rebinding `packet.evidence`, but the *elements* are only immutable because `EvidenceRef` is itself `frozen=True`. Assert it at the composed level (`packet.evidence[0].label = "x"` raises) so a future change making the child mutable is caught by the parent's test, not discovered in production. (The list container itself is still replaceable-by-reassignment-blocked but not deep-frozen as a `list`; immutability rides on element-frozen + outer-frozen, which is sufficient for a value contract.)

**Container immutability — use `tuple`, not `list` (refinement, 1.4b `e9d1e51`).** `frozen=True` blocks *reassigning* the field (`m.evidence = […]` raises) but does NOT deep-freeze a `list` value — `m.evidence.append(x)` still mutates a "frozen" trust record in place. For true immutability, a composed collection field is **`tuple[Child, ...]`** (immutable container) rather than `list[Child]`. It is snapshot-stable (the field name is unchanged), wire-stable (JSON array both ways), and Pydantic coerces a list input to the tuple — so the migration is low-ripple. Standardize it across the frozen contracts (`ProvenancePacket`'s collections, `GenerateResult.citations`) in the before-fork hardening sweep; use `tuple` from the start in new contracts. The element-frozen pin (above) still matters — tuple immutability + element-frozen together give a deeply-immutable value.

**Rule:** When a frozen contract composes a sibling frozen contract, use `tuple[Child, ...]` (not `list`) for true container immutability, and test the nested element's parse-don't-trust rejection, the dict→model coercion (JSON/MCP boundary), and deep immutability — the outer `frozen`/`extra="forbid"` covers none of them.

---

## <a id="9"></a>9. A type-shaped chokepoint mints its input from the authorizer AND re-validates at execution — never trust a forgeable stamp alone

**Date:** 2026-06-17.
**Source slice:** 1.4a (`8aa6935`).

`HostPort` is the sole mutation chokepoint (Key safety rule #4): `authorize(intent) -> HostAction`, `perform(action) -> HostResult`. The design makes the chokepoint *type-shaped* — you normally obtain a `HostAction` only by calling `authorize`, which stamps `authorized=True` (the field defaults `False`, fail-closed). That gives a compile-time-ish shape: "you can't `perform` what you didn't `authorize`."

But Python has no private constructor — a caller CAN hand-build `HostAction(capability=…, authorized=True)`, forging the stamp. So the type-shape is necessary but **not sufficient**. The load-bearing addition is **defense-in-depth at `perform`**: `perform` re-validates `action.capability ∈ capabilities()` (and the `authorized` flag) *itself*, raising `HostDenied` — it does NOT trust the stamp alone. This makes "**`perform` never executes a non-allowlisted capability**" a perform-LOCAL invariant, independent of how the action was constructed, and it additionally fail-closes on capability *revocation* between authorize and perform. The forgeable-stamp gap that remains (forging an *allowlisted* capability) is the residual the architecture-level INV-allowlist test closes (no module bypasses `authorize` at all) — seeded in 1.4a as the static AST tripwire, matured to the full runtime proof in Phase-2 (Task 2.S / D-A13).

Generalize: for any gated seam (consent gates, redaction sinks, egress filters), don't rely on a boolean "I was checked" flag riding on the payload — the executor re-asserts the gate. A flag is a hint; the gate is the control.

**Rule:** A privileged-operation chokepoint obtains its input type only from its authorizer AND re-validates the allowlist/gate at execution time — a forgeable `authorized`/`checked` stamp is a hint, never the control; pair it with the architecture-invariant "nothing bypasses the authorizer" test.

---

## <a id="10"></a>10. An ingress/boundary validator is a positive allow-list, never an enumerated deny-list — especially when frozen

**Date:** 2026-06-17.
**Source slice:** 1.4c (`b1dafcc`).

`resolve_codegraph_dir` validates the `CODEGRAPH_DIR` env value before it is passed to the Phase-3 CLI shell-out. The first cut was a **deny-list**: reject `/`, `\`, `.`, `..`. The security review killed it — a deny-list enumerates the bad and passes everything else, so it let through CLI-flag injection (`-rf`, `--output=x`), a null byte, a bare Windows drive (`C:`), the unicode fullwidth solidus (U+FF0F), and `~`/`$HOME`/`*`/whitespace. The decisive point: **freezing a permissive deny-list into a frozen contract bakes the weak semantics in** — every later consumer inherits the holes, and §14 mandates allow-listing at the trust boundary.

The fix is a **positive charset allow-list**: `re.fullmatch(r"[A-Za-z0-9._-]+", value)` plus reject a leading `-` (option-injection) and the `.`/`..` path-traversal names. Everything not explicitly permitted is rejected — the boundary's default is *deny*. Pin it with a **bypass corpus** (the ~18 adversarial forms above) as a test, so a future relaxation that reintroduces a hole fails loudly. This is the §14 ingress posture generally (it recurs at the 1.5 MCP `get_file` path canonicalization + the query/k bounds): validate by what's allowed, not by what's forbidden; bound by Pydantic type + a positive semantic check.

Defense-in-depth for the eventual shell-out (Phase-3, on the record): even with the allow-list, pass the resolved value as a single non-option argv element (`--` separator / absolute-resolve) with `shell=False` — so a future allow-list relaxation still can't inject a flag or a command.

**Rule:** Validate an ingress/boundary value (path, dir-name, identifier) with a positive charset allow-list (`re.fullmatch`) + a bypass-corpus test, never an enumerated deny-list — the boundary defaults to deny; this is doubly load-bearing when the validator is frozen into a contract.

---

## <a id="11"></a>11. A safety contract excludes the dangerous field by shape AND `extra="forbid"` — mechanically, not by convention

**Date:** 2026-06-17.
**Source slice:** 1.4d (`05c3551`) — second instance (first: `StoreVersionStamp`, 1.2b).

When a frozen contract must NOT carry a piece of sensitive or source-of-truth-divergent data, two things make the exclusion *mechanical* rather than a documented hope: (1) the field is simply **absent** from the model, and (2) `extra="forbid"` **actively rejects** an attempt to add it. Together they turn "this contract never holds X" into a test-pinnable invariant — a stray `X=...` kwarg raises `ValidationError`, caught at the boundary.

This has now recurred twice on load-bearing contracts: `SecretRef{service, account}` has **no secret field** (Key safety rule #3 — the ref flows through config/events/logs; the plaintext exists only transiently as `resolve()`'s return), pinned by `test_secret_ref_carries_no_secret` (rejects `secret`/`value`/`password`/`token`) + a no-leak test (the secret is absent from `repr`/`str`/`model_dump(_json)`/the store `repr`). `StoreVersionStamp` has **no SHA field** (§5 source-of-truth — the git-SHA is the LanceDB version tag, the sole canonical home; a stamp SHA would be a divergent second home), pinned by `test_stamp_rejects_sha_field`.

The pattern generalizes to any "must-not-carry" invariant: a privacy field, a second source-of-truth, a capability that must come from elsewhere. Don't rely on "we just won't set it" — omit it AND `extra="forbid"` AND pin a reject/no-leak test, so the absence is enforced for every caller and every later edit.

**Rule:** For a contract that must not carry sensitive/divergent data, omit the field, set `extra="forbid"`, and pin a reject-the-kwarg (+ no-leak, if sensitive) test — mechanical exclusion, never a documented convention.
