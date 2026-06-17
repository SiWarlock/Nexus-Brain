---
description: Run tests by class. cwd-aware. Usage: /run-tests [unit|integration|eval|all]
allowed-tools: Bash
argument-hint: "[unit|integration|eval|all]"
---

<!--
  TEMPLATE NOTE (delete when generating):
  Shown cwd-aware (two modes). For a SINGLE code area, delete "Step 0 — Detect
  mode" and the second mapping table. Fill the mapping table(s) with the
  project's real test commands per class/marker.
-->

Run tests by class. **cwd-aware** — runs the right test runner for whichever code area you're in.

Argument: `$ARGUMENTS` — see the mapping table(s) below. Default: `unit`.

## Step 0 — Detect mode

```bash
case "$(pwd)" in
  */app|*/app/*) MODE=the Tauri desktop app ;;
  *)                                                      MODE=the Python engine (core) ;;
esac
```

Announce the detected mode before running.

---

## the Python engine (core) mode mapping

| Argument | Command |
|---|---|
| (empty / `unit`) | `uv run pytest -m unit` |
| `integration` | `uv run pytest -m integration` |
| `all` | `uv run pytest` |
| <other class / marker> | `<command>` |

## the Tauri desktop app mode mapping

<!-- Delete this table for a single-code-area project. -->

| Argument | Command |
|---|---|
| (empty / `unit`) | `pnpm test:run` |
| `integration` / `e2e` | `pnpm test:run` |
| `all` | `pnpm test:run` |

If an argument names a class that belongs to the *other* mode, **ERROR** with a clear message naming the expected cwd.

---

<!-- ▼ EXAMPLE BLOCK [id=test-class-discipline-notes]: test-class discipline notes — OPTIONAL. Some test classes
     need preconditions (a live external dependency, an env var, a slow browser).
     The source project documented things like: "the live-attack class needs a
     reachable target + a bearer env var, else it skips with a clear message;"
     "the visual-smoke class is slow — run per-PR, not per-commit." Add the
     project's own per-class discipline notes here, or delete this block. ▼ -->
<!-- ▲ END EXAMPLE BLOCK [id=test-class-discipline-notes] ▲ -->

## Output

Report:
- Mode (which code area)
- Test count + class
- Pass / fail counts
- First ~20 lines of any failure
- Total duration
