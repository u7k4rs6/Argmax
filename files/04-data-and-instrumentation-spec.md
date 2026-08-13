# Argmax: Data and Instrumentation Spec

Replaces the frontend spec. There is no UI. This is the highest-value
document in the set, because everything it fails to specify becomes
permanently unrecoverable the moment credits are spent.

Status: written before Step 0. Retention thresholds that depend on measured
output length are marked `[BLOCKED: Step 0]`.

---

## 0. Why this document exists

Three defects in the published predecessor trace to instrumentation
decisions that were never written down:

1. Only a **mean entropy scalar** was retained instead of per-token logprob
   arrays. Final-answer margin analysis was permanently foreclosed and had
   to be disclosed as a limitation.
2. **Per-problem gate outcomes were never persisted.** A paired bootstrap
   supporting the "statistically indistinguishable" claim would have needed
   a full confirmatory re-run, so the claim was deleted instead.
3. A **matched-compute baseline was never implemented**, yet prose
   describing one reached the submitted draft. Every real comparison was
   flat N=64.

None of the three was a coding error. Each was a field that nobody decided
to write. This document is the decision.

## 1. Principles

1. **Store raw, derive later.** Any field computable from a stored raw
   response is a derived field and may be recomputed at will. Any field not
   stored is gone.
2. **Storing raw is cheap, except when it is not.** See section 7: for
   reasoning models, per-token logprobs over long hidden chains are large
   enough that "keep everything" needs a stated policy rather than an
   assumption.
3. **Nothing is derived-only.** A test asserts that every derived table
   rebuilds identically from raw.
4. **Every claim maps to a field.** Before a hypothesis is pre-registered,
   name the fields that will decide it. If no field decides it, either add
   the field or drop the hypothesis. This is the mechanism that prevents
   defect 3 from recurring.
5. **Absence is data.** Truncated, unparseable, and failed samples get
   records, not omissions.

## 2. Request-side requirements

Instrumentation starts at the request, not at the writer.

| Requirement | Reason |
|---|---|
| `n = 1` per request | `usage` is aggregated across `n`, destroying per-sample token accounting |
| `logprobs` requested at the deepest supported level | defect 1; margin analysis needs per-token values |
| `max_tokens` set explicitly per model | truncation must be a controlled variable, not a provider default |
| `seed` sent and recorded | best effort only, never relied on |
| `stop` sequences empty unless justified | a stop sequence silently truncates the answer and looks like a short completion |
| Full response object retained | fields the provider adds later are then already captured |

**Capability probe first.** Before any phase, one sample per model records
what the API actually returns for that model: whether logprobs arrive, at
what depth, which `usage` fields exist, whether reasoning comes back in a
dedicated field or inline in delimiters, and whether `seed` is honoured.
Stored at `configs/models/<slug>.capabilities.json`. The sampler refuses to
start a phase whose required fields are not in the probe.

This is the fix for defect 1. That hole was found at analysis time, after
the money was spent. A probe costs one sample.

## 3. The `sample` record

One JSON object per line, per API call. Fields marked **R** are required
and the schema test fails without them.

### 3.1 Identity and provenance

| Field | Type | Notes |
|---|---|---|
| `schema_version` **R** | int | bump on any change; readers branch on it |
| `sample_key` **R** | str | sha256 over model, params, benchmark, problem, index |
| `run_id` **R** | str | joins to `runs/<run_id>/manifest.json` |
| `split` **R** | enum | `exploratory` or `confirmatory`, no default |
| `benchmark` **R** | str | |
| `benchmark_version_hash` **R** | str | canonicalized problem set hash |
| `problem_id` **R** | str | content-derived, stable across releases |
| `problem_hash` **R** | str | includes frozen option order |
| `sample_index` **R** | int | 0-based within the problem |

### 3.2 Request

| Field | Type | Notes |
|---|---|---|
| `model_requested` **R** | str | exact provider string |
| `model_returned` **R** | str | echoed by the API; assert equal, record if not |
| `param_hash` **R** | str | over the full parameter set |
| `temperature`, `top_p`, `max_tokens`, `seed`, `stop` **R** | | stored individually as well as in the hash |
| `prompt_hash` **R** | str | prompt text is not stored, see doc 3 section 5 |
| `prompt_template_id` **R** | str | version the template; a reworded prompt is a different experiment |
| `request_timestamp_utc` **R** | str | |
| `latency_ms` | int | |
| `attempt_count` **R** | int | 1 unless retried |

