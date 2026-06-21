"""
Curated adversarial seed corpus — the hard cases.

These samples are HAND-CRAFTED to exercise:
  - Split secrets (across chunk/line boundaries)
  - Base64-encoded secrets
  - Secrets in code comments
  - Secrets in URLs
  - Secrets in env dumps
  - Accepted-residual edge classes (§18 / DECISIONS.md D-26/C-11)

SAFETY: All secrets are SYNTHETIC. No real credentials.
NETWORK: Zero network egress.
"""

from __future__ import annotations

from .types import AcceptedResidualClass, NonSecretSample, SecretClass, SecretSample

# ---------------------------------------------------------------------------
# Adversarial: Split secrets
# §18 "adversarial <20-char split" is an ACCEPTED RESIDUAL.
# These cases validate that we correctly classify splits as accepted residuals,
# NOT that the engine must catch them.
# ---------------------------------------------------------------------------

SPLIT_SECRET_CASES: list[SecretSample] = [
    SecretSample(
        label="split-sk-across-line",
        plaintext="sk-",
        secret_class=SecretClass.PREFIX_TOKEN,
        accepted_residual=AcceptedResidualClass.ADVERSARIAL_SHORT_SPLIT,
        is_adversarial=True,
        context=(
            "# config.py — continued from previous chunk\n"
            "key = (\n"
            '    "sk-"\n'
            '    "SyntheticFakeKey0000000000000000000000000000"  # synthetic\n'
            ")\n"
        ),
    ),
    SecretSample(
        label="split-akia-across-chunks",
        plaintext="AKIA",
        secret_class=SecretClass.PREFIX_TOKEN,
        accepted_residual=AcceptedResidualClass.ADVERSARIAL_SHORT_SPLIT,
        is_adversarial=True,
        context=(
            "# --- chunk boundary ---\n"
            "# ... [prior chunk omitted]\n"
            "aws_key = 'AKIA'\n"
        ),
    ),
    SecretSample(
        label="split-ghp-token-fragment",
        plaintext="ghp_SYNTH00000000",
        secret_class=SecretClass.PREFIX_TOKEN,
        accepted_residual=AcceptedResidualClass.ADVERSARIAL_SHORT_SPLIT,
        is_adversarial=True,
        context=(
            "# First 18 chars of a ghp_ token split at chunk boundary\n"
            "token_part1 = 'ghp_SYNTH00000000'\n"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Adversarial: Secrets in code comments
# These SHOULD be caught (they're in the catchable set, not splits).
# ---------------------------------------------------------------------------

COMMENT_EMBEDDED_CASES: list[SecretSample] = [
    SecretSample(
        label="comment-python-inline-sk",
        plaintext="sk-SyntheticKeyForTestingPurposesOnlyABCDEFG123456",
        secret_class=SecretClass.PREFIX_TOKEN,
        is_adversarial=True,
        context=(
            "def get_client():\n"
            "    # TODO: remove before merge — sk-SyntheticKeyForTestingPurposesOnlyABCDEFG123456\n"
            "    return client\n"
        ),
    ),
    SecretSample(
        label="comment-shell-hash-akia",
        plaintext="AKIAFAKEID0000000001",
        secret_class=SecretClass.PREFIX_TOKEN,
        is_adversarial=True,
        context=(
            "#!/bin/bash\n"
            "# Old key: AKIAFAKEID0000000001  -- rotated 2025-01\n"
            "aws s3 ls s3://my-bucket/\n"
        ),
    ),
    SecretSample(
        label="comment-javascript-docstring-token",
        plaintext="ghp_SynthTestToken00001122334455667788",
        secret_class=SecretClass.PREFIX_TOKEN,
        is_adversarial=True,
        context=(
            "/**\n"
            " * @example Authorization: token ghp_SynthTestToken00001122334455667788\n"
            " */\n"
            "function fetchData() {}\n"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Adversarial: Secrets in URLs
# ---------------------------------------------------------------------------

URL_EMBEDDED_CASES: list[SecretSample] = [
    SecretSample(
        label="url-github-pat-in-remote",
        plaintext="ghp_SyntheticGitRemoteToken0000000001",
        secret_class=SecretClass.PREFIX_TOKEN,
        is_adversarial=True,
        context="[remote \"origin\"]\n\turl = https://ghp_SyntheticGitRemoteToken0000000001@github.com/org/repo.git",
    ),
    SecretSample(
        label="url-db-password",
        plaintext="SyntheticDBPass99999",
        secret_class=SecretClass.HIGH_ENTROPY_KV,
        is_adversarial=True,
        context="DATABASE_URL=postgresql://admin:SyntheticDBPass99999@localhost:5432/mydb",
    ),
    SecretSample(
        label="url-query-param-token",
        plaintext="SynthQueryToken000000000000000000000001",
        secret_class=SecretClass.PREFIX_TOKEN,
        is_adversarial=True,
        context="https://api.example.com/webhook?token=SynthQueryToken000000000000000000000001&event=push",
    ),
]

# ---------------------------------------------------------------------------
# Adversarial: Base64-encoded secrets in various contexts
# ---------------------------------------------------------------------------

BASE64_CASES: list[SecretSample] = [
    SecretSample(
        label="base64-sk-in-yaml-config",
        # base64 of "sk-SyntheticBase64Key0000000000000000000"
        plaintext="c2stU3ludGhldGljQmFzZTY0S2V5MDAwMDAwMDAwMDAwMDAwMDAwMA==",
        secret_class=SecretClass.HIGH_ENTROPY_KV,
        is_adversarial=True,
        context=(
            "apiVersion: v1\n"
            "kind: Secret\n"
            "data:\n"
            "  api-key: c2stU3ludGhldGljQmFzZTY0S2V5MDAwMDAwMDAwMDAwMDAwMDAwMA==\n"
        ),
    ),
    SecretSample(
        label="base64-aws-secret-in-k8s",
        # base64 of "SyntheticAWSSecretKey0000000000000000000"
        plaintext="U3ludGhldGljQVdTU2VjcmV0S2V5MDAwMDAwMDAwMDAwMDAwMDAwMA==",
        secret_class=SecretClass.HIGH_ENTROPY_KV,
        is_adversarial=True,
        context=(
            "apiVersion: v1\nkind: Secret\nmetadata:\n  name: aws-creds\n"
            "data:\n"
            "  AWS_SECRET_ACCESS_KEY: U3ludGhldGljQVdTU2VjcmV0S2V5MDAwMDAwMDAwMDAwMDAwMDAwMA==\n"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Adversarial: Multi-line / env-dump mixed with legitimate content
# ---------------------------------------------------------------------------

ENV_DUMP_CASES: list[SecretSample] = [
    SecretSample(
        label="env-dump-mixed-legitimate",
        plaintext="SyntheticEnvSecretKeyForFuzzTesting0001",
        secret_class=SecretClass.ENV_DUMP,
        is_adversarial=True,
        context=(
            "# Captured from CI logs\n"
            "CI=true\nGITHUB_ACTIONS=true\nRUNNER_OS=Linux\n"
            "SECRET_KEY=SyntheticEnvSecretKeyForFuzzTesting0001\n"
            "GITHUB_WORKFLOW=test\nGITHUB_RUN_ID=1234567890\n"
            "GITHUB_SHA=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0\n"
        ),
    ),
    SecretSample(
        label="env-dump-aws-keys-in-printenv",
        plaintext="AKIAFAKEPRINTENV0001",
        secret_class=SecretClass.PREFIX_TOKEN,
        is_adversarial=True,
        context=(
            "$ printenv\n"
            "TERM=xterm-256color\nSHELL=/bin/bash\n"
            "AWS_ACCESS_KEY_ID=AKIAFAKEPRINTENV0001\n"
            "AWS_SECRET_ACCESS_KEY=SyntheticAWSSecretAccKey000000000000001\n"
            "HOME=/home/ubuntu\nPATH=/usr/local/bin:/usr/bin\n"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Accepted-residual edge cases
# These exercise the §18/C-11 enumerated boundary exactly.
# The engine is EXPECTED to pass these through.
# ---------------------------------------------------------------------------

ACCEPTED_RESIDUAL_CASES: list[SecretSample] = [
    # Git SHAs — must not be redacted
    SecretSample(
        label="git-sha-in-manifest-json",
        plaintext="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        secret_class=SecretClass.HIGH_ENTROPY_KV,
        accepted_residual=AcceptedResidualClass.GIT_SHA_HEX,
        is_adversarial=True,
        context='{"last_indexed_sha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0", "project": "nexus"}',
    ),
    SecretSample(
        label="git-sha-in-commit-log",
        plaintext="deadbeefcafe0000000000000000000000000001",
        secret_class=SecretClass.HIGH_ENTROPY_KV,
        accepted_residual=AcceptedResidualClass.GIT_SHA_HEX,
        is_adversarial=True,
        context="commit deadbeefcafe0000000000000000000000000001\nAuthor: Dev <dev@example.com>",
    ),
    SecretSample(
        label="git-sha-kv-ingest-context",
        plaintext="f8e7d6c5b4a3029100000000ffffeeeeddddcccc",
        secret_class=SecretClass.HIGH_ENTROPY_KV,
        accepted_residual=AcceptedResidualClass.GIT_SHA_HEX,
        is_adversarial=True,
        context="ingestedFromSha=f8e7d6c5b4a3029100000000ffffeeeeddddcccc",
    ),
    # Sub-20-char JSON values — C-11 boundary
    SecretSample(
        label="sub20-json-changeme",
        plaintext="changeme",
        secret_class=SecretClass.JSON_SENSITIVE_VALUE,
        accepted_residual=AcceptedResidualClass.SUB_20_CHAR_JSON,
        is_adversarial=True,
        context='{"password": "changeme"}',
    ),
    SecretSample(
        label="sub20-json-19chars",
        plaintext="Synth19CharPass!!X",  # 18 chars < 20
        secret_class=SecretClass.JSON_SENSITIVE_VALUE,
        accepted_residual=AcceptedResidualClass.SUB_20_CHAR_JSON,
        is_adversarial=True,
        context='{"token": "Synth19CharPass!!X"}',
    ),
    SecretSample(
        label="sub20-json-exactly-20-CATCHABLE",
        # 20 chars — at or above the floor, should be caught
        plaintext="SynthPass20CharExact",
        secret_class=SecretClass.JSON_SENSITIVE_VALUE,
        accepted_residual=None,  # NOT an accepted residual — exactly at the floor
        is_adversarial=True,
        context='{"password": "SynthPass20CharExact"}',
    ),
]

# Additional non-secret look-alikes for corpus FP coverage
CORPUS_NON_SECRETS: list[NonSecretSample] = [
    NonSecretSample(
        label="git-sha-corpus-1",
        plaintext="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        reason="Git SHA — §18 accepted residual; must NOT be redacted",
    ),
    NonSecretSample(
        label="ulid-corpus",
        plaintext="01HWZX7ZX7ZX7ZX7ZX7ZX7ZX7Z",
        reason="ULID — structured ID, not a secret; allowlisted in the entropy filter",
    ),
    NonSecretSample(
        label="uuid-corpus",
        plaintext="550e8400-e29b-41d4-a716-446655440000",
        reason="UUID — structured random ID, not a secret",
    ),
    NonSecretSample(
        label="lorem-ipsum-high-entropy",
        plaintext="LoremIpsumDolorSitAmetConsecteturAdipiscingElit",
        reason="Long word with moderate entropy but no secret prefix/context — should not flag",
    ),
    NonSecretSample(
        label="hex-code-constant",
        plaintext="0xDEADBEEFCAFEBABE",
        reason="Hex constant in code — common, not a secret",
    ),
    NonSecretSample(
        label="base64-hello-world",
        plaintext="aGVsbG8gd29ybGQ=",
        reason="'hello world' in base64 — low-entropy content, not a secret",
    ),
]


def get_adversarial_corpus() -> list[SecretSample]:
    """Return the full curated adversarial corpus."""
    return (
        SPLIT_SECRET_CASES
        + COMMENT_EMBEDDED_CASES
        + URL_EMBEDDED_CASES
        + BASE64_CASES
        + ENV_DUMP_CASES
        + ACCEPTED_RESIDUAL_CASES
    )
