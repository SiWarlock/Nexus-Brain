# Federation Cross-Repo Resolution Probe — Phase-0 Spike 0.3 (O-FED)

**Date:** 2026-06-20  
**Investigator:** orchestrator spike agent  
**Scope:** Retire the `[SPIKE — O-FED]` open question before the Phase-6 federation router contract — can cross-repo symbol resolution be done by matching CodeGraph's `unresolved_refs.reference_name` (+ `candidates` JSON) in repo A against the namespaced `qualified_name` of `nodes` in repo B?  
**Anchors:** `ARCHITECTURE.md §11` (federation router & registry; `{projects_requested, answered, excluded[]}`; side-by-side-marked fallback) · `§6` (per-project CodeGraph DB) · `§24`/`§26` (silently-partial answer = trust failure).

---

## Verdict

**`reference_name` × namespaced-`qualified_name` resolution is VIABLE as a *merge-when-unambiguous* enrichment, but NOT as the default — side-by-side-marked must stay the conservative default, and cross-repo merge only fires when the match is unique.** Against a 56-ref / 35-node schema-faithful synthetic corpus, a namespace-aware **segment-suffix** match achieved **precision 1.000** (29/29 single-resolutions correct, zero false positives, zero forced picks on ambiguous refs) and **recall 0.967** (29/30 true single-truth links). Crucially, the matching rule fails *safe in the right direction*: lost/partial namespace precision pushes borderline refs into AMBIGUOUS or NO_MATCH (both → marked-excluded), never into a wrong RESOLVED. A real v0.9.7 cross-check (optional, ran without friction, no install) revealed the load-bearing caveat: real CodeGraph `qualified_name` is **thinner** than the schema example (`verifyToken`, `PaymentGateway::charge` — no file-path prefix), and a real repo's `unresolved_refs` table can be **sparse/empty**. Thin namespacing only *increases* ambiguity (safe), but sparse `unresolved_refs` directly caps recall. Net: ship it gated behind a uniqueness check; keep `excluded[]` as the floor.

---

## 1. Method + why synthetic

**Primary method = a schema-faithful synthetic corpus, by design.** Per the §18 supply-chain posture ("pin-by-hash, fail-closed"), CodeGraph is provisioned later via `setup` with hash verification — it is **not** ad-hoc-installed inside a spike. So the federation resolution question (a *schema-shape* question, not a runtime question) is answered against a corpus hand-authored to the CodeGraph 1.0.1 schema verified in spike 0.2: `unresolved_refs(id, from_node_id, reference_name NOT NULL, reference_kind NOT NULL, line, col, candidates TEXT(JSON), file_path, language)` and `nodes(id, kind, name, qualified_name NOT NULL, file_path, language, …, is_exported, …)`. The federation-relevant columns are identical across 0.9.7→1.0.1 (the only 1.0.1 diff, `nodes.return_type`, is irrelevant here), so the schema basis is sound.

**Optional real cross-check ran (no install).** A `codegraph` binary (v0.9.7) was already on PATH; it indexed two tiny `/tmp` fixture repos (`realA` referencing, `realB` defining) without friction in ~60ms each. **No upgrade to 1.0.1 and no package install were performed** — the binary already present was used as-is, and the throwaway `.codegraph/` index dirs were deleted after reading. The cross-check produced two material divergences from the synthetic assumptions (see §6, Risks 1 & 2); they were folded into the verdict rather than dismissed.

All prototype code, fixtures, and SQLite DBs are throwaway and live under `/tmp/ofed-spike/` (corpus builder, resolver, ground truth). Nothing outside this probe doc is a deliverable.

## 2. Fixture / corpus setup

**Two SQLite DBs faithful to the 1.0.1 schema:** `repoA.db` (referencing repo — `unresolved_refs` only) and `repoB.db` (defining repo — `nodes` only). B holds **35 nodes** (34 exported), a realistic mix of a TS service (`src/auth/…`, `src/billing/…`, `src/codec/…`) plus a Python module (`app.users.…`, `app.notify.…`), including deliberate cross-repo homonyms. A holds **56 `unresolved_refs`**, each carrying a hand-labeled GROUND TRUTH (`gt` = the true B `qualified_name`, a *set* of qnames for genuine homonyms, or `None` for no-match) and a case class:

| Class | n | What it probes |
|---|---|---|
| **clean** | 16 | one A-ref unambiguously maps to exactly one B `qualified_name` |
| **ambiguous** | 12 | one `reference_name` matches ≥2 B `qualified_name`s (cross-repo homonyms — `validate`, `connect`, `Logger`, `encode`, `serialize`) — MUST be marked, never picked |
| **nomatch** | 14 | A-ref has no real B definition (incl. a stale-`candidates` ghost id, a dotted `legacyAuth.refresh`) — MUST fall through to marked-excluded |
| **nsvar** | 14 | same symbol, varied/partial `qualified_name` formats (slash-path, `::` vs `.`, missing `app.` prefix, bare leaf, cross-language) — probes matching-rule brittleness |

