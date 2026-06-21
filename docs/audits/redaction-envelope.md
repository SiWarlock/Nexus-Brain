# Redaction Envelope — Spike 0.1

**Date:** 2026-06-17
**Track:** contract
**Spike:** 0.1 — redaction property/fuzz harness + envelope
**Anchors:** `ARCHITECTURE.md §18` · `THREAT_MODEL.md §Redaction engine` · `DECISIONS.md D-15/D-26/C-11`
**Status:** COMPLETE — harness validated (34/34 tests pass), stub baseline measured.
**De-risks:** Phase-1.5 `Redactor` interface freeze · Phase-2.3 engine build.

---

## 1. Gate definition (the "zero-leak" invariant)

From `ARCHITECTURE.md §18` (exact quote):

> **Redaction gate = "zero-leak on the CATCHABLE set"** (recall-floor on curated prefix/entropy/JSON-value classes; **enumerated accepted residuals** — ≈git-SHA hex, adversarial <20-char split, sub-20-char JSON; the literal-zero promise was undeliverable, D-26/C-11); **keychain-refs-only is the PRIMARY control**, redactor = defense-in-depth.

Operational interpretation:
- "Zero-leak" applies ONLY to the **catchable set** (defined below in §2).
- The **accepted residuals** (§3) are exempted by name in §18 — they are NOT gate failures.
- The gate is a **recall-floor + FP-ceiling** on the catchable set (not literal zero across all inputs).
- The primary control is **keychain-refs-only** at ingest time. The redactor is the second line of defense for accidental leaks.

---

## 2. Catchable-set classes

The harness covers all four classes enumerated in `THREAT_MODEL.md §Redaction engine`. These are the classes for which the §18 recall-floor gate applies.

| Class | `SecretClass` enum | Examples | Detection approach |
|---|---|---|---|
| **Prefix-tokened keys** | `PREFIX_TOKEN` | `ghp_*`, `github_pat_*`, `sk-*`, `xoxb-*`, `AKIA*`, PEM blocks, JWT (`*.*.* base64url`) | Token-prefix scan. High precision, deterministic. |
| **High-entropy KEY=value** | `HIGH_ENTROPY_KV` | `SECRET_KEY=<40-char alphanum>`, `export SIGNING_KEY=<...>`, base64-encoded values in `KEY=value` | Shannon-entropy scoring on the value when the key name carries a secret indicator. |
| **JSON sensitive-value** | `JSON_SENSITIVE_VALUE` | `"password": "<value>"`, `"token": "<value>"`, `"api_key": "<value>"` with value length >= 20 | JSON key name allowlist + value length floor. |
| **Env dump** | `ENV_DUMP` | Multi-line `printenv` or `.env` output containing mixed secrets | Context-aware multi-line scan combining prefix + KV detection. |

**Corpus coverage (spike 0.1):**
- Generated samples: ~150 (property-based, seeded RNG, reproducible)
- Adversarial samples: 20 (curated hard cases: split secrets, base64, code comments, URLs, env dumps, accepted-residual boundaries)
- Total catchable-set samples per run: **125**

---

## 3. Enumerated accepted residuals (§18-anchored)

These are the ONLY classes exempted from the catchable-set gate. They are explicitly named in `ARCHITECTURE.md §18` and `DECISIONS.md D-26/C-11`. Do NOT add new values without an orchestrator escalation + owner gate.

| `AcceptedResidualClass` | §18 anchor | Rationale |
|---|---|---|
| `GIT_SHA_HEX` | §18 / D-14 | Git SHA-1 (40-char) and SHA-256 (64-char) hex strings pass the entropy filter but are non-sensitive version identifiers. LanceDB git-SHA version tagging (`D-14`) requires them to pass through unreacted. Zero tolerance for redacting git SHAs (hard sub-invariant, separately tested). |
| `ADVERSARIAL_SHORT_SPLIT` | §18 / C-11 | Secrets split into sub-20-character fragments across chunk boundaries. The literal-zero promise is undeliverable for adversarial split cases — the primary control (keychain-refs-only) prevents the full secret from reaching the redactor. These cases produce short prefixes (`sk-`, `AKIA`, `ghp_`) that are below the minimum detection length. |
| `SUB_20_CHAR_JSON` | §18 / C-11 | JSON `"password"`/`"token"`/`"secret"` values shorter than 20 characters. Below this floor, FP rate becomes unacceptable (common words: `changeme`, `test`, `admin`). The 20-char floor is the minimum-length threshold for the JSON-sensitive-value class. |

### Sub-invariant: git SHA FP rate = 0.0%

This is separately enforced as a hard test (`test_git_sha_not_redacted_by_stub`). The stub passes at 0.0% FP on git SHAs. The Phase-2.3 engine must also pass. Redacting git SHAs would break LanceDB version tagging (D-14), chunk provenance (`last_resolved_sha`), and manifest integrity — these are architecture-level invariants, not just quality metrics.

---

## 4. Leak oracle definition

A **leak** is defined as:

> The plaintext value of a catchable-set secret (or a recognizable substring of it, length >= 8) appears literally in the redacted payload delivered to the sink, after case-normalization.

