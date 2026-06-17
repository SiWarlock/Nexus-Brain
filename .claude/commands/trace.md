---
description: Pull a structured trace for a given id and format it for inspection. Usage: /trace <id>
allowed-tools: Bash, Read, Grep
argument-hint: "<id>"
---

Pull the structured trace for a given id and format the lifecycle for inspection.

Argument: `$ARGUMENTS` — the id of the run / request to inspect.

<!-- ▼ EXAMPLE BLOCK [id=trace-body]: /trace body — from the source project. Replace wholesale. ▼ -->

## Procedure

1. **Local lookup first** — grep local structured-log output for the id:
   ```bash
   grep "<id-field>\":\"$ARGUMENTS\"" <local-log-path> | head -200
   ```

2. **Fallback to the observability platform** — if not in local logs, fetch from the configured observability platform.

3. **Format the lifecycle** for human inspection:
   ```
   id: <id>
   Lifecycle:
     [t=0ms]   <stage>: <summary>
     [t=Xms]   <stage>: <summary>
     [total=Tms] completed
   Cost / resource summary:
     <per-stage cost or resource breakdown>
   Final outcome:
     <terminal state>
   ```

4. **On a non-OK final status** — surface the failure: which stage emitted it, what the rest of the system saw, whether it was a cascading failure.

## Output

A single formatted trace block + (optionally) the raw tail if the user requests a deep dive.

## Forbidden in this command

- **Fetching traces for ids outside this project's trace format.** If an id doesn't match, say so; don't try to interpret a foreign trace.
- **Inferring stage output when traces are missing.** If a span is absent, report "no trace" — don't fabricate.

<!-- ▲ END EXAMPLE BLOCK [id=trace-body] ▲ -->