`candidates` JSON is populated on a realistic subset (sometimes empty, sometimes the bare name, once a ghost id `someGhostId_999`) to exercise candidate-set union and stale-candidate fall-through.

## 3. Resolution approach (the exact matching rule)

**Namespace-aware segment-suffix match.** For each `unresolved_ref` with `reference_name` R:

1. **Normalize** R into segments by splitting on `::`, `.`, and `/`, then dropping pure file-extension tail tokens (`ts/py/js/…`). `src/auth/token.ts::verifyToken` → `[auth, token, verifyToken]`; `billing.PaymentGateway.charge` → `[billing, PaymentGateway, charge]`.
2. For each **exported** B node (`is_exported=1` — a non-exported symbol is not a valid public cross-repo target), normalize its `qualified_name` the same way. The node is a CANDIDATE iff **`segs(R)` is a segment-wise suffix of `segs(qualified_name)`** (R is a trailing, more-or-equally-qualified slice of the B qname).
3. **Candidate-set union:** if the ref's `candidates` JSON holds a token whose segments suffix-match an exported B node, add that node too (intersection of CodeGraph's own guesses with B's real symbols).
4. **Decision:** exactly **1** distinct B node → `RESOLVED` (emit qname); **≥2** → `AMBIGUOUS` (MARK; emit nothing); **0** → `NO_MATCH` (MARK excluded; emit nothing).

Suffix (not exact) match is what lets a partial namespace at the call site bind to a fully-qualified B definition — and is *also* the deliberate source of homonym ambiguity, which the rule is required to MARK rather than resolve.

## 4. Measurement (precision / recall + per-class)

Precision = correct single-resolutions emitted / total single-resolutions emitted. Recall = correct single-resolutions / true single-truth cross-repo links (clean + nsvar). Ambiguous and no-match classes are scored on *marking* correctness, not emission.

| Class | n | RESOLVED | AMBIGUOUS | NO_MATCH | Notes |
|---|---|---|---|---|---|
| clean | 16 | 16 (all correct) | 0 | 0 | 16/16 |
| nsvar | 14 | 13 (all correct) | 0 | 1 | 1 conservative miss (see below) |
| ambiguous | 12 | 0 | 11 (all correct) | 1 | **0 forced picks**; 1 was a true no-match (label artifact, see below) |
| nomatch | 14 | 0 | 0 | 14 (all correct) | **0 false positives** |

```
Single-resolutions emitted        : 29   (correct: 29)
PRECISION (correct / emitted)     : 1.000
True single-truth links (clean+ns): 30
  recalled                        : 29
RECALL (correct / true links)     : 0.967
AMBIGUITY: 11/12 marked ambiguous; 0 forced single-pick  (must be 0 ✓)
NO-MATCH : 14/14 marked excluded ; 0 false-positive resolved (must be 0 ✓)
```

**The two non-RESOLVED-correct cases, both conservative-safe:**

- `billing.PaymentGateway.charge` → NO_MATCH (the one true recall miss). The call site's namespace `[billing, PaymentGateway, charge]` is **not** a suffix of B's `[src, billing, gateway, PaymentGateway, charge]` because the *file* segment `gateway` sits between `billing` and `PaymentGateway`. The caller's mental package namespace diverges from CodeGraph's file-derived one. The rule correctly **marks** rather than guesses — recall cost, zero precision cost.
- `Logger.info` → NO_MATCH (counted against "ambiguous" in the harness, but the resolver is actually *right*). There is no `Logger.info` node in B (only the `Logger` class), so `[Logger, info]` suffix-matches nothing. NO_MATCH is sound: a method call on a homonym class is unresolvable cross-repo until the class itself is resolved. This is a ground-truth **label artifact**, not a resolver error — the real ambiguous-marking rate is effectively 11/11.

## 5. Fallback-path confirmation (ambiguous + no-match → marked/excluded)

**Confirmed sound.** The two failure classes that §11 cares about both terminate in a *marked* outcome, never a guess:

- **Ambiguous (≥2 B candidates):** 0/12 forced single-picks. The resolver emits the full candidate set tagged AMBIGUOUS and resolves nothing — the federation router routes these into `excluded[]` (or surfaces all candidates side-by-side-marked), never silently into the merged answer.
- **No-match (0 B candidates), incl. stale `candidates` ghosts and dotted partials:** 14/14 marked NO_MATCH, 0 false positives. The ghost-id candidate (`someGhostId_999`) correctly contributed nothing because it suffix-matches no real exported B node — stale candidates fall through cleanly.

This is exactly the §11 / §24 / §26 contract: a **silently-partial portfolio answer is a TRUST FAILURE**. Every ref that cannot be uniquely bound is *visible* in the result envelope (`{projects_requested, answered, excluded[]}`), so an answer is never quietly missing a repo's contribution. The matching rule's bias — degrade toward AMBIGUOUS/NO_MATCH under namespace loss — is aligned with this invariant by construction.

## 6. Open risks for the Phase-6 federation router

