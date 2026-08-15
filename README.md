# Argmax

A batch sampling and analysis pipeline. It draws `M` completions per problem
from a hosted model, stores every response verbatim, and computes
accuracy-versus-compute curves per problem, per model, per benchmark tier.

It is not a service. There is no UI, no user, no request path, no uptime
requirement. The only availability concern is that a long sampling run
survives interruption without losing paid-for samples.

## Design documents

Read these before changing anything. They are the specification; this code is
an implementation of them.

| Document | Covers |
|---|---|
| `files/01-prd.md` | why this project exists, what it may compare against, the scope table |
| `files/02-technical-architecture.md` | stage graph, components, reproducibility, pre-registration |
| `files/03-security-and-access.md` | credentials, spend controls, benchmark data handling, release |
| `files/04-data-and-instrumentation-spec.md` | every stored field, retention policy, validation |

The PRD was deliberately absent until the reasoning-model token cost was
measured. Step 0 answered that from the predecessor's stored data, so
`01-prd.md` now carries sections 1 to 3 and the scope table. **No scope row has
been picked**, and its hypotheses, thresholds and success criteria stay
unwritten until one is. See "Step 0" below.

## Status

Pre-Step 0. **No paid sampling has run and none should run yet.**

Every quantity that costs money is undecided and is marked `[BLOCKED: Step 0]`
in the configs and the code:

- `max_tokens` per reasoning model
- `M` (samples stored per problem) and the N grid
- number of models, number of tiers
- whether reasoning models enter at all
- full-logprob retention for reasoning models

Step 0 is an audit of the abandoned phase 14b probe for real token counts. If
the audit cannot answer them, a paid fallback probe is required, and that
probe doubles as the capability probe. Writing a guessed number into any of
these fields is the specific mistake this repo is built to prevent.

## The one architectural decision to understand first

**Sample once at `M` per problem. Derive every N in the grid by subsampling
the stored samples. Never call the API again to get a smaller N.**

The object under study is the whole curve accuracy(N). Issuing a fresh run per
N multiplies cost by the size of the grid. Subsampling makes the curve nearly
free once the samples exist, and recomputable at any future grid for nothing.

Subsampling is **without replacement**, seeded from
`(problem_id, model_slug, N, replicate)`, and the scheme is recorded in the
run manifest rather than left to a library default.

## Layout

```
argmax/
  files/                    the design documents
  PREREGISTRATION.md        tag registry, one row per tag
  Makefile                  probe / sample / derived / analyze / verify
  configs/
    models/                 exact model string, params, pricing snapshot
    benchmarks/             source, version, filters, tier label
    phases/                 what a phase runs; the unit of spend
  src/argmax/
    datasets/               loading + canonicalization
    sampling/               client, rate limiter, retry, ledger, spend guard
    persist/                writers, paths, schema validation
    extract/                five-pass ladder (copied, not imported)
    analysis/               curves, gates, matched compute
    verdict/                PASS/FAIL against prereg thresholds
  scripts/                  thin CLI wrappers only, no logic
  data/raw/{exploratory,confirmatory}/
  data/derived/
  runs/
  notes/
  tests/
```

`src/` holds logic, `scripts/` holds argument parsing. If a script contains a
computation, it is in the wrong place.

## Setup

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pre-commit install
cp .env.example .env      # then fill in TOGETHER_API_KEY
```

The key must be a **dedicated Argmax key**, not the one used with
`self-consistency-backfire`. See `files/03-security-and-access.md` section 2.1.

## Running

```sh
make probe   MODEL=<slug>          # capability probe, ~1 sample, run before any phase
make sample  PHASE=<phase> SPLIT=<split>
make derived                       # pure function of raw; deterministic, idempotent
make analyze SPLIT=<split>
make verify                        # falsification suite

make leakcheck QUESTIONS=<gated source> TARGET=<path> [README=<path>]
                                   # before publishing anything from the raw store
```

`make leakcheck` exists because the ban on committing question text is not
sufficient on its own: raw responses echo the prompt, so a completion that
restates the question *is* question text. It reduces the gated source to
hashed n-grams, scans the release tree for them, and reports paths and line
numbers only, never the matching text. A file it cannot read is reported as
unscanned and fails the check, because "no hits" and "no evidence" are
different claims.

`make sample` refuses to start unless `ARGMAX_SPEND_CEILING_USD` is set in the
environment. There is no default ceiling, because a default becomes the real
limit.

Analysis entry points require `--split` with no default. A default is how the
wrong split gets used silently.

## What must never happen

- Question or option text committed to this repo. See
  `files/03-security-and-access.md` section 5. GPQA's authors ask that
  examples not appear in plain text online.
- An `argmax-prereg-*` tag moved, deleted, or force-pushed.
- Anything under `data/` or `runs/` committed.
- A confirmatory analysis run from a dirty working tree, or without a prereg
  tag in the manifest. Both are refused in code.
- `is_correct` coerced to `false` because no answer was extracted. It is
  nullable and stays null.

## Reproducibility, stated precisely

**Not guaranteed:** bit-identical generations. Hosted inference is
non-deterministic across batching and hardware even at fixed seed. `seed` is
sent and recorded, never relied upon.

**Guaranteed:** every number is recomputable from the stored raw responses
with no network access; `make derived && make analyze` from a clean checkout
at the tagged commit reproduces every derived table byte-identically; every
manifest records git SHA, dirty flag, lockfile hash, dataset hash, model
strings requested and returned, full parameters, capability probe id, pricing
snapshot id, and prereg tag.

## Archived artifacts

Two Zenodo records, published 2026-08-16, supplementing arXiv:2608.11403 and
its v2. The v1 paper is read from `paper/backfire_preprint.pdf`; the v2 LaTeX
source is `paper/tex/backfire_preprint.tex`.

| record | DOI | access | contents |
|---|---|---|---|
| **Derived data** | [10.5281/zenodo.21933418](https://doi.org/10.5281/zenodo.21933418) | **Open**, CC BY 4.0 | derived tables for both models, spend ledger, run manifests, pre-registration registry, provenance digests. No model completions, no benchmark question text. Reproduces every number in the paper. |
| **Raw sample store** | [10.5281/zenodo.21933422](https://doi.org/10.5281/zenodo.21933422) | **Restricted, request-access** | per-sample records with verbatim completions, usage blocks and depth-5 logprob arrays |

**The restricted record is not open data.** It is gated on the same terms as
GPQA, because model chains of thought restate gated benchmark items: a
pre-release leakage check over that tree reports 20,376 matched n-grams. The
leak is authored by the model, not by the recording pipeline, which stores a
prompt hash and never a prompt. Request access only if you already hold GPQA
access.

Both records carry the GPQA canary string and attribute GPQA (Rein et al.,
2023, arXiv:2311.12022, CC BY 4.0).