**Oracle conservatism notes:**
1. The oracle uses literal substring matching (case-insensitive). It does NOT track encoding-aware forms (e.g. the base64 encoding of an already-base64-encoded secret). The Phase-2.3 engine should address this by decoding before detection, not by weakening the oracle.
2. The minimum detection length is 8 characters. Short prefixes (`sk-`, `AKIA`, 3–4 chars) below this threshold are classified as `ADVERSARIAL_SHORT_SPLIT` accepted residuals.
3. All sink checks are in-memory string comparisons. No network calls. (Safety rule #6.)

A **gate failure** is a leak that does NOT have an `accepted_residual` classification. Accepted-residual leaks are tracked separately and do not contribute to the recall floor.

---

## 5. Proposed envelope

### Recall floor (catchable set): **≥ 95%**

| Rationale | |
|---|---|
| §18 requires "zero-leak on the catchable set" | A hard zero is practically unachievable for adversarial inputs not yet in the corpus (new prefix patterns, novel encoding chains). 0.95 is the enforceable approximation of "zero" on the current corpus. |
| The `prefix-entropy-v3` approach (THREAT_MODEL.md) achieves near-perfect recall on prefix + JSON classes in NexusOps | Real engine should target 0.98+ on a calibrated run; 0.95 is the CI gate floor to allow some corpus noise. |
| Stub baseline: 77.6% | The stub deliberately underperforms (missing entropy + base64). This gap confirms the harness is measuring something real, not a tautology. |
| **Flag for escalation if:** the real Phase-2.3 engine cannot exceed 0.95 on the current corpus | That would indicate a fundamental approach failure or a corpus calibration problem — escalate to orchestrator. |

### FP ceiling (non-secret look-alikes): **≤ 5%**

| Rationale | |
|---|---|
| Git SHAs, UUIDs, short JSON values are explicitly excluded from the catchable set | The main FP risk is entropy-based misclassification of code hex constants and UUID-shaped values. |
| False positives degrade ingest quality | Incorrectly redacted content becomes unsearchable; too many FPs make the redactor a liability. |
| 0.05 ceiling allows ~1–2 FPs per 26 non-secret samples | Corresponds to accepting noise from high-entropy code literals that lack disambiguating key context. |
| Stub baseline: 0.0% FP | The stub is conservative (prefers recall over precision); the real entropy-scoring engine may produce more FPs. |
| **Sub-invariant:** git SHA FP rate = 0.0% (zero tolerance, hard test) | |

---

## 6. Methodology

### Property generator (`generator.py`)
Covers all four §18 classes with a seeded deterministic RNG (reproducible, no crypto randomness). Generates:
- GitHub PAT (classic + fine-grained), OpenAI/Anthropic `sk-*`, Slack `xox*`, AWS `AKIA*`, PEM blocks (4 types), JWT-shaped tokens
- HIGH_ENTROPY_KV: 10 key names × 3 context formats
- BASE64_KV: 6 samples (base64 of synthetic values, in `KEY=b64value` form)
- JSON_SENSITIVE_VALUE: 7 key names × 3 JSON formats + 4 nested blobs
- ENV_DUMP: 4 multi-line env blobs

### Adversarial corpus (`corpus.py`)
Hand-crafted hard cases (20 samples):
- **Split secrets:** 3 cases (prefix only at chunk boundary — accepted residual)
- **Comment-embedded:** 3 cases (Python `#`, shell `#`, JS `/** */`)
- **URL-embedded:** 3 cases (git remote, DB URL password, query param token)
- **Base64-encoded:** 2 cases (K8s Secret YAML, AWS secret in k8s)
- **Env dump mixed:** 2 cases (CI log dump, `printenv` output)
- **Accepted-residual edges:** 6 cases (git SHAs, sub-20-char JSON, exactly-20-char boundary)

### Leak oracle (`oracle.py`)
Conservative literal substring match (case-normalized). `is_gate_failure()` excludes accepted residuals. FP detection compares original vs redacted payloads.

### Measurement harness (`harness.py`)
`run_harness(redact_fn, sinks, verbose) -> dict[Sink, HarnessReport]`. One report per sink; report carries recall, FP rate, per-class breakdown, leaked samples, FP samples, and `gate_pass(floor, ceiling)`.

---

## 7. What the Phase-1.5 `Redactor` interface + Phase-2.3 engine must assert

### 7.1 Interface contract (Phase-1.5 freeze)

The `Redactor` interface MUST specify:

1. **Sink enum** — the callable must accept `sink: Sink` with exactly three values: `{persist, mcp_egress, cloud_egress}`. All three are required; the engine MAY apply stricter policy on `cloud_egress` but MUST cover all three. (§18: "runs at all three sinks.")

2. **Accepted-residual contract** — the interface docstring MUST enumerate the three accepted-residual classes by name (git SHA hex, adversarial <20-char split, sub-20-char JSON) and cite §18/C-11. Any caller that relies on `redact()` for security must understand what classes are accepted-out. This prevents future callers from treating redact() as a guarantee of literal-zero output.

3. **Recall/FP gate** — the interface MUST declare the envelope: `recall >= PROPOSED_RECALL_FLOOR` on the catchable set, `fp_rate <= PROPOSED_FP_CEILING`. This becomes the acceptance criterion for Phase-2.3. The envelope constants live in `harness.py` and are the single source of truth.

4. **Behavioral contracts (pinned by `test_harness_infra.py`):**
   - Idempotent: `redact(redact(p, s), s) == redact(p, s)` — asserted by `test_redact_is_idempotent`
   - Never raises on any input string — asserted by `test_redact_never_raises`
   - Pure / side-effect-free: no network, no file I/O — asserted by design (in-memory oracle + no-egress constraint)
   - Git SHAs MUST NOT be redacted — asserted by `test_git_sha_not_redacted_by_stub` (zero-tolerance sub-invariant)

### 7.2 CI gate (Phase-2.3 hard gate)

The harness must be wired into CI as a hard gate (block merge on failure):

```python
# ci/eval/redaction_fuzz/test_ci_gate.py (Phase-2.3 — do not create until the engine lands)
from core.redactor import redact
from ci.eval.redaction_fuzz.harness import run_harness, PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING

def test_redaction_gate_all_sinks():
    reports = run_harness(redact)
    for sink, report in reports.items():
        assert report.gate_pass(PROPOSED_RECALL_FLOOR, PROPOSED_FP_CEILING), (
            f"Redactor failed gate on {sink}: recall={report.recall:.1%} fp={report.fp_rate:.1%}\n"
            f"Leaks: {[r.sample.label for r in report.leaked_samples]}"
        )

def test_git_sha_never_redacted():
    """Zero-tolerance sub-invariant: git SHAs must pass through unreacted."""
    from ci.eval.redaction_fuzz.types import Sink
    sha = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
    for sink in Sink:
        assert sha in redact(sha, sink).lower(), (
            f"Git SHA was redacted on {sink} — breaks LanceDB version tagging (D-14)"
        )
```

---

## 8. Findings and escalation flags

### Confirmed (no escalation needed)

| Finding | Status |
|---|---|
| The three `AcceptedResidualClass` values match exactly the §18 enumeration | CONFIRMED |
| Git SHA zero-tolerance sub-invariant is testable and passes on the stub | CONFIRMED |
| The 20-char length floor for sub-20-char JSON is reasonable and aligns with C-11 | CONFIRMED |
| The oracle minimum detection length (8 chars) correctly classifies split-secret fragments as accepted residuals | CONFIRMED |
| The harness is delivery-agnostic (parametrized on `redact_fn`) | CONFIRMED |
| All three sinks are exercised independently and produce independent reports | CONFIRMED |

### Flag for orchestrator escalation

**FLAG-1: Oracle does not track encoding-aware forms.**

The current oracle uses literal substring matching. A secret encoded as base64, then that base64 string embedded in a YAML/JSON field, is correctly caught if the base64 value appears in the payload. However, if the real engine decodes base64 values before checking, the oracle may over-count catches (the base64 form is gone but the decoded form is already unembeddable). This is a Phase-2.3 calibration task, not a policy change. No new accepted-residual class needed — flag for the engine author.

**FLAG-2: JWT detection gap in the stub.**

JWTs appear in the catchable set (`prefix_token` class) but the stub only catches them via the Authorization header context. JWTs in other contexts (bare token fields, JSON values) are missed by the stub. This is a stub limitation only. The real engine must use a JWT shape matcher (`*.*.* base64url`) not just context-matching. Not a policy issue.

**FLAG-3: Corpus does not include secrets in binary files or compiled output.**

The current corpus covers text files. Binary files, compiled bytecode, or minified JS are out of scope for this spike. If the ingest pipeline touches these artifact types, a corpus extension is needed before Phase-2.3. Flag for orchestrator to assess ingest scope.

**FLAG-4: No sink-specific policy differentiation in the stub.**

§18 says the redactor "runs at all three sinks" but does not specify whether cloud_egress should apply stricter policy than persist. The stub treats all three identically. The Phase-1.5 interface freeze should decide: does the engine receive sink as a hint only, or does it apply strictly different rules (e.g. redacting more aggressively on cloud_egress)? This is a load-bearing API surface decision — escalate to orchestrator.

---

## 9. Stub baseline summary (harness validation run)

The stub is a minimal prefix-scanner — not the real engine. Its numbers prove the harness measures correctly.

| Metric | Stub result | Proposed gate |
|---|---|---|
| Recall (catchable set, all sinks) | **77.6%** (97/125) | ≥ 95% |
| FP rate (all sinks) | **0.0%** (0/26) | ≤ 5% |
| Git SHA FP rate | **0.0%** | 0.0% (hard) |
| Prefix-token recall | **90%** (46/51) | ≥ 95% |
| High-entropy KV recall | **63%** (27/43) | ≥ 95% |
| JSON-sensitive recall | **73%** (19/26) | ≥ 95% |
| Env dump recall | **100%** (5/5) | ≥ 95% |
| Accepted residuals (escaped) | **5/8** (expected) | N/A |

The stub fails the gate on recall, which is the correct behavior — it proves the gate is a real enforcement, not a rubber stamp.
