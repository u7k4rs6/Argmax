# Argmax: Product Requirements

Status: **sections 1 to 3 and the scope table only.** No hypotheses, no
thresholds, no success criteria. Those are written after the maintainer picks a
row from section 4, because every one of them is a function of which row is
picked, and writing them first is how a scope gets chosen by what has already
been written about it.

This document became writable when Step 0 returned the reasoning-model token
cost. `02-technical-architecture.md` section 1 and the README both say the PRD
is deliberately absent until that measurement exists. It exists now:
`notes/phase14b_token_audit.md`, `notes/max_tokens_estimate.md` and
`notes/predecessor_cap.md`.

Companion documents: `02-technical-architecture.md`,
`03-security-and-access.md`, `04-data-and-instrumentation-spec.md`.

---

## 1. What this project is for

The predecessor study, arXiv:2608.11403, measured how often majority-vote
self-consistency **reduces** accuracy on expert-level multiple choice, and
showed that two cheap verifier-free gates cannot avoid the damage. Its abstract
names its own central open question in one clause:

> "we do not test reasoning-native models, which we flag as the central open
> question."

**Argmax cannot answer that question**, and section 2.2 gives the measured
reason: it is not a budget problem. What Argmax can attack is a narrower thing
the paper names as a pipeline limitation rather than a finding:

> "Localized entropy (computed over final-answer tokens only) was not
> computable from stored data, which retained only the mean scalar; this is a
> limitation of the pipeline rather than a finding."

That limitation is the whole reason this repository's instrumentation exists.
Specifically:

1. **Per-token logprobs retained with a span pointing at the answer token.**
   The predecessor kept only a mean-entropy scalar, which foreclosed
   final-answer margin analysis permanently. A margin between the top answer
   token and the runner-up is a candidate deploy-time signal of exactly the
   kind the paper says is missing, and it is computable from data that costs
   nothing extra to collect at sampling time.
2. **Per-problem gate outcomes persisted**, so a paired comparison between two
   gates is a groupby rather than a re-run. The predecessor deleted a claim it
   could not test because those rows did not exist.
3. **A matched-compute comparison as a function**, so a sentence claiming one
   strategy beats another at equal budget resolves to stored rows.

Everything else in this repository, the split discipline, the pre-registration
tags, the falsification suite, exists to keep those three from producing a
confident number that means nothing. That is the lesson the predecessor
actually paid for, and `02` and `04` encode it.

**What this project is not for.** It is not a replication of the backfire
result. That result is published, it replicated across two model families
within the original study, and re-measuring it more widely is a contribution to
that paper rather than a separate one. Section 4 treats that distinction as the
eligibility bar rather than as a matter of taste.

## 2. What is already established, and what Argmax inherits

### 2.1 The published result

From arXiv:2608.11403, `paper/backfire_preprint.pdf`, accepted at the COLM 2026
Workshop on Efficient Reasoning. On the **full 198-problem** GPQA Diamond
benchmark, N=64, temperature 0.7, two 7-8B non-reasoning models, with 47
problems exploratory and a pre-registered 151-problem confirmatory split:

| | Qwen2.5-7B-Instruct-Turbo | Llama-3-8B-Instruct-Lite |
|---|---|---|
| backfire rate, pooled over 198 | **56.6%** | **65.7%** |
| grid-oracle ceiling above N=1 | +14 pp | +17 pp |
| movement from fixed-budget N=64 by either verifier-free gate | **< 0.002** | **< 0.002** |
| plurality correct in the top agreement bin | about half | lower than its lowest-agreement bin |
| confirmatory hypotheses passed | 4 of 4 | 4 of 4 |

> **Correction.** An earlier version of this section quoted 47 percent and 66
> percent backfire on 47 problems, an N=1 accuracy of 40.8 percent, and an
> agreement gate capturing "0 percent and 2.7 percent". Those are from
> `backfire_paper_draft.md` at the predecessor's repository root, a superseded
> 47-problem draft. The published preprint is the 198-problem version and its
> numbers are above. The same mistake put the wrong sentence in section 1: the
> superseded draft called a deploy-time signal "the key open problem", while
> the published abstract flags reasoning-native models as the central open
> question. Both are corrected here.

