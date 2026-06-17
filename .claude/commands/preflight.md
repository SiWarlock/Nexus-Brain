---
description: Full preflight gate — sync deps, lint, format-check, type-check, test.
allowed-tools: Bash, Read
argument-hint: ""
---

<!--
  TEMPLATE NOTE (delete when generating):
  This command is shown CWD-AWARE (two modes — one per code area). If the project
  has a SINGLE code area, delete "Step 0 — Detect mode" and the "Mode B" block,
  and keep just one linear gate. If it has two areas, fill both modes. Each mode's
  steps are the project's real quality commands for that area.
-->

Run the full quality gate for the current code area. **cwd-aware** — runs the right toolchain for whichever code area you're in.

Stops on first failure. Reports per-step pass/fail with the first ~20 lines of error output. Does NOT auto-fix on failure.

## Step 0 — Detect mode

```bash
case "$(pwd)" in
  */app|*/app/*) MODE=the Tauri desktop app ;;
  *)                                                      MODE=the Python engine (core) ;;
esac
```

Announce the detected mode to the user before running steps. If the mode looks wrong for the user's intent, surface the cwd and ask before proceeding.

---

## the Python engine (core) mode (cwd is `core/` or repo root)

### Step 1 — Sync dependencies
```bash
uv sync
```

### Step 2 — Lint
```bash
uv run ruff check .
```

### Step 3 — Format check
```bash
uv run ruff format --check .
```

### Step 4 — Type check
```bash
uv run mypy core
```

### Step 5 — Test
```bash
uv run pytest
```

---

## the Tauri desktop app mode (cwd is `app/` or below)

<!-- Delete this whole section for a single-code-area project. -->

### Step 1 — Sync dependencies
```bash
pnpm install
```

### Step 2 — Lint
```bash
pnpm lint
```

### Step 3 — Format check
```bash
pnpm format --check
```

### Step 4 — Type check
```bash
pnpm typecheck
```

### Step 5 — Test
```bash
pnpm test:run
```

### Step 6 — Build
```bash
pnpm tauri build
```

<!-- Keep a build step only if the area's build catches a class of errors the
     type-checker alone doesn't (e.g. a frontend production build). -->

---

## Final step (both modes) — forbidden-pattern warn-grep (NON-BLOCKING)

The area's `CLAUDE.md` `[id=forbidden-patterns]` region may carry a ` ```forbidden-patterns ` fenced block (one bare `grep -E` pattern per line; `#` lines are comments — the machine-readable side of banked lessons). Grep the **staged diff's added lines** against it:

```bash
pats=$(awk '/^```forbidden-patterns/{f=1;next} /^```/{f=0} f' <area>/CLAUDE.md | grep -vE '^[[:space:]]*(#|$)' || true)
if [ -n "$pats" ]; then
  git diff --staged -U0 | grep '^+' | grep -nE -f <(printf '%s\n' "$pats") || true
fi
```

- **No block / no pattern lines ⇒ silent skip** (the template ships comments only).
- **Any hit ⇒ a WARN line in the output — never a failure.** Name the matched pattern + the forbidden-pattern rule it enforces; the implementer fixes it or flags it at Step 9 with justification. This step exists so a banked lesson bites mechanically even in a session that never loaded its prose.

---

## Output

**Success:**
> "Preflight clean (<mode>): lint ✓ + format ✓ + types ✓ + N tests pass"

**Failure (either mode):**
> "Preflight failed at Step N: <step name>"
> <first ~20 lines of error output>

## Forbidden in this command

- **Auto-fixing on failure.** The gate exists to catch problems; fixing them silently defeats the purpose.
- **Modifying baseline / ignore files to suppress failures.** Fix the underlying error.
- **Skipping steps.** Run in order; stop on first failure.
- **Cross-mode contamination.** Don't run one area's toolchain from another area's cwd. If cwd is wrong, fail loud with a clear message.