### Risk 1 (HIGH): `unresolved_refs` can be sparse/empty — directly caps recall

In the real v0.9.7 cross-check, `realB/src/auth.ts` exported `verifyToken`/`PaymentGateway` and `realA/src/handler.ts` called them with no local definition, yet repo A's `unresolved_refs` table came back **empty** (only 2 nodes recorded; the call-site refs were not emitted as unresolved). Cross-repo resolution can only resolve refs that CodeGraph actually *records* as unresolved; if the indexer under-populates `unresolved_refs` for a language/construct, those links are invisible regardless of how good the matcher is. **Recommendation:** treat `unresolved_refs` coverage as parser/version/language-dependent and unknown until measured on real indexed repos; never assume the table is complete. Recall in production will be ≤ the synthetic 0.967.

### Risk 2 (HIGH): real `qualified_name` is THINNER than the schema example → more homonyms

Real v0.9.7 emitted `qualified_name = 'verifyToken'` (bare) and `'PaymentGateway::charge'` — **no file-path or package prefix**, unlike the spike-0.2 example `src/utils/auth.ts::verifyToken`. Stripping file-path namespacing collapses distinct symbols that share a leaf name into homonyms. Re-running the rule against thin qnames, the *only* names that newly collide were `validate`, `connect`, `Logger`, `encode`, `serialize` — i.e. exactly the symbols already designed as homonyms; unique leaf names (`verifyToken`, `hashPassword`) still resolve. So thin namespacing pushes borderline cases **toward AMBIGUOUS, never toward false RESOLVED** — precision is preserved, recall erodes. Still HIGH because production recall depends entirely on how much real namespace survives in `qualified_name`.

### Risk 3 (MEDIUM): cross-repo homonyms are intrinsic, not a tuning artifact

`validate`/`connect`/`Logger`/`encode`/`serialize` across two real repos genuinely cannot be disambiguated from `reference_name` alone (no type info at the unresolved call site). These are correctly marked, but a federation router that wants *merge* coverage on common names will hit a hard ceiling. **Recommendation:** do not attempt heuristic tie-breaking (e.g. "pick the most-exported / first-alphabetical") — that trades a marked-excluded (honest) for a possibly-wrong merge (trust failure). Keep them in `excluded[]`.

### Risk 4 (MEDIUM): partial-namespace mismatch (file-segment vs package-segment)

The `billing.PaymentGateway.charge` miss shows caller-namespace ≠ CodeGraph file-namespace. A strict segment-suffix rule under-resolves when an intermediate *file* segment is absent from the caller's reference. Loosening to a "subsequence" (non-contiguous) match would recover it but would also manufacture false positives — not worth the precision risk for the federation default.

### Risk 5 (LOW): language-specific `qualified_name` formats

Python (`app.users.repo.UserRepository.find_by_id`, dotted) vs TS (`src/billing/gateway.ts::PaymentGateway.charge`, `::`-flavored) normalize fine under the split-on-`{::,.,/}` rule in this corpus, but a third language's convention (Go receivers, Rust paths, Java FQNs) is unverified. **Recommendation:** add per-language normalization fixtures before relying on cross-language federation merges.

## 7. Recommendation

1. **Ship `reference_name` × `qualified_name` resolution as a uniqueness-gated *enrichment*, not the default.** The federation router's default contract stays **side-by-side-marked** (`{projects_requested, answered, excluded[]}`); a cross-repo link is merged into the answer **only** when the segment-suffix match yields exactly one exported B node. Everything else → `excluded[]`. This banks the 1.0 precision while honoring the §24/§26 "silently-partial = trust failure" invariant.
2. **Use the matching rule from §3 verbatim** (normalize on `{::, . , /}` + drop ext tails; suffix match against `is_exported=1` B nodes; union the `candidates` set; ≥2 → ambiguous, 0 → excluded). Do **not** add heuristic tie-breaking.
3. **Set no precision/recall bar from this spike alone.** Synthetic precision is 1.0 by the rule's safe-degradation property, but production *recall* is gated by two real-world unknowns (Risk 1 sparse `unresolved_refs`, Risk 2 thin `qualified_name`) that the synthetic corpus cannot measure.
4. **Run a real-CodeGraph validation pass once provisioned** (via `setup` + hash-verification, per §18 — never ad-hoc). Measure, on real multi-repo indexes: (a) `unresolved_refs` coverage per language, (b) how much namespace survives in `qualified_name`, (c) the cross-repo homonym rate. Only then set a merge-coverage expectation for the Phase-6 router. Name the failure modes to watch: sparse/empty `unresolved_refs`, thin/partial `qualified_name`, cross-repo homonyms, file-vs-package namespace mismatch, language-specific qname formats, and stale `candidates`.

---

*Spike complete. Reviewed + accepted by the orchestrator; committed at the Phase-0 round seal. Method = schema-faithful synthetic corpus + a bounded already-present-v0.9.7 real cross-check, §18-aligned (no ad-hoc install) — see D-A18.*