The paper's stated limitations: one benchmark, two models, both small and
non-reasoning, and reasoning-native models untested. It also records that
localized entropy was not computable from its stored data, and that its two
gate figures are computed on different problem sets and should not be read as
like-for-like.

### 2.2 What Argmax may and may not compare against it

This is settled, not open, and it constrains scope before any hypothesis is
written. Under `02-technical-architecture.md` section 7.1, two conditions are
comparable when their answer rates match or when the result is shown
insensitive to the difference. The published runs used `max_tokens = 2048`,
typed as a literal in four places and never registered, and answered at 0.9946
and 0.9860.

The measured consequence, from `notes/predecessor_cap.md`:

- A **non-reasoning model at 2048** answers at roughly 0.99 and is directly
  comparable. Citing the published numbers is legitimate.
- A **reasoning model at 2048** would answer at **at most 0.2649**,
  distribution-free, no fit involved, and **25 of 47 problems would produce
  nothing at all**. Not comparable, and not fixable by spending more.
- A **reasoning model at 16,384** answers at 0.6460 and loses 8 of 47 problems
  outright. Not comparable to the published numbers, and the cap difference
  refuses the comparison independently.

There is no cap at which a reasoning model matches both the published cap and
the published answer rate. **Any scope that puts a reasoning model beside the
published numbers is buying an incomparable pair**, and the incomparability is
already established for free, so it is not a finding that needs purchasing.

### 2.3 What the predecessor's instrumentation cannot answer retrospectively

The margin gate cannot be computed from the published runs. Their logprob
arrays were never stored, only a mean-entropy scalar, and the phase 14b probe
requested `logprobs: 1`, which returns the chosen token and no runner-up. So
the most promising candidate for the limitation the paper records requires new
samples, and those samples require a capability probe that confirms
`top_logprobs >= 2` is honoured for the chosen model. That probe is the first
spend of any scope below.

## 3. What Step 0 determined, and the one hypothesis it suggests

### 3.1 The token cost, and what it forecloses

Measured on the abandoned phase 14b probe, 404 records, MiniMax-M2.7 on GPQA
Diamond:

| Quantity | Value |
|---|---|
| cost per sample, reasoning model at a 16,384 cap | **$0.00971** |
| truncated at that cap | 35.1% |
| answer rate at that cap | 0.6460 |
| median output tokens | 4,655 |
| cost per sample, non-reasoning at 2048, from the predecessor's recorded snapshot | **$0.000161** (Qwen), **$0.0000996** (Llama) |

A reasoning sample costs **60 to 98 times** a non-reasoning one. That ratio,
not the absolute price, is what decides scope at a $6 ceiling.

`max_tokens` cannot be set from this data to any truncation-free value. The
fitted tail is not identified: the two-component mixture reproduces the body,
the censored fraction and the median, and its slow component's p99 moves by a
factor of twelve across refits the data barely distinguish. The design question
is therefore which truncation rate is acceptable, and the answer rate that
comes with it is a required published field per `04` section 4.

### 3.2 Mode membership is a property of the problem

The completion-length distribution is two populations, not one: a fast mode
with median 2,266 tokens carrying 54 percent of the weight, and a slow mode
that thinks to the cap. Which mode a sample lands in is **decided by the
problem, not by the sample**. 24 of 47 problems sit at exactly 0.00 or exactly
1.00 fast fraction; a permutation null that shuffles mode labels across
problems produces 24 extremes in **none of 10,000 draws**, and the observed
between-problem variance is 5.65 times the null.

That is a finding about the predecessor's data and it is solid.

### 3.3 The candidate hypothesis, stated as a candidate