### 3.3 Response, verbatim

| Field | Type | Notes |
|---|---|---|
| `api_response_id` | str | provider-side id for support tickets |
| `raw_text` **R** | str | the complete completion, unmodified, unstripped |
| `finish_reason` **R** | str | provider value, not normalized |
| `usage_raw` **R** | object | **the entire usage block, verbatim**, not selected fields |
| `logprobs_raw` | object | provider structure, verbatim; null only if the probe says unsupported |
| `response_extras` | object | any field the provider returned that this schema does not name |

`usage_raw` and `response_extras` exist so that a provider adding a
reasoning-token counter next month is captured without a schema change.
Selecting fields at write time is how defect 1 happened.

### 3.4 Reasoning split (reasoning-native models)

| Field | Type | Notes |
|---|---|---|
| `reasoning_text` | str | hidden chain, if separable |
| `answer_text` | str | visible remainder |
| `split_method` **R** | enum | `api_field`, `delimiter`, `none` |
| `split_ok` **R** | bool | false when the opening delimiter appears with no close, which is exactly the truncated-mid-thought case |
| `reasoning_tokens` | int | from `usage_raw` if the provider reports it, else null |
| `reasoning_tokens_est` | int | from the logprob token array if present, else tokenizer estimate; the estimation method is recorded, never silently swapped |

Getting this split right is the whole reason Step 0 exists. The phase 14b
probe died on truncation before a visible answer, and the token budget
needed to avoid that is the number the cost model turns on.

### 3.5 Truncation and outcome

| Field | Type | Notes |
|---|---|---|
| `truncated` **R** | bool | `finish_reason == "length"` |
| `hit_ceiling` **R** | bool | `completion_tokens >= max_tokens`; kept separate because providers disagree about `finish_reason` |
| `outcome_class` **R** | enum | `answered`, `no_answer_visible`, `truncated_no_answer`, `api_failure` |
| `error_type`, `error_message` | str | null unless `api_failure` |

### 3.6 Extraction (written by the offline extractor)

| Field | Type | Notes |
|---|---|---|
| `extracted_answer` | str | canonical option letter, null if none |
| `extraction_pass` **R** | int | which of the five ladder passes fired, null if all failed |
| `answer_span_chars` | [int, int] | offsets into `raw_text` |
| `answer_span_tokens` | [int, int] | offsets into the logprob token array |
| `extractor_version` **R** | str | the ladder will be revised; old records must stay interpretable |
| `is_correct` | bool or null | **null when no answer was extracted; never coerced to false** |

`answer_span_tokens` is the field that makes final-answer margin analysis
possible at all. Per-token logprobs without a span pointing at the answer
token are an undifferentiated array. Storing the span is what turns defect
1 into a solved problem rather than a partially solved one.

### 3.7 Cost

| Field | Type | Notes |
|---|---|---|
| `pricing_snapshot_id` **R** | str | joins to the dated price table |
| `cost_usd_est` **R** | float | from `usage_raw` and the snapshot |

## 4. The `problem` record (derived, per problem per model)

Rebuildable from samples. Persisted anyway, because it is what analysis and
figures read.

- `problem_id`, `benchmark`, `tier`, `domain`, `subdomain`, `n_options`,
  `correct_option`
- `n_samples_stored`, `n_answered`, `n_truncated`, `n_no_answer`,
  `n_api_failure`
- `answer_rate` **R**, `n_answered / n_samples_stored`. **Every reported
  accuracy carries its answer rate alongside it**, in the same table, the
  same figure panel and the same sentence. An accuracy without one is not
  reportable. See the mechanism below.
- `single_sample_accuracy`, the mean over answered samples, with the
  unanswered-sample policy recorded as a field, not assumed
- `vote_accuracy[N]` for every N in the grid, with `ci_low`, `ci_high`,
  `n_draws`, `draw_scheme` (`without_replacement`), and `seed_recipe`
- `backfire[N]`: `vote_accuracy[N] < single_sample_accuracy`
- `peak_N`, `peak_accuracy`, `curve_shape` classification (monotone up,
  monotone down, rise then fall, flat within CI)
- `plurality_agreement`, `mean_token_entropy` (carried over from the
  predecessor for comparability)
- **New, enabled by retained logprobs:** `answer_token_logprob_mean`,
  `answer_margin_vs_runner_up`, `answer_entropy` computed over the answer
  span only rather than the whole completion

