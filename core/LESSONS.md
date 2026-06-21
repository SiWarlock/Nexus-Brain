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

---

## <a id="12"></a>12. Freeze the boundary INTERFACE, not the engine's quality envelope — don't bake a recall/quality claim into the iface or its `Fake*`

**Date:** 2026-06-18.
**Source slice:** 1.5a (`redactor_interface_freeze`).

Phase 1 freezes a `Redactor` whose *engine* doesn't land until Phase 2.3. The temptation is to encode the engine's acceptance target — the catchable-set recall floor (≥95%) + FP ceiling (≤5%) — into the Phase-1 artifact. Resist it. The interface freezes three things and only three: the **signature** (`redact(payload: str, sink: Sink) -> str`), the **closed alphabet** (`Sink` StrEnum `{persist, mcp_egress, cloud_egress}`, membership-snapshot pinned — the §2.5-seam `spec(§18)` pin), and the **behavioral invariants that hold regardless of detection quality** (idempotent so the redaction marker doesn't re-redact, never-raises so a boundary callable can't DoS ingest/egress, git-SHA passthrough as a zero-tolerance sub-invariant since redacting a SHA breaks the LanceDB version tag + `last_resolved_sha`/§18·D-14, pure/in-memory). The **recall/FP envelope is documented** (the docstring names the single-source-of-truth constants in `ci/eval/redaction_fuzz/harness.py`) but **enforced where the engine lands** — the Phase-2.3 CI fuzz gate, not a Phase-1 assert.