What mode membership predicts is **whether a sample answers at all**. Its link
to correctness is **unresolved, not absent**, and the distinction matters:

- The raw correlation between a problem's fast fraction and its accuracy is
  0.856, and it is an artifact. 142 of 159 slow samples have no answer and the
  predecessor recorded every unanswered sample as wrong, which is the coercion
  `04` section 3.6 forbids.
- Among samples that produced an answer, the gap collapses to 0.9098 against
  0.8235 with heavily overlapping Wilson intervals, and the per-problem
  correlation falls to 0.099.
- **17 answered slow observations is too few to conclude anything.** Absence of
  evidence here is exactly that. A properly powered version of this comparison
  is a design target, not a result to cite.

The candidate hypothesis, for the maintainer to accept, reject or reword when a
row is picked:

> **Mode membership predicts curve shape, not accuracy level.** A problem whose
> samples answer fast and a problem whose samples think to the cap are
> different populations, and the accuracy-versus-N curve should peak in
> different places for them. The prediction is about where the curve turns, not
> about how high it sits.

Curve shape is the right target for three reasons. The accuracy level is
confounded with the answer rate, and the answer rate is what mode membership
already predicts, so predicting level would partly be predicting the confound.
The published paper's own result is a statement about curve shape, backfire
being a curve that turns down. And `argmax.analysis.curves` decides shape on
paired differences with per-replicate rows persisted, so a shape claim resolves
to stored artifacts while a level claim would need the answer-rate correction
argued separately.

**This is a hypothesis, not a finding, and it is not registered here.** It
becomes registrable when a row is picked and a threshold is attached to it,
with the deciding fields named per `04` section 1 principle 4.

---

## 4. Scope

### The eligibility bar

A row is eligible only if **its result stands alone**. The test is one
sentence: state what the row contributes. If that sentence is thin, the row is
ineligible, and the honest home for the work is a revision of an existing paper
rather than a new entry.

This bar exists because the cheapest failure available to this project is to
spend its remaining credits reproducing a published result on more problems and
calling it a paper.

**Standing alone does not mean standing next to the backfire paper.** The
central-open-question column below is kept because it is true and because it
bounds what may be claimed, not because it is the criterion. A result can be
worth publishing while answering none of that paper's questions.

### What the confidence-signal work actually contributes

The v2 extension is not "a better gate for the backfire paper". It is a methods
result about **how confidence signals are measured in long-form generation**,
and it stands on three legs, two already in hand:

1. **The dilution mechanism, established.** A whole-completion mean surprisal
   gives the answer token a weight of about **1 in 613**. The median token in a
   response carries 0.0004 nats against a mean of 0.26, so the statistic is
   dominated by several hundred near-deterministic prose tokens.
   **This does not depend on per-token arrays.** It is computed entirely from
   summary scalars the predecessor's pipeline already stored: `n_tokens`,
   `mean_per_token_nll` and `median_per_token_nll`. The arrays are gone and the
   result survives them, which is what makes it citable now rather than after a
   new run.
2. **The localised alternative, untested by anyone.** The published paper
   records that localized entropy over final-answer tokens "was not computable
   from stored data" and calls that a pipeline limitation rather than a
   finding. Nobody has measured whether a span-localised signal separates
   confidently-correct from confidently-wrong, on this benchmark or on this
   model class. That is the experiment.
3. **The threshold-selection demonstration, established.** Sweeping every
   candidate cut on the stored entropy signal gives a best separation of
   **+0.356 on Qwen and -0.317 on Llama**: the same procedure, opposite sign,
   the positive one a maximum over roughly 150 cuts resting on 17 problems.
   A worked example of a selected threshold that reverses direction on a second
   model, from real data rather than simulation.

Together those are a paper about measurement: **a widely used confidence
statistic is diluted by construction, its apparent gate performance is a
selection artifact, and the localised version that would fix the first problem
has never been tested.** Legs 1 and 3 are already computed from stored data,
which means the new sampling buys leg 2 only, and leg 2 is the part that can
fail informatively.