That last group is the analysis the published paper could not run. It is
available only if section 2 and `answer_span_tokens` are both honoured.

### 4.1 Why `answer_rate` is required, and what it is guarding against

A truncated sample casts no vote. At a token cap C, the pool that actually
votes is the answered samples, so its size is `n_answered`, not `N`, and
**it is not a random subset of the N drawn**. It is exactly the subset that
finished answering inside C, which is to say it is enriched for the samples
that answer fast.

If that enrichment correlates with correctness in either direction, accuracy
is confounded with the cap:

- **If fast answers are more often right** (easy problem, direct recall),
  raising the cap admits slower and worse samples and accuracy falls. The
  curve reads as a model getting worse with more budget.
- **If fast answers are more often wrong** (guessing rather than working),
  raising the cap admits slower and better samples and accuracy rises. The
  curve reads as reasoning paying off.

Neither reading is available from the accuracy alone, because both produce a
moving accuracy for a policy whose behaviour never changed. The measured
predecessor case is not hypothetical: at a 16,384-token cap, 35.1 percent of
samples were truncated and 34.9 percent carried no visible answer at all, so
a third of the intended pool never voted. See
`notes/phase14b_token_audit.md` and `notes/max_tokens_estimate.md`.

The rule this imposes on the analysis:

1. **The analysis may not assume the voting pool is a random subset of the
   drawn pool.** Any statement of the form "accuracy at N" is a statement
   about `n_answered` samples out of N, and the record carries both so that
   the reader can see the difference rather than infer it.
2. **A change in accuracy across caps is not interpretable until the answer
   rate is shown to be stable across them.** If the answer rate moves, the
   pool moved, and the accuracy change is at least partly composition rather
   than capability. `02-technical-architecture.md` section 7.1 forbids the
   comparison outright for exactly this reason.
3. **`answer_rate` is not a diagnostic to check when something looks wrong.**
   It is published with the number it qualifies, always, because the failure
   it guards against looks like a clean result.

Adding this field bumps `SCHEMA_VERSION` and readers branch on it, per
section 1. A `problem` record from an earlier version has no `answer_rate`
and its accuracies are therefore unqualified; that is a fact about those
records, not something to backfill.

## 5. The `gate_outcome` record

One row per (gate, threshold, problem, model, N). This is the direct fix
for defect 2.

- `gate_name`, `gate_version`, `threshold`, `threshold_source`
  (`preregistered` or `exploratory`)
- `problem_id`, `model_slug`, `N`
- `gate_statistic` (the raw value compared against the threshold)
- `decision` (`route` or `hold`), `accuracy_under_decision`,
  `samples_consumed_under_decision`

With these rows a paired bootstrap is a groupby, not a re-run. The
predecessor deleted a claim it could not test because these rows did not
exist. `samples_consumed_under_decision` is included because the interesting
property of a gate that does not move accuracy may be that it reaches the
same accuracy at fewer samples.

## 6. The `budget_matched` record

The fix for defect 3, and the one that requires the most discipline,
because the failure mode is a fluent sentence rather than a missing file.

One row per (problem, model, total token budget T, strategy):

- `budget_tokens`, `strategy_id`, `n_samples_used`, `max_tokens_per_sample`
- `tokens_actually_consumed` (from stored `usage_raw`, not from the plan)
- `accuracy_under_strategy`, `ci_low`, `ci_high`
- `claim_ids` (which pre-registered claims cite this row)

Rule: **no sentence in any draft may describe a compute-matched comparison
unless a `claim_id` in that sentence resolves to rows here.** The
falsification suite enforces it by failing when a registered `claim_id` has
zero backing rows. This turns a prose-discipline problem into a test.

## 7. Retention policy

The brief's premise, "storing raw is cheap", holds for the non-reasoning
models and breaks for the reasoning ones. Rough shape, to be replaced with
measured values after Step 0:

- A per-token logprob entry serializes to roughly 20 to 30 bytes.
- A completion of a few hundred tokens costs single-digit kilobytes. Fine.
- A reasoning completion running to tens of thousands of tokens costs
  hundreds of kilobytes per sample uncompressed, and the sample count is in
  the tens of thousands. That is a disk-scale problem, not a rounding
  error.

Policy, per model class:

| Data | Non-reasoning | Reasoning |
|---|---|---|
| `raw_text` | always | always |
| `usage_raw` | always | always |
| logprobs over the answer span | always | always |
| logprobs over hidden reasoning | always | `[BLOCKED: Step 0]`; default is a fixed sampled fraction plus summary statistics for the rest |

If hidden-reasoning logprobs are subsampled, the sampling is deterministic
from `sample_key`, the fraction is recorded in the manifest, and the
`problem` record carries `logprob_coverage` so that no later analysis
mistakes partial coverage for complete coverage. Silent partial coverage
would be defect 1 in a new costume.

Storage mechanics: JSONL gzipped at rest, Parquet for derived tables, none
of it in git, released as an archived artifact per `03-security-and-access.md`
section 7.

## 8. The `run_manifest`

One per run, at `runs/<run_id>/manifest.json`:

- `run_id`, `phase_id`, `split`, start and end timestamps
- git SHA, dirty flag, lockfile hash
- `dataset_version_hash`, `prompt_template_id`, `extractor_version`
- full parameter set and `param_hash` per model
- `capabilities_id` per model
- `pricing_snapshot_id`
- `prereg_tag` (required and non-null for `split == confirmatory`)
- unanswered-sample policy, draw scheme, N grid, `M`
- realized cost, sample counts by `outcome_class`

The manifest is what a reviewer asking "what exactly did you run" is
handed. It should answer that question without opening a single script.

## 9. Validation

| Test | Asserts |
|---|---|
| schema conformance | every raw record has every **R** field with the right type |
| recomputability | derived tables rebuild byte-identically from raw |
| no coercion | no record has `is_correct == false` with `extracted_answer == null` |
| span integrity | `answer_span_tokens` indexes inside the stored logprob array |
| coverage honesty | `logprob_coverage < 1.0` is present wherever subsampling was applied |
| accuracy carries its answer rate | **every figure or table artifact carrying an accuracy carries a matching `answer_rate`**; a published accuracy without one fails the suite |
| claim coverage | every registered `claim_id` resolves to at least one artifact row |
| threshold integrity | pre-registered threshold values match the tagged commit, not just the verdicts computed from them |
| capability match | every phase's required fields are present in that model's capability probe |

The last two are the ones that catch the failures the predecessor actually
had. A verdict that validates against a moved threshold passes every naive
test.

### 9.1 The answer-rate pairing test, stated precisely enough to implement

The test is mechanical, so the contract has to be mechanical too.

- **What counts as an accuracy.** Any column, key or series in a published
  artifact whose name is `accuracy` or ends in `_accuracy`, and any figure
  panel whose plotted quantity is one of those. `single_sample_accuracy`,
  `vote_accuracy[N]`, `peak_accuracy` and `accuracy_under_strategy` are all
  in scope.
- **What counts as a match.** An `answer_rate` at the same granularity,
  reachable without a join the reader has to perform: the same table row for
  a table, the same panel or its caption for a figure. A rate published in a
  different file is not a match, because the failure this guards against is
  a number travelling on its own.
- **Where the pairing lives for a curve.** `vote_accuracy[N]` is a family of
  accuracies, so it needs `answer_rate` per N, not one rate for the problem:
  the voting pool at N=64 and at N=4 are different pools, and the whole point
  is that their composition can differ.
- **What the test does on absence.** Fails. It does not warn, and it does not
  pass an artifact that has no accuracy in it either way; an artifact with no
  accuracy is simply out of scope.
- **The escape hatch, and its cost.** An accuracy genuinely computed over a
  pool with no truncation (`n_truncated == 0` for every contributing sample)
  still publishes `answer_rate`, which will read 1.0000. The rate is not
  omitted when it is uninteresting, because "uninteresting" is a judgement
  made after seeing it and the reader has not seen it.

## 10. Open items for Step 0

Step 0 audits the abandoned phase 14b probe for token counts. While in
there, three additional questions are worth answering at zero extra cost,
because they determine fields in this document:

1. Were logprobs requested at all in that probe, and did the provider
   return them for that model? Decides whether the reasoning-model logprob
   policy in section 7 is even a live question.
2. Which provider and pricing were in effect, so the cost model has a
   comparable baseline rather than a remembered rate.
3. Is `finish_reason` stored, or is truncation only inferable from length?
   Decides whether `hit_ceiling` can be reconstructed retrospectively.

If a paid fallback probe is needed, it should double as the capability
probe in section 2. The sample is being bought either way.
