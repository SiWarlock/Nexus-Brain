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
