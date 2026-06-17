---
description: Run a named eval class. Usage: /eval [category]
allowed-tools: Bash, Read
argument-hint: "[category|all]"
---

Run the named eval class.

Argument: `$ARGUMENTS` — one of the categories below; `all` runs the full suite. Default: prompt the user to pick if no argument.

<!-- ▼ EXAMPLE BLOCK [id=eval-body]: /eval body — illustrative shape. Replace wholesale with this project's eval classes. ▼ -->

Argument values (example):
- `<eval-class-1>` — <one-line description>
- `<eval-class-2>` — <one-line description>
- `<eval-class-3>` — <one-line description>
- `all` — full eval suite

## Mapping

| Argument | Command |
|---|---|
| `<eval-class-1>` | `<test command for that class>` |
| `<eval-class-2>` | `<...>` |
| `<eval-class-3>` | `<...>` |
| `all` | `<...>` |

## Pre-flight checks

1. **Required env var set** — if not, abort with a clear message pointing at the setup doc.
2. **Target reachable** — quick health-check; if down, abort.
3. **Cost budget** — if a cost cap is set, check current spend; abort if at cap.

## Output

Per category:
- Test count + pass rate
- Verdict breakdown
- Cost: total + per-item average
- New findings / regression status

## Forbidden in this command

- **Running against any target other than the configured/allowlisted one.**
- **Auto-incrementing the cost cap.** If at cap, halt; surface to the user; the user decides.

<!-- ▲ END EXAMPLE BLOCK [id=eval-body] ▲ -->