None of that requires the backfire paper to be nearby. It requires one
long-form generation task, one model whose provider returns depth of at least
2, and the answer spans that doc 4 section 3.6 already mandates.

**One sentence per row:**

- **A.** Tests whether Chen et al. 2024's mixture explanation for
  rise-then-fall majority-vote curves, and the few-sample optimal-call-count
  estimator built on it, survive on a uniformly hard benchmark where the
  easy-query component they invoke is absent. **Not thin.** It tests a
  mechanism claim from a different paper by manipulating the thing that claim
  rests on, which is not what the backfire paper does.
- **B.** Contributes the first backfire measurement on a reasoning-tuned
  policy, which the published paper names as untested, but at M=8 it cannot
  reach the N at which backfire was defined and a third of its samples never
  answer. **Thin as executed, not thin in principle.**
- **C.** Contributes the finding that a reasoning study and a non-reasoning
  study of the same phenomenon cannot be compared at any token budget, which is
  a methods result the backfire paper does not contain. **Not thin, but already
  established for free**, from stored data, in `notes/predecessor_cap.md`.

> **Correction.** An earlier version of this table read row A as "the backfire
> rate across three tiers" and marked it thin, because Thread A was defined
> only in the kickoff brief, which is in neither repository, and the reading
> was a guess. Thread A is the Chen et al. test above. The guess changed a
> verdict, so the definition is now transcribed in
> `docs/kickoff/THREADS.md` and the verdict below is revised. The brief itself
> is still not committed.

### Thread A, reformulated, with the evidence that forced it

**The original premise was tested and failed.** Thread A asked whether Chen et
al.'s mixture explanation breaks when the easy component is absent, with GPQA
Diamond as the uniformly hard case. It is not uniformly hard for these models:

| | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| per-problem accuracy variance against a homogeneous null | **25.5x** | **17.1x** |
| p | < 0.0001 | < 0.0001 |
| problems at accuracy 0.00 | 12 | 6 |
| problems above 0.95 | 10 | 0 |
| two components beat one by | 77.5 AIC | 67.1 AIC |

Full working in `notes/mixture_premise.md`. The published paper asserts the
opposite in its Positioning section, which section 4.4 below records as a
disclosure item.

**The reformulation.** Test the estimator where the mixture **is** present and
measured, rather than where it is absent. This is a different question from the
one the kickoff brief specified, and it is recorded as a reformulation with its
evidence rather than swapped in quietly. The original is not recoverable by
choosing a different benchmark, because establishing that any task is unmixed
for a given model requires exactly the measurement that just refuted it here.

#### The specification, concrete enough to cost

Chen et al. estimate, from a small number of samples per query, the call count
that maximises **aggregate** performance, using the easy/hard mixture structure.
The test is whether that estimate lands where the measured optimum is.

**Ground truth.** From the stored `M = 64` samples per problem, compute
`vote_accuracy(N)` on the published grid `{1, 2, 4, 8, 16, 32, 64}` using
`argmax.analysis.curves`, which reports the pool bootstrap and the paired
differences. Define:

- `N*_agg`, the grid point maximising pooled accuracy over all problems
- `N*_i`, the grid point maximising problem i's own vote accuracy

**The estimator's input.** `k` samples per problem, drawn from the same stored
M with the seed recipe already in `argmax.keys`, so no additional sampling is
required at any k. **`k` in {4, 8, 16}**: 4 and 8 match the probe sizes the
predecessor's agreement gate used, and 16 adds a third point without
approaching M.

**Prediction error, reported at both levels.**

| Metric | Definition | Level |
|---|---|---|
| aggregate regret | `MV_acc(N*_agg) - MV_acc(N̂_agg(k))`, in accuracy points | primary |
| grid distance | `abs(log2 N̂ - log2 N*)`, because the grid is geometric | both |
| exact match | `P(N̂ = N*)` | both |
| per-problem regret | mean over problems of `vote_acc(N*_i) - vote_acc(N̂_i(k))` | secondary |

