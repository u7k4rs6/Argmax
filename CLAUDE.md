# Working rules for agents in this repo

This file is binding on Claude Code and any similar agent operating here. It
is referenced by `files/03-security-and-access.md` section 8.

## Hard prohibitions

These are not stylistic preferences. Each maps to an unrecoverable failure.

1. **Never print environment variables.** No `print(os.environ)`, no `env`, no
   `echo $TOGETHER_API_KEY`, not in a script, not in a shell command, not to
   debug. A key printed into a transcript or a notebook output is a leaked
   key.
2. **Never commit anything under `data/` or `runs/`.** They are gitignored;
   do not add exceptions, do not `git add -f`.
3. **Never move, delete, or force-push a tag matching `argmax-prereg-*`.** A
   pre-registration tag that can be moved is not a pre-registration. If a tag
   is wrong, cut a new one with a new version and record why in
   `PREREGISTRATION.md`.
4. **Never issue an API call without an explicit instruction naming the
   phase.** Sampling spends non-refundable credits. "Try it and see" is not an
   instruction.
5. **Never commit benchmark question text, option text, or explanations.**
   Ids, hashes, domain labels, and answer keys as letters only. See
   `files/03-security-and-access.md` section 5.
6. **Never write a number into a `[BLOCKED: Step 0]` field.** Not a guess, not
   a placeholder that looks plausible, not "a reasonable default". If a value
   is needed to make code run, raise `StepZeroBlocked` instead.

## Environment

```sh
. .venv/bin/activate
```

Always activate the venv before running anything. If it does not exist:
`python -m venv .venv && . .venv/bin/activate && pip install -e '.[dev]'`.

## Where code goes

- `src/argmax/` holds all logic.
- `scripts/` holds argument parsing and nothing else. If you are writing a
  computation in `scripts/`, move it to `src/`.
- The predecessor's analysis lived in numbered phase scripts, which made
  "which script produced this number" answerable only by reading all of them.
  Do not reintroduce that pattern.

## Analysis code has no network

Modules under `src/argmax/analysis/`, `src/argmax/extract/`,
`src/argmax/verdict/`, and `src/argmax/persist/` must not import an HTTP
client (`httpx`, `requests`, `openai`, `aiohttp`, `urllib.request`). There is
a test that enforces this: `tests/test_no_network.py`. Do not weaken it.

## Raw data is immutable

Files under `data/raw/` are append-only. Never rewrite, sort, deduplicate in
place, or "fix" one. A corrupted trailing line from an interrupted write is
tolerated by the reader and reported, not repaired.

Derived tables are a pure function of raw. Deleting `data/derived/` and
running `make derived` must reproduce byte-identical files.

## Absence is data

Truncated, unparseable, and failed samples get records, not omissions.
Truncation is a measurement, not an error — it is the finding that killed the
phase 14b probe, and it must be counted and flagged, never retried into
oblivion and never silently scored as incorrect.

## Before proposing a change to a stored field

Read `files/04-data-and-instrumentation-spec.md` first. Every field in the
`sample` record exists because its absence cost the predecessor a specific
analysis. Removing one, or selecting a subset of a verbatim block like
`usage_raw` at write time, is how defect 1 happened.

Adding a field is cheap. Bump `SCHEMA_VERSION` and make readers branch on it.

## Claims and tests

Any sentence in a draft that describes a compute-matched comparison must carry
a `claim_id` that resolves to rows in the `budget_matched` table. The
falsification suite fails when a registered `claim_id` has zero backing rows.
Do not register a claim you have not produced rows for.

A failing test in `tests/falsification.py` may be correct — a hypothesis can
be genuinely falsified. Such tests are marked with the hypothesis id and a
comment stating that red is the expected state and why. Do not "fix" one
without reading that comment.
