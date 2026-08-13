# Argmax: Technical Architecture

Status: written before Step 0. Contains no scope, model count, or budget
numbers. Every place one is required is marked `[BLOCKED: Step 0]`.

Companion documents: `01-prd.md`, `03-security-and-access.md`,
`04-data-and-instrumentation-spec.md`. The PRD was deliberately absent until
the reasoning-model token cost was measured. That measurement now exists, from
stored data rather than from a paid probe, so `01-prd.md` covers sections 1 to
3 and the scope table. Its later sections stay unwritten until a scope row is
picked.

---

## 1. What this system is

A batch sampling and analysis pipeline. It draws N completions per problem
from a hosted model, stores every response verbatim, and computes
accuracy-versus-compute curves per problem, per model, per benchmark tier.

It is not a service. There is no UI, no user, no request path, no uptime
requirement. The only availability concern is that a long sampling run
survives interruption without losing paid-for samples.

Design pressure comes from three places, in this order:

1. Credits are scarce and non-refundable. Anything that causes a re-run is
   the most expensive class of bug.
2. The published predecessor lost three analyses permanently because data
   was not persisted at sample time. Instrumentation dictates architecture,
   not the reverse. See `04-data-and-instrumentation-spec.md`.
3. Confirmatory claims must be traceable to a script and a stored artifact.
   Prose describing an unimplemented computation reached the submitted
   draft of the last paper twice.

## 2. The single most important architectural decision

**Sample once at `M` per problem. Derive every N in the grid by subsampling
the stored samples. Never call the API again to get a smaller N.**

The object under study is the whole curve accuracy(N). A naive
implementation issues a fresh run per N, which multiplies cost by the size
of the grid. Subsampling makes the curve nearly free once the samples exist,
and makes it recomputable at any future grid without spending anything.

Two consequences that must be decided explicitly rather than by accident:

- **Ceiling effect.** Subsampling *without replacement* at `N == M` yields
  exactly one possible draw, so the curve's endpoint has no subsample
  variance and no CI. If a confidence interval at the largest N is wanted,
  `M` must exceed the largest grid point (for example `M = 96`, grid tops
  out at 64). The predecessor hit this and reported a bare point estimate.
  Decision `[BLOCKED: Step 0]`, but it must be a decision.
- **Draw scheme.** Subsample without replacement, which emulates "what if I
  had only drawn N". Sampling with replacement inflates agreement through
  duplicates. Record the choice in the run manifest; do not leave it to a
  library default.

## 3. Stage graph

```
  datasets/            (a) canonicalize
      |                    fixed problem ids, option order frozen, hashed
      v
  capability probe     (b) one sample per model, records what the API
      |                    actually returns (logprobs? usage fields?
      |                    reasoning split?) before any phase spends
      v
  sampler              (c) N=1 requests, bounded concurrency, resumable
      |                    writes append-only raw JSONL, never overwrites
      v
  raw store            (d) ground truth on disk; nothing downstream may
      |                    mutate it
      v
  extractor            (e) five-pass answer ladder, records which pass
      |                    fired and the character/token span
      v
  derived tables       (f) pure function of raw; `make derived` is
      |                    deterministic and idempotent
      v
  aggregator           (g) vote curves, gates, matched-compute comparisons
      |                    all persisted as artifacts, not printed
      v
  verdicts + tests     (h) falsification suite asserts stored verdicts
                           against pre-registered thresholds
```

Stages (e) through (h) never touch the network. This is enforceable and
should be enforced: analysis code imports no HTTP client.

## 4. Repository layout

```
argmax/
  README.md
  CLAUDE.md                     agent working rules, venv activation
  PREREGISTRATION.md            tag registry, one row per tag, see 8.3
  Makefile                      sample / derived / analyze / verify
  pyproject.toml + lockfile
  .env.example
  configs/
    models/<model_slug>.yaml    exact model string, params, pricing
    benchmarks/<bench>.yaml     source, version, filters, tier label
    phases/<phase>.yaml         what a phase runs; the unit of spend
  src/argmax/
    datasets/                   loading + canonicalization
    sampling/                   client, rate limiter, retry, ledger
    persist/                    writers, schema validation
    extract/                    five-pass ladder (copied, not imported)
    analysis/                   curves, gates, matched compute
    verdict/                    PASS/FAIL against prereg thresholds
  scripts/                      thin CLI wrappers only, no logic
  data/
    raw/exploratory/...
    raw/confirmatory/...
    derived/
  runs/<run_id>/manifest.json
  runs/ledger.jsonl
  notes/                        audits, including phase14b_token_audit.md
  tests/
    falsification.py            asserts verdicts AND thresholds
    fixtures/                   recorded API responses, offline CI
```