The aggregate level is the faithful reproduction of what Chen et al. claim. The
per-problem level is the extension the backfire result makes interesting, since
that is where the oracle headroom lives, and it is reported as an extension
rather than as their claim.

**Baselines, fixed before the comparison.** The estimator must be scored
against: always `N = 64`; always `N = 1`; and the best fixed N chosen on the
same `k` samples without the mixture model. The third is the one that matters,
because it isolates what the mixture structure contributes over naive selection.

**What PASS looks like.** The estimator's aggregate regret is small relative to
the headroom between the best and worst grid points, and smaller than every
baseline's, at all three k. Per-problem, its grid distance is below what the
naive baseline achieves.

**What FAIL looks like.** Regret indistinguishable from the naive baseline, or
predicted N uncorrelated with measured N*, or a k-dependence that reverses
direction between models or between k values. A FAIL is publishable: it says
few-sample optimal-call estimation does not transfer to a benchmark of this
difficulty profile, which is a claim about the method rather than about this
project.

**No thresholds are registered here.** "Small relative to the headroom" and
"below the naive baseline" become numbers in `PREREGISTRATION.md` when the
maintainer picks the row, per doc 4 section 1 principle 4.

#### The sampling design it needs, and why it shrank

**Three tiers are no longer required.** Tiers were a device for varying the
mixture across conditions. The mixture varies **within** the benchmark, it is
measured, and its components are estimated, so the variation the design needed
is already in one problem set. Two further reasons to drop the tiers: a tiered
design must hold `n_options` and format fixed across tiers per doc 2 section
5.1, which constrains which supersets are usable; and section 4.3 below shows
47 problems per tier cannot resolve any plausible between-tier gradient anyway.

The design is therefore **one benchmark, all 198 problems, one model, M = 64**,
with logprobs retained at depth 5. Every `k` in {4, 8, 16} is a subset of the
same M, so the estimator costs nothing beyond the one sampling run.

### Costing basis

Re-verified 2026-08-13 against Together's own pricing and model pages, recorded
as `configs/pricing/together-2026-08-13.yaml`. The predecessor's 2026-05
constants are **not** carried forward, and one of the two had moved:

| Per sample, cap 2048 | 2026-05 basis | **2026-08-13 snapshot** |
|---|---|---|
| Qwen2.5-7B-Instruct-Turbo | $0.000161 | **$0.000268** (price up 67 percent) |
| Llama-3-8B-Instruct-Lite | $0.0000996 | **$0.0000996** (unchanged) |

Reasoning model at a 16,384 cap: **$0.00971** per sample, measured 2026-08, and
the MiniMax rates that produced it still hold at today's snapshot.

Token counts per sample are measured from the predecessor's stored completions,
not assumed: 295.8 in and 598.9 out for Qwen, 272.4 in and 438.7 out for Llama.

**`M = 64`, not 96, and this was verified against the implementation rather
than argued.** Doc 2 section 2 warns that subsampling without replacement at
`N == M` admits one draw, so the endpoint has no subsample variance. That is a
statement about the Monte Carlo layer, and the reported CI is not the Monte
Carlo layer: `argmax.analysis.bootstrap` resamples the **pool**, which varies
even when the draw does not.

Checked by running it. On a 64-sample pool of 34 correct and 30 incorrect, at
`N = M = 64`:

| Quantity | Value |
|---|---|
| `degenerate` flag | True |
| `mc_halfwidth` | 0.0000 |
| reported CI | **[0.0000, 1.0000]** |

The endpoint interval is not merely non-degenerate, it is the full range,
because each resampled pool flips the majority and the vote at N=64 is one
Bernoulli outcome per world. That is the honest answer for a single problem at
its endpoint, and it averages down across 198 of them. `M = 64` therefore
supports a reported CI at `N = 64`, and it reproduces the published design
exactly. **The 33 percent of budget that `M = 96` was buying is freed.**