Two corollaries. (1) **The interface references its envelope's single source, it doesn't import it** — `core/` must not depend on `ci/` (import-direction law; `ci/` is outside core's import root anyway, so an accidental import fails at collection/mypy). A docstring reference keeps the number discoverable without coupling the layers. (2) **The `Fake*` double must make NO quality claim.** A `FakeRedactor` is a contract-faithful test double — it honors the behavioral invariants (so downstream tests that inject it exercise the real contract) and is observably non-identity (it strips a couple of obvious prefix tokens so a "was the redactor applied?" test has signal), but it explicitly does **not** meet the recall envelope and its docstring says so. A Fake that silently claimed engine-grade redaction would let a test pass while the real catchable-set engine is still unbuilt — the fidelity trap of LESSON 1, applied to a quality envelope instead of a behavioral contract.

This generalizes to every boundary/safety interface frozen ahead of its engine (the 1.5 MCP contract's ingress validation vs. the Phase-8 boundary; any port whose adapter is eval-tested): freeze the shape + the invariants that are true by construction; defer the quality bar to the layer that can actually measure it; never let the interface or its double over-promise.

**Rule:** A safety/boundary interface freezes signature + closed alphabet + by-construction behavioral invariants now; the engine and its recall/quality envelope are enforced where the engine lands — reference the envelope's single-source constants, never import or assert them in the interface, and never bake a quality claim into the `Fake*` double.

---

## <a id="13"></a>13. Fail-CLOSED config: restrictive defaults + parse-don't-trust at the frozen schema; the fail-SOFT fallback is the loader's

**Date:** 2026-06-18.
**Source slice:** 1.5b (`policy_yaml_schema`).

A privacy/safety config (`policy.yaml`, §16) must **fail closed**: absent, empty, or unreadable input must land the system in its *most-restrictive* posture, never an open one. The freeze split this across two layers, and the split is the lesson. The **frozen schema** (`ProjectPolicy`) owns two of the three fail-closed obligations: (1) every field **defaults to most-restrictive** — `privacy=local`, every opt-in bool (`mcp.expose`/`federation.visible`/`sessions.consent`) `False`, `brainignore=()`, provider ids `None` — so a `{}` policy parses straight to lockdown; and (2) **parse-don't-trust reject** (§4) — an unrecognized/empty/wrong-case `privacy`, or any unknown key (`extra="forbid"` at all five model levels), raises `ValidationError` rather than silently coercing toward open. The third obligation — **fail-SOFT recovery**, i.e. "a *malformed* policy file is treated as most-restrictive instead of crashing the process" — is deliberately **NOT** the schema's job; it belongs to the Phase-2/3 **loader** (the startup-reconcile path), which catches the `ValidationError` and substitutes the lockdown default. A frozen schema that swallowed bad input and returned defaults would *hide* corruption (a user's intended `cloud` silently becoming `local`, or a typo'd opt-in silently dropped) — the schema must be a strict parser; leniency lives one layer up, in the loader, where it is a deliberate recovery, not an accident.

The test consequence: pin BOTH directions. Fail-closed defaults are pinned by constructing `ProjectPolicy()` *and* `model_validate({})` (the empty-dict path is what the loader actually hits). But defaults alone are a trap — a buggy schema that *ignored all input and always returned defaults* passes every fail-closed + snapshot test. So also pin a **positive value-preservation test**: a non-default policy (`privacy=cloud`, opt-ins `True`, a `brainignore` entry, a provider id) round-trips through `model_dump`/`model_validate` (and the JSON serializer path) with every value intact. The OFF-state pin and the ON-state pin together prove the schema both locks down by default *and* honors explicit choices — neither alone is sufficient.

**Rule:** A fail-CLOSED config freezes most-restrictive defaults + parse-don't-trust reject (`extra="forbid"`, no silent coercion) at the schema; the fail-SOFT "malformed → most-restrictive" recovery is the loader's, not the schema's. Pin both the default-lockdown (`{}` parse) AND a positive value-preservation round-trip, so an always-return-defaults bug can't pass.

---

## <a id="14"></a>14. Ingress validation layers: freeze the input-SHAPE allow-list at the contract; runtime containment/authorization is the boundary phase's

**Date:** 2026-06-18.
**Source slice:** 1.5c1 (`mcp_contract_ingress`).

The §14 MCP `get_file` path is untrusted input from an external caller, and its validation splits across two layers — the split is the lesson, and it's the **third instance of a recurring freeze-discipline pattern** (cf. LESSON 12 interface-vs-engine, LESSON 13 schema-vs-loader): the **frozen Phase-1 contract** pins the static, by-construction guarantee; the **runtime, stateful enforcement** belongs to the consuming phase. For an ingress path the contract layer is a **positive charset allow-list on the path SHAPE** (`re.fullmatch(r"[A-Za-z0-9._/-]+")` + reject leading `/`, any `..` segment, empty/whitespace — LESSON 10, default-deny, bypass-corpus-pinned). The contract layer deliberately does NOT — and cannot — do **containment**: "is this path inside the resolved project root?" needs the real root resolved at runtime (Phase 8.2), which canonicalizes the realpath and re-checks containment THERE. Critically, the shape layer accepts non-canonical-but-charset-valid forms (`a//b`, `a/./b`, `a/`, `.`) and dotfile paths (`.git/config`) — these are not traversal, and `.github/` is legitimately indexed (§8 discovery) — so the runtime containment MUST operate on the **resolved realpath** (collapsing `.`/`//`, resolving symlinks) before serving, with the redactor on egress regardless.

Two corollaries reinforced here. (1) **Strictest allow-list at a frozen boundary, widen additively.** ASCII-only was chosen over a unicode-aware `\w` allow-list because it eliminates the entire unicode-normalization/homoglyph/bidi residual class at once, and because loosening a frozen allow-list later is additive/safe while tightening it is breaking — so the reversible direction is freeze-tight, widen (with NFC-normalize) only when a real need appears. (2) **An ingress param REJECTS; a resolver FALLS BACK.** `get_file`'s validator raises `ValidationError` on a bad path (parse-don't-trust at the boundary), unlike 1.4c's `resolve_codegraph_dir` which defaults to `.codegraph` — a resolver supplies a value, an ingress param gates untrusted input, and silently defaulting untrusted input would mask an attack.

**Rule:** Split ingress validation — freeze the input-SHAPE positive allow-list (strictest/ASCII, bypass-corpus-pinned, widen-additively) at the Phase-1 contract; defer canonicalize-against-the-resolved-root CONTAINMENT + authorization + egress redaction to the boundary phase, and run containment on the resolved realpath (the shape layer admits non-canonical + dotfile forms by design). An ingress param raises; a resolver falls back.

---

## <a id="15"></a>15. A policy/authz denial is a typed returned MARKER, not a raised exception — discriminated + extra-forbid on both arms

**Date:** 2026-06-18.
**Source slice:** 1.5c2 (`mcp_contract_results`).

§14 mandates "policy-denied → marker-not-error": when the MCP boundary denies a tool call (an unauthorized project, a policy block), the tool returns a denial VALUE, never raises. A denial is an *outcome*, not a *failure* — raising would surface to the caller as a tool error indistinguishable from a crash/bug, losing the "you asked for something policy forbids" signal and inviting retry/alarm. So the frozen contract types the tool return as a discriminated union `McpToolResult = McpResult | PolicyDenied`, where `PolicyDenied{denied: Literal[True], reason}` is an ordinary frozen model the handler constructs and returns.

Two techniques make the union safe, both pinned. (1) **A `Literal[True]` discriminator** — `denied` can only be `True`, so a `PolicyDenied` can never masquerade as a non-denial (`False`/`None`/`0`/`""` rejected at parse). (2) **`extra="forbid"` on BOTH union arms** — so neither arm can smuggle the other's keys (a `McpResult` can't carry a stray `denied`; a `PolicyDenied` can't carry `items`/`provenance`), keeping the union unambiguous to a structural matcher. Pin the union itself with `typing.get_args(McpToolResult) == (McpResult, PolicyDenied)` so a future arm add/remove is a visible, test-breaking change. (Note: `denied=1` lax-coerces to `True` — harmless here because it only ever *strengthens* a denial; the boundary phase constructs `PolicyDenied` directly. A non-strengthening boolean would want `StrictBool` — see the safety-opt-in-bool sweep.)

**Rule:** Model a policy/authz denial as a typed returned marker in a discriminated union (`Result | Denied`), never a raised exception — give the marker a `Literal`-pinned discriminator, set `extra="forbid"` on both arms so neither smuggles the other's keys, and pin the union via `get_args`.

---

## <a id="16"></a>16. Shared cross-cutting types live in `core/_types.py`; identity vs content get distinct hardened aliases; freeze the char-policy tight before fork

**Date:** 2026-06-20.
**Source slice:** 1.6a (`identity_alias_consolidation_and_hardening`).

Eleven modules across `model/` and `ports/` had each re-declared the same `_StrippedStr`/`IdentityStr` alias — a maintenance hazard + an inconsistent hardening surface. The consolidation home is **`core/_types.py`**, a cross-cutting foundational module both `model/` and `ports/` import. It can NOT be `core/model/_types.py`: `ports/` is a §2.5 sibling of `model/`, so a `ports`→`model` import is a forbidden cross-sibling edge. A genuinely cross-cutting type module (imported from anywhere, depending on nothing) is the right placement — the §2.5 DAG's "cross-cutting layers can be imported from anywhere" clause.

Two aliases, not one, because identity and content have different threat models. **`IdentityStr`** (ids, paths, SHAs, tokens, markers, dict keys, symbols): strip + min_length + a TIGHT `max_length` (1024) + reject the full Unicode control/format/bidi/zero-width/separator set (categories `Cc`/`Cf`/`Zl`/`Zp` — bidi-overrides U+202A–E, zero-width U+200B–D, BOM U+FEFF, NEL U+0085, C1, line/para separators) while still ALLOWING legitimate unicode letters/digits (so a unicode source path like `日本語.py` validates). **`TextStr`** (human prose / model output / cited spans — `chunk.text`, `cited_text`, `GenerateResult.text`, plus message fields `PolicyDenied.reason`, `host.summary/detail`): strip + min_length + a LARGER cap (8192) + reject NUL/C0/C1 except `\t\n\r`, but KEEP legitimate multilingual format chars. The classification rule: *reference/identifier/path/marker → `IdentityStr`; human-readable prose/message → `TextStr`; explicitly-documented-loose or plain-value fields (e.g. an `ObsEvent` attribute value) → leave.*

The load-bearing call was the char-policy on the FROZEN cross-track identity fields. Rejecting the invisible/bidi/control Unicode classes on identities is a clear-cut, low-risk hardening (no legitimate id/path/SHA contains them), and the **before-fork window is the only cheap time to draw the line** — tightening a frozen cross-track contract after the fork is breaking. So freeze tight now, widen additively later if a real need appears (LESSON 14's freeze-tight-widen-additively, applied to the char set). This was owner-confirmed (the load-bearing-cross-track-contract + security-finding class the owner reserves). The mirror-image decision: the analogous CONTENT sanitization — bidi-overrides in `chunk.text`, which is *source code* (the Trojan-Source attack) — is deliberately NOT a frozen-contract hard-reject (that would refuse legitimate multilingual content); it belongs at the Phase-2 ingest/redactor as a flag/strip (LESSON 14: shape/by-construction at the contract, content sanitization at the consuming phase).

**Rule:** Hoist a shared field-constraint type to a cross-cutting `core/_types.py` (never a sibling package's `_types`, which forces a cross-sibling import); split identity (`IdentityStr` — tight cap + reject all control/format/bidi/zero-width unicode, allow letters) from content (`TextStr` — larger cap, keep multilingual); freeze the identity char-policy tight before the fork (post-fork tightening is breaking), and defer content/bidi (Trojan-Source) sanitization to the consuming phase.

---

## <a id="17"></a>17. Security/safety/lifecycle/output booleans use `StrictBool`, not `bool` — parse-don't-trust on booleans

**Date:** 2026-06-20.
**Source slice:** 1.6c (`strictbool_safety_bools`).

Pydantic's default `bool` is LAX: it coerces `1`/`0`/`"yes"`/`"true"`/`"on"`/`"1"` into `True`/`False`. On a field that gates **exposure, consent, authorization, lifecycle, or a system output**, that lax coercion is a parse-don't-trust hole — a malformed or attacker-influenced `"yes"`/`1` silently becomes `True` on a security-relevant flag. The 1.5b security-reviewer first flagged it on `policy.{mcp.expose, federation.visible, sessions.consent}`; the fix (owner-approved) generalizes to a uniform rule: **every frozen-contract boolean is `StrictBool`** (rejects the lax forms, accepts only a real `bool`), with ONE exemption — a **deny-strengthening `Literal[True]` marker** (`PolicyDenied.denied`), where a lax `1`→`True` only ever produces a denial and so can't weaken the gate.

The converted set (7) spanned the gate bools (policy opt-ins), the **security stamp** (`HostAction.authorized` — defense-in-depth atop the `perform` capability re-check, LESSON 9: a lax-coerced `authorized="1"` is now rejected at parse), the **lifecycle** flag (`Chunk.tombstone`), and the **system-output** flags (`HostResult.ok`, `McpResult.truncated`). The last two were included for a *uniform* rule rather than a per-field judgment, because "is this bool security-relevant enough?" is a fragile line and the cost of `StrictBool` everywhere is ~zero (every internal producer sets a real `bool`, so nothing legitimate is rejected). `StrictBool` is wire-identical to `bool` (a JSON boolean), so all schema/JSON snapshots stay green — it's a pure parse-tightening. The before-fork window is the time to draw it: a frozen cross-track bool tightened post-fork is breaking.

**Rule:** A frozen-contract boolean is `StrictBool` (reject lax `1`/`"yes"`/`"on"` coercion — parse-don't-trust), not bare `bool`; the only exemption is a deny-strengthening `Literal[True]` marker. Draw it before the fork (post-fork tightening is breaking); it's wire-identical so snapshots stay green.

---

## <a id="18"></a>18. A reusable measurement RIG ships REAL instrumentation + a Fake target + `PROPOSED_*` envelope constants; the authoritative numbers land where the real backend lands

**Date:** 2026-06-20.
**Source slice:** 0.4 (`lancedb_maintenance_bakeoff_rig`); generalizes spike 0.1 (`redaction_fuzz`).

A Phase-0 measurement rig exists to **de-risk a later phase's load-bearing unknown** (0.1: the §18 redaction recall envelope; 0.4: the §6 maintenance-contract "invisibility" budget). The durable pattern, shared by both rigs, is three parts: **(1) REAL instrumentation** — the measurement code that will run unchanged against the real backend later (0.1's leak oracle; 0.4's `tracemalloc`-peak / monotonic-delta / dir-walk meters), unit-tested against known quantities; **(2) a deterministic Fake/stub target** that validates the harness wiring without the real dependency (`stub_redactor` / `FakeMaintenanceStore`) — so the rig + its tests run with no heavy dep; **(3) named `PROPOSED_*` envelope constants** (`PROPOSED_RECALL_FLOOR`/`PROPOSED_FP_CEILING`; the `PROPOSED_*` latency/RAM/disk ceilings) flagged in-docstring as *proposed, pending the real run*. The **authoritative numbers** (real recall %, real reference-Mac latency/RAM/disk) are set **where the real backend lands** (2.3 for the redactor; Phase 3 for `lancedb`) — **never bake a real-hardware or real-quality number into the rig as a claim.** The rig lives in **`ci/`** (above `core/`, never imported by core; `core ⊥ ci/` both directions) and runs **out-of-band** (under the `core/` uv env), not in the core suite.

The 0.4 review fold added a sharp sub-lesson: **design the instrumentation against the real backend's actual cost model, even when validating against a Fake.** The RAM meter must span ingest **+ `optimize()`**, because a real `lancedb` index build's RAM lives in `optimize()`, not ingest — a meter wrapping only ingest would read ~0 on the real Phase-3 target and silently under-report the load-bearing metric. The Fake validates wiring; the real cost model dictates *what window* to measure.

**Rule:** A reusable measurement RIG (a Phase-0 spike de-risking a later phase) ships REAL instrumentation + a deterministic Fake target + named `PROPOSED_*` envelope constants; the authoritative numbers land where the real backend lands (never bake a real-hardware/quality number into the rig); it lives in `ci/` and runs out-of-band (never imported by core); and the instrumentation is designed against the real backend's cost model (measure the right window, not the convenient one).

---

## <a id="19"></a>19. An ingest-stage's re-declared closed set is pinned EQUAL to the frozen contract's via a `get_args` drift test

**Date:** 2026-06-21.
**Source slice:** 2.1 (`discovery_and_classification`).

The classifier (`core/ingest/classify.py`) emits a `FileClassification` whose `doc_or_code` and `ownership` fields are `Literal` closed sets that MUST equal the frozen `Chunk` contract's same-named fields (§5/§8): the `add` pipeline (2.4) folds the classification straight into `Chunk`s, so any divergence — a value the classifier can emit that `Chunk` rejects, or vice-versa — is a latent runtime `ValidationError` deferred to the first real ingest, not a caught one. The stage re-declares the alphabet locally rather than importing the model for two string tuples (ingest → model is a permitted import, but the local restatement keeps the stage readable); the trap is that two independently-declared closed sets **drift silently** — nothing fails until a real file hits the unmatched value.

The fix is a **drift test** asserting the two are byte-identical via `typing.get_args` on the model annotations — `get_args(FileClassification.model_fields["doc_or_code"].annotation) == get_args(Chunk.model_fields["doc_or_code"].annotation)` (and the same for `ownership`). It fails the instant either side changes without the other, converting a deferred runtime failure into a unit failure. This is the closed-set analogue of LESSON 6 (StrEnum membership snapshot) for the case where a **non-contract stage mirrors a contract field** rather than owning its own canonical alphabet. The open-ended axes (`producer`/`doc_type`, typed `IdentityStr`) are deliberately NOT membership-pinned — the contract declares them open ("classifier may grow") — so a non-empty assertion is the only guard they get.

**Rule:** When an ingest/pipeline stage re-declares a `Literal` closed set that must equal a frozen contract field's, pin the equality with a `get_args` drift test on both model annotations — never trust two hand-kept copies to stay in sync (a drift is a *deferred* runtime `ValidationError`). Open-ended (`IdentityStr`) axes get a non-empty guard, not a membership pin.

---

## <a id="20"></a>20. A mid-pipeline stage with an all-required frozen output contract emits an internal `*Draft`; the frozen model is assembled where the full context exists

**Date:** 2026-06-21.
**Source slice:** 2.2a (`anchor_aware_chunking_docs`); companion to LESSON 19.

The §8 chunk stage must produce `Chunk` + `Anchor` data, but **both frozen contracts are all-required** — `Chunk` needs `vector` (embed, Phase-3), `chunk_id`/`created_at` (IdGen/Clock seams), `*_sha`/`generation` (ingest, 2.4); `Anchor` needs `anchor_id`/`project_id`/`last_resolved_sha`. None of that context exists at chunk-time. The wrong move is to relax the frozen contract (make fields optional, add a placeholder `vector=[]`) so it can be partially built early — that punches a hole in a freeze-before-fork cross-track contract (a Finding) and defers the "is this really populated?" question to runtime. The right move: the stage emits an **internal `*Draft`** (`ChunkDraft`) carrying exactly the **chunk-derivable subset** + the stage-owned data (here: the anchor span strings, whose *syntax* this producer owns); the **frozen model is assembled at the stage that has the full context** (2.4, with ingest-context + the IdGen/Clock/embed seams). The draft is a plain internal type (like `DiscoveredFile`/`FileClassification`) — frozen + `extra="forbid"` for parse-don't-trust, but **not** an Appendix-A contract (no freeze/snapshot obligation), so it stays free to evolve across the spine's stages.

Two pins keep the draft honest against the contract it feeds: a **`get_args` closed-set drift test** (LESSON 19) and a **field-name subset test** (`draft's chunk-mirroring fields ⊆ Chunk's fields`, against a canonical `ANCHOR_SPAN_FIELDS` constant so the test doesn't re-declare the boundary) — so a draft field that couldn't fold into `Chunk` fails a unit test, not the first real ingest. A subtle corollary surfaced in review: the draft's fields inherit the **contract's own value constraints** even pre-assembly — `ChunkDraft.text` is `TextStr` (cap `TEXT_MAX_LEN`) and `target_symbol` is `IdentityStr` (cap `IDENTITY_MAX_LEN`), so the stage must already respect those caps (sub-split oversized text; truncate an over-long symbol) or it crashes on its own "any input" guarantee. The draft isn't a constraint-free scratch type — it's the contract's antechamber.

**Rule:** A mid-pipeline stage whose frozen output contract is all-required emits an internal `*Draft` of the derivable subset (frozen + `extra="forbid"`, but NOT an Appendix-A contract); assemble the frozen model at the stage that owns the full context (ids/SHA/vector via the seams) — never relax or partially-construct a frozen cross-track contract. Pin the draft to its target with a `get_args` closed-set test + a field-name subset test, and honor the target's per-field value constraints (caps) in the draft already.

---

## <a id="21"></a>21. Redactor detection: run the allowlist BEFORE the entropy test, and capture the whole sensitive value

**Date:** 2026-06-21.
**Source slice:** 2.3 (`redactor_catchable_set_engine`); ★ Key safety rule #2.

Three detection-ordering/completeness rules the §18 redactor lives or dies by — all surfaced building (or security-reviewing) the catchable-set engine:

1. **Allowlist before entropy (the cardinal ordering).** A git-SHA / ULID / UUID is high-entropy *by shape*, so an entropy filter that runs first will redact it — and redacting a git-SHA is the cardinal §18 residual failure (it breaks the LanceDB version tag, `last_resolved_sha` provenance, and manifest integrity — §18/D-14). The allowlist (40/64-hex SHA · ULID · UUID) MUST run first; only a value that survives it reaches the entropy test. (Anticipated in the brief; the convention the whole engine is ordered around.)

2. **Capture the WHOLE sensitive value, not the high-entropy run (the security-HIGH this slice).** A detector that redacts only the contiguous high-entropy substring leaks the tail of a value that contains an embedded delimiter — `API_KEY=ab,cd<more-secret>` splits at the `,` and the tail survives (and the all-alphanumeric fuzz corpus structurally can't see it, so the *gate* read green while a real leak existed — only the adversarial security review caught it). Redact a sensitive value to its quote/delimiter boundary (quoted → to the closing quote; non-sensitive → conservatively to the delimiter as the URL-query FP guard).

3. **Entropy detection is CONTEXTUAL — assignment values only, never a bare-token scan.** A blanket high-entropy scan over bare tokens redacts every hex/base64/long-id literal = unacceptable false positives; restricting entropy redaction to values *inside an assignment* (`KEY=v` · `export` · YAML `k: v` · JSON `"k":"v"`) is what holds the bare-token FP corpus at 0%.

**Rule:** In a redaction/secret-detection engine, run the passthrough ALLOWLIST (git-SHA/ULID/UUID) before any entropy test (entropy-first redacts a SHA = the cardinal §18 residual failure); capture a flagged sensitive value WHOLE to its quote/delimiter (a partial high-entropy run leaks the tail past an embedded delimiter); and scan entropy contextually (assignment values only, never bare tokens) to hold false positives down. A synthetic gate that reads green does NOT prove completeness — adversarial review of the detection logic is the backstop.

---

## <a id="22"></a>22. Redaction idempotence keys on an EXACT marker match, never a prefix — a prefix check is input-spoofable

**Date:** 2026-06-21.
**Source slice:** 2.3 (`redactor_catchable_set_engine`); ★ Key safety rule #2 (security-reviewer MED).

A redactor must be idempotent (`redact(redact(p,s),s) == redact(p,s)`) — it skips re-processing content it already redacted, identified by its own marker. The trap: implementing that skip as `value.startswith("[REDACTED")` is **input-spoofable** — ingested content (source code, a doc, an MCP payload) can itself contain the literal `[REDACTED…` prefix shape and thereby **suppress redaction of an adjacent real secret** (wrap the secret's container in the marker shape and the prefix check waves it through). Idempotence must instead key on an **EXACT match against the closed, finite marker set** (`{[REDACTED_TOKEN], [REDACTED_SECRET], [REDACTED_PEM_KEY], [REDACTED_JWT], [REDACTED_CREDENTIAL]}`) — only the redactor's OWN exact markers are skipped; a spoofed near-marker is processed normally. The marker set is closed + secret-free (matches no detector), so exact-match idempotence holds without re-triggering. Generalizes to any sanitizer/marker scheme: the skip-already-done predicate over UNTRUSTED input must be exact-and-closed, never a prefix/substring (a fuzzy self-recognition check on attacker-influenced data is a suppression vector).

**Rule:** A redactor/sanitizer's "already-processed" skip predicate keys on an EXACT match against a closed marker set, never `startswith`/`contains` — a prefix/substring check on untrusted content is spoofable to suppress redaction of an adjacent real secret.

---

## <a id="23"></a>23. Vendor the one needed module (license-retained, edits-flagged) when an architecture-pinned dep is deprecated/un-importable but its logic is sound

**Date:** 2026-06-21.
**Source slice:** 2.2b (`anchor_aware_chunking_code`).

When an architecture-pinned dependency is deprecated or un-importable (a broken package `__init__`, a removed transitive module — here `llama-index-packs-code-hierarchy`'s `__init__` eagerly imported a `llama_index.core.llama_pack` module removed from current core, breaking every import path to the `CodeHierarchyNodeParser` we needed) but the **specific logic is sound + permissively licensed**, the right remediation is to **VENDOR that one module** — NOT to fight the broken package (pin-hunting old version pairs, `importlib`/`sys.modules` shims around the `__init__`) and NOT to silently swap to a different tool (an architecture deviation = escalate to the owner). Vendoring done right: copy the single module **verbatim** into the codebase behind an internal seam; **retain the original copyright + license notice + a provenance comment** (source package + version); pin **only the libraries that module actually imports** (not the broken parent package — and watch for a SECOND-order incompatibility: the chosen grammar lib `tree-sitter-language-pack` bundled its own incompatible tree-sitter binding, forcing standard `tree_sitter` + individual grammar packages, LESSON-21-adjacent "verify the transitive runtime, not just the install"); mark every necessary edit in-file (`# VENDOR-EDIT`) + flag at Step 9 (here 3: the grammar-loader rewrite, the grammar registry, a Pydantic v1→v2 `.dict()`→`.model_dump()` compat fix **required** because `.dict()` RAISES under `-W error` on Pydantic v2); **exclude the vendored file from strict lint/type** (it's vendored-not-authored). This preserved the exact owner-chosen capability (the deep-hierarchy parser) while escaping the deprecated pack. Two governance musts: it's a **load-bearing dep decision → owner sign-off** (the owner chose vendor-over-alternatives deliberately); and carry a **re-sync-vs-upstream TODO** + the owner's standing instruction that a maintained library genuinely beating the vendored module on a material capability is surfaced BEFORE finalizing, never silently swapped.

**Rule:** When an architecture-pinned dep is deprecated/un-importable but the needed logic is sound + permissively licensed, VENDOR that one module behind an internal seam (license + provenance retained, every edit `# VENDOR-EDIT`-flagged, pin only the libs it imports + verify their transitive runtime, exclude from strict lint) — don't fight the broken package or silently swap tools (an arch deviation = escalate). Requires owner sign-off + a re-sync-TODO.