`src/` holds logic, `scripts/` holds argument parsing. The predecessor's
analysis lived in numbered phase scripts, which made "which script produced
this number" answerable only by reading all of them.

## 5. Component specs

### 5.1 Dataset layer

Responsibilities: load, filter, canonicalize, hash.

- Every problem gets a stable `problem_id` that is a function of content,
  not of row order. Row order changes when a dataset is re-released.
- **Option order is frozen at canonicalization and hashed.** Majority
  voting is over option letters. If option order shuffles between runs, the
  letters mean different things and the stored votes silently become
  incomparable.
- `n_options` is recorded per problem and asserted constant within a tier.
  This matters more than it looks: the chance floor of a majority vote is a
  function of the option count, so a 4-choice hard tier compared against a
  10-choice easy tier confounds difficulty with chance rate. Tier selection
  should hold `n_options` fixed across tiers where possible.
- `dataset_version_hash` = hash over the canonicalized problem set. Stored
  in every manifest. A changed hash invalidates comparison.

Tier candidates are a PRD question, but the architecture assumes three
tiers sharing one format. Note that the GPQA release contains supersets of
Diamond, which offers a mid tier with identical format, identical domains,
and lower difficulty by construction. That property is worth preserving in
whatever is chosen.

### 5.2 Capability probe

New component, no predecessor. Runs before any phase, costs approximately
one sample per model, and writes `configs/models/<slug>.capabilities.json`.

It records what the provider *actually returns* for that model:

- whether `logprobs` is honoured, and at what depth
- which fields appear in the `usage` block, including any separate
  reasoning-token count
- whether reasoning is returned in a dedicated field or inline in
  delimiters, and which delimiters
- whether `seed` is accepted
- the `model` string echoed back in the response

The sampler refuses to start a phase whose instrumentation requirements
exceed the recorded capabilities. This is the direct fix for the
predecessor's permanent loss of final-answer margin analysis: that hole was
discovered at analysis time, after the samples were paid for.

### 5.3 Sampler

- OpenAI-compatible chat completions endpoint.
- **`n=1` per request, always.** Requesting `n>1` returns one aggregated
  `usage` block for the whole batch, which destroys per-sample token
  accounting. Per-sample tokens are the entire point of Step 0 and the
  entire basis of the cost model. The extra request overhead is worth it.
- Bounded worker pool with a token-bucket rate limiter. Concurrency is
  configured per model, not global.
- Idempotency key:
  `sha256(model_string, param_hash, benchmark, problem_id, sample_index)`.
  Before issuing a call the sampler consults an index of existing keys and
  skips. Resume is "run the same command again".
- Spend guard: the runner computes a projected cost from the capability
  probe's token measurements before starting, adds realized spend from
  `runs/ledger.jsonl`, and aborts if the total would cross
  `ARGMAX_SPEND_CEILING_USD`. No ceiling set means refuse to run.

### 5.4 Persistence

Append-only JSONL, one file per (split, benchmark, model, param_hash,
problem):

```
data/raw/{split}/{benchmark}/{model_slug}/{param_hash}/{problem_id}.jsonl
```

`param_hash` is in the path so that a parameter change cannot contaminate
an existing sample set. This is cheap insurance against the single most
common silent-corruption mode in this kind of pipeline.

Raw files are never rewritten, never sorted, never deduplicated in place. A
corrupted trailing line from an interrupted write is tolerated by the
reader and reported, not repaired.

Derived tables are **JSON Lines**, rebuilt from raw by a pure function, with
rows sorted by a declared total order before writing. Deleting `data/derived/`
and running `make derived` must reproduce byte-identical files. There is a test
for this.

**Why not Parquet.** Parquet was specified here first and does not survive the
byte-identical requirement: writers embed a producer version string in the file
metadata and pad pages, so two builds of identical data differ in bytes for
reasons that have nothing to do with the data. Byte-identical is the stronger
invariant and it is the one kept, because it catches a second failure Parquet
equality would not: **nondeterministic row ordering**. A table whose rows are
correct but arrive in a different order every build is not a pure function of
raw, and a format-level comparison that normalises order would call it one.

The cost is real and accepted: JSON Lines is larger on disk and slower to scan
than Parquet, and columnar analysis loads the whole table. The trade is
recorded here rather than in a docstring, so the document and the code agree
without something in between mediating.

### 5.5 Extraction

The five-pass ladder is copied from the published repo verbatim, then
instrumented. Every extraction records which pass fired and the span it
matched. See `04-data-and-instrumentation-spec.md` section on extraction.

Extraction runs offline over stored raw text, so the ladder can be revised
and re-run at zero cost. It must never run inside the sampler.

### 5.6 Aggregator

Three artifact-producing computations, all persisted, none printed-only:

**Vote curves.** For each problem, model, and N in the grid: B seeded
subsample draws, majority vote per draw, mean correctness across draws,
plus a CI. Seed is derived from `(problem_id, model_slug, N, replicate)` so
results are reproducible and independent of iteration order.

**Gates.** For each gate (plurality agreement, mean token entropy, and any
new logprob-margin gate the retained arrays now permit), the per-problem
decision, the threshold used, and the resulting accuracy are written as
rows. The predecessor persisted only aggregates, which is why a paired
bootstrap for the "statistically indistinguishable" claim would have
required a full confirmatory re-run, and why the claim was cut instead.

**Matched-compute comparison.** A first-class function, not a description.
Given a total token budget T for a problem, it compares the achievable
strategies at that budget (many short samples, fewer long samples, one very
long sample) using stored `usage` data, and writes a row per comparison.
Every sentence in the paper that claims a compute-matched comparison must
resolve to a row here. The falsification suite asserts the rows exist
before the paper's claims are allowed to reference them.

## 6. Failure and retry semantics

Distinguish three outcomes that are easy to collapse and expensive to
collapse:

| Outcome | Meaning | Retry? | Counted as |
|---|---|---|---|
| `answered` | visible answer extracted | no | data |
| `no_answer_visible` | completed, no parseable answer | no | data, `is_correct = null` |
| `truncated_no_answer` | `finish_reason == length`, no visible answer | no | data, and a first-class result |
| `api_failure` | transport, 5xx, exhausted retries | yes, then recorded | not data |

**Truncation is a measurement, not an error.** The phase 14b probe was
abandoned because reasoning models exhausted the output budget on hidden
chain of thought. That is a finding about the cost model, and it must be
counted, flagged, and reported, never retried into oblivion and never
scored as incorrect without the flag travelling alongside.

`is_correct` is nullable and is never coerced to `false` for a missing
answer. Whether unanswered samples are excluded or scored as wrong is a
pre-registered analysis decision, made once, applied everywhere, and
recorded in the manifest.

Retries: exponential backoff with jitter on 429 and 5xx, honouring
`Retry-After`, capped attempts. Every attempt increments `attempt_count` on
the eventual record. A sample that exhausts retries is written as an
`api_failure` record so the gap is visible rather than inferred from a
count mismatch.

## 7. Reproducibility guarantees

State these precisely, because over-claiming here is a reviewer target.

**Not guaranteed:** bit-identical generations. Hosted inference is
non-deterministic across batching and hardware even at fixed seed. `seed`
is sent and recorded, never relied upon.

**Guaranteed:**

1. Every number in the paper is recomputable from the stored raw responses
   with no network access.
2. `make derived && make analyze` from a clean checkout at the tagged
   commit, against the released raw store, reproduces every derived table
   and figure byte-identically.
3. Every manifest records: git SHA, dirty flag, lockfile hash,
   `dataset_version_hash`, model string requested and returned, full
   parameter set, capability probe id, pricing snapshot id, prereg tag.
4. Confirmatory analysis refuses to run from a dirty working tree, and
   refuses to run without a prereg tag recorded in the manifest.

### 7.1 `max_tokens` is an experimental treatment, not a config value

It looks like an infrastructure setting and it is not one. The cap decides
which samples produce a visible answer at all, so it decides which samples
vote, and therefore it moves accuracy directly. A curve measured at one cap
and a curve measured at another are measurements of two different
experiments.

**The criterion is the answer rate, not the cap.** An earlier version of this
section made equal caps the test of comparability. That is wrong, and wrong in
the direction that matters: a non-reasoning model at 16,384 tokens truncates
near zero while `MiniMaxAI/MiniMax-M2.7` at the same cap truncates 35.1
percent. The shared cap yields two pools of different kinds, one nearly
complete and one missing a third of its samples, and comparing accuracies
across them compares populations rather than policies. Equal caps are neither
necessary nor sufficient. The rule:

> **Two conditions are comparable when their answer rates match, or when the
> result is shown to be insensitive to the difference between them.** A
> constant cap is the mechanism that usually produces matching answer rates.
> It is not the criterion, and it does not produce them across models that
> differ in how much they think.

"Shown to be insensitive" means shown, not asserted: recompute the comparison
on the subpopulation where the rates do match, or on a common floor, and
report both. The mechanism is in `04-data-and-instrumentation-spec.md` section
4.1, and section 4 makes `answer_rate` a required field on the problem record
precisely so this test can be applied rather than assumed.

That the cap is a treatment still binds the runner and the analysis both:

1. **`max_tokens` is held constant across every condition within a study.**
   Every model, every tier, every arm, every N in the grid. If two models
   cannot share a cap, they are not in the same study, and saying so is
   cheaper than discovering it in the comparison.
2. **It is recorded in the run manifest** as part of the full parameter set
   (guarantee 3), per model, and it is in `param_hash`, so a cap change lands
   in a different storage path and cannot contaminate an existing sample set.