### 4.3 Power at 47 problems per tier, and why the tiers went

Conditional: this section costs the tiered design that section 4.1's
reformulation has already dropped. It is kept because it bounds **any** design
that compares per-problem rates between groups of this size, including a future
tiered one.

Two independent proportions, alpha 0.05 two-sided, power 0.80, baseline
backfire rate 0.566 from the published pooled figure. Alpha is the
conventional default and **is not pre-registered**; nothing here registers a
threshold.

| n per tier | minimum detectable difference in backfire rate |
|---|---|
| **47** | **28.2 points** |
| 66 | 24.0 points |
| 100 | 19.7 points |
| 151 | 16.1 points |
| 198 | 14.0 points |

| gradient to detect | n per tier required |
|---|---|
| 10 points | **391** |
| 20 points | **97** |

A single tier's own rate at n=47 has a 95 percent interval of
[0.433, 0.705], width 0.272. At n=198 it is [0.496, 0.633], width 0.137.

**47 problems per tier resolves nothing below a 28 point gradient.** For scale,
the published difference between the two models is 56.6 against 65.7, about 9
points, which would need roughly 391 problems per group to detect. A three-tier
design at 47 each would have been powered only for an effect larger than any
this literature reports.

### 4.4 A disclosure item for any v2 draft

The published paper's Positioning section states: "our gate results sit in
tension with few-sample estimation of an optimal call count: **on a uniformly
hard benchmark**, the verifier-free signals such estimation would rely on do
not recover the headroom."

Its own stored data does not support "uniformly hard" as a property of the
benchmark for these models: per-problem accuracy varies at 25.5 and 17.1 times
a homogeneous null, with 12 problems at zero accuracy and 10 above 0.95 for
Qwen. The paper elsewhere reports that backfire is not uniform across domains
and names chemistry as the dominant contributor, so the heterogeneity is
partly acknowledged and then not carried into the positioning sentence.

**This is a disclosure item, not a finding.** It does not touch the paper's
results, which are per-problem backfire rates rather than claims about
uniformity, and it does not change any number in it. It affects one sentence of
positioning against Chen et al., and a v2 that reformulates Thread A around
that same positioning has to say so plainly rather than quietly relying on the
corrected reading.

### The table

| | **A. Non-reasoning, cap 2048, three tiers (Thread A)** | **B. Reasoning, one model, one tier, large cap** | **C. Both, two registered studies, no cross-comparison** |
|---|---|---|---|
| **Sizing** | **198 problems, M=64, Qwen only = 12,672 samples** (was 3 tiers x 47 at M=96 with 2 models) | 47 problems, M=8, 1 model = 376 samples | A plus B as sized here |
| **Cost at the 2026-08-13 snapshot** | **$3.40** | **$3.65** | **$7.05** |
| **Credits needed above $6** | none, **$2.60 margin** | none, $2.35 margin | **$1.05**, and $37.81 more if B is to reach N=64 |
| **What it buys** | A test of whether Chen et al.'s few-sample optimal-call estimator lands where the measured optimum is, on a benchmark whose mixture is present and quantified, plus legs 1 to 3 of the measurement result and the margin gate off the same samples | An answer rate and a truncation rate for a reasoning policy, plus a curve that tops out at N=4 with a CI | Both of the above, plus a documented incomparability between them |
| **What it forecloses** | The reasoning-model question entirely, at this budget | Any comparison to the published numbers, and any claim at the N where backfire is defined | Nothing extra, but it spends the margin the capability probe and the inevitable re-run need |
| **Answers the backfire paper's central open question** (reasoning-native models). Bounds the claims; not the eligibility criterion | **No** | **No**, see section 2.2: not a budget problem | **No** |
| **Supplies leg 2 of the measurement result** (the untested localised signal) | **No** on its own, but see below: A's samples make it free | **No** | **No** |
| **Plausible venue** | Standalone workshop or short paper: it tests a published scaling model, not this project's predecessor. With the confidence-signal work attached, a methods paper that cites the backfire result rather than extending it | None standalone. A technical note at best | Workshop methods note |
| **Eligible** | **Yes, on the reformulated question in section 4.1.** The original was refuted before sampling | **No** | **No** |

### One row clears the bar, and it was the one previously marked thin

**A is eligible.** Under the correct Thread A definition it is not a
generalisation of the backfire result; it is a test of a mechanism claim in
Chen et al. 2024, on the case that discriminates it. The backfire paper does
not test a scaling model, does not manipulate the mixture, and does not
evaluate an optimal-call-count estimator.

B and C remain ineligible for the reasons already given: B measures nothing at
a budget that fits, and C's distinctive contribution is already established for
free from stored data.

### A and the gate extension share their samples

This is the thing worth noticing. The v2 gate extension needs non-reasoning
samples on the published 47 problems, at cap 2048, with per-token logprobs
retained. **Row A's hard tier is those same problems under those same
settings.** Collect A's samples with `logprobs_depth` set and the gate
comparison is a groupby over rows that already exist:

| Step | What | Samples | Cost |
|---|---|---|---|
| 1 | Capability gate, both models, deepest documented logprob depth | 2 | under $0.01 |
| 2 | Row A, three tiers x 47 problems, M=96, both models, cap 2048, logprobs retained | 27,072 | **$4.98** |
| 3 | Thread A: does the rise-then-fall shape survive on the hard tier | 0 | $0 |
| 4 | Margin gate against agreement gate, on the hard tier, paired per problem | 0 | $0 |

**Total about $4.99, leaving $1.01.** Two registered studies off one sampling
run, which `02` section 8.1 permits and `02` section 8.3 requires be tagged
separately.

The margin gate half is comparable to the published numbers by construction:
same cap, same prompt, same provider, answer rates matching at 0.99. If it
fails to beat the agreement gate, that is a publishable negative result on a
limitation the paper records but could not test, obtained at no marginal
sampling cost. It is not an answer to the paper's central open question, which
is reasoning-native models and is out of reach for the reasons in section 2.2.

### What the v2 extension does and does not attack

**It attacks the gate question**, meaning the backfire paper's stated key open
problem: is there a deploy-time signal that separates confidently-correct from
confidently-wrong. The candidate is the answer-token margin against the
runner-up, which the predecessor could not compute because it stored a scalar
and requested depth 1.

**It does not attack the reasoning-model question**, and nothing in this plan
does. Any sentence suggesting otherwise is wrong.

### Why the reasoning-model question stays open

The published paper names it as untested: both its policies are small and
non-reasoning, and whether backfire shrinks for reasoning-tuned models, which
may be better calibrated, is unknown. This project does not close it, for a
reason that is measured rather than budgetary in origin:

- At the published cap of 2048, a reasoning policy answers **at most 0.2649**
  of the time, distribution-free, and **25 of 47 problems produce nothing at
  all** (`notes/predecessor_cap.md` section 2.1). The comparison is not
  expensive there, it is empty.
- At 16,384 the policy answers 0.6460 and the cap no longer matches, so `02`
  section 7.1 refuses the comparison on both counts.
- Reaching N=64 on 47 problems with a reasoning policy costs **$43.81**
  against $6 available, and that is before the answer rate is dealt with.

So the barrier is not only money. **There is no cap at which a reasoning policy
both matches the published cap and matches the published answer rate**, which
means the reasoning-model question cannot be answered as an extension of this
paper at any budget. It needs its own study, with its own controls, and a
budget that admits a reasoning policy at a large cap. Recording that here is
the point: it is a scope boundary with a measurement behind it, not an item
deferred for lack of funds.

---

**Sections 5 onward are deliberately unwritten.** Hypotheses, thresholds,
success criteria, the halt conditions and the falsification plan follow the
row, not the other way round.