3. **Curves measured at different caps are never compared,** not across
   models, not across tiers, not against the predecessor's published numbers,
   and not against an earlier phase of this project. A comparison that spans
   a cap change is a finding about the cap.
4. A cap change is therefore a **registration change**, not an
   implementation choice. It gets a new prereg tag and a new row in
   `PREREGISTRATION.md` stating what was compared before and what may be
   compared after.

Binding 3 is the conservative form of the rule above: a cap change is one way
to move the answer rate, so a comparison spanning one is refused outright
rather than argued. **The converse does not hold.** Holding the cap fixed does
not license a comparison, because two models at one cap can still answer at
different rates, and that case has to be settled on the rates themselves.
`notes/max_tokens_estimate.md` shows how far apart the rates can be: at one
cap and one benchmark tier, the fraction of samples that answer at all is a
property of the problem, and 8 of 47 problems produced no answer whatsoever.

### 7.2 A pooled accuracy publishes the heterogeneity it pools over

Same shape as the answer-rate rule, and for the same reason: a number that
averages over a mixture looks exactly like a number that does not.

**Any accuracy pooled across problems is published with a measure of the
per-problem heterogeneity it pools over.** The measure is the ratio of the
observed between-problem variance to what a homogeneous null produces, where
the null resamples each problem's successes binomially at the pooled rate with
that problem's own sample count. A ratio near 1 means the pooled number
describes a population. A large ratio means it describes an average over groups
that differ, and the reader needs to know which.

This is not hypothetical on this benchmark. Two per-problem properties are
already measured in the predecessor's stored data:

| Property | Ratio to its null | Source |
|---|---|---|
| per-problem accuracy, Qwen2.5-7B | **25.5x** | `notes/mixture_premise.md` |
| per-problem accuracy, Llama-3-8B-Lite | **17.1x** | same |
| completion-length mode membership | **5.65x** | `notes/max_tokens_estimate.md` s7 |

At 25.5x, a pooled accuracy of 0.34 is an average over a component the model
almost never gets right and a component it usually does, and the pooled figure
alone tells the reader neither thing. Pooling stays allowed. Pooling silently
does not.

The rule covers any statistic computed by pooling problems, including backfire
rates and gate captures, because the argument is about composition rather than
about accuracy specifically.

**Not yet implemented.** The field and the test that enforces it follow the
`answer_rate` precedent in `04-data-and-instrumentation-spec.md` sections 4.1
and 9.1, and neither exists at the time of writing. This section records the
requirement so that the implementation is owed rather than optional.

## 8. Pre-registration and verification

### 8.1 Split discipline

Exploratory and confirmatory are separate directory trees, not a boolean
flag. Analysis entry points require `--split` with no default, because a
default is how the wrong split gets used silently.

### 8.2 Order of operations

Explore, freeze hypotheses and thresholds, tag, then sample and analyze the
confirmatory split. PASS/FAIL is decided on confirmatory only.

### 8.3 Tag naming

The predecessor ended with `pre-pilot-v6.0` and `backfire-prereg-v1.0`
covering different hypothesis sets, and nearly cited the wrong one in the
paper. Rules:

- Format: `argmax-prereg-<phase>-v<major>.<minor>`, no exceptions.
- `PREREGISTRATION.md` carries one row per tag: tag, date, commit, which
  hypotheses it covers, which analyses may cite it.
- Tags are protected against deletion and force-push. See
  `03-security-and-access.md`.

### 8.4 Falsification suite

`tests/falsification.py` asserts stored verdicts against pre-registered
thresholds, **and asserts the threshold values themselves**. A regenerated
result whose threshold was quietly edited must fail loudly rather than pass
against a moved line.

A test may fail by design when a hypothesis is genuinely falsified. Such
tests are marked with the hypothesis id and a comment stating that red is
the expected state and why. The predecessor's `test_h3` is the model here.

Additional required tests:

- schema conformance for every raw record
- recomputability: derived tables rebuild identically from raw
- no-network: analysis modules import no HTTP client
- claim coverage: each pre-registered claim id maps to at least one stored
  artifact row

## 9. Decisions blocked on Step 0

| Decision | Unblocked by |
|---|---|
| `max_tokens` per reasoning model | p95 output tokens, truncation curve |
| `M` (samples stored per problem) and the N grid | cost per sample |
| Number of models, number of tiers | total cost envelope |
| Whether reasoning models enter at all | reasoning cost multiplier |
| Full-logprob retention for reasoning models | mean output length, see doc 4 |

Write none of these into any document until the audit or the fallback probe
returns real numbers. Guessing the token cost is precisely how the
predecessor acquired a pooled-versus-confirmatory mismatch that cost four
revision rounds.
