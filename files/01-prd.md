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
showed that a cheap agreement gate cannot avoid the damage. It closes by naming
its own key open problem in one sentence:

> "developing a deploy-time signal that distinguishes 'confidently correct'
> from 'confidently wrong' would unlock the oracle ceiling and is the key open
> problem."

Argmax exists to attack that sentence with instrumentation the predecessor did
not have. Specifically:

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

From arXiv:2608.11403, on 47 GPQA Diamond problems, N=64, temperature 0.7, two
7-8B non-reasoning models:

| | Qwen2.5-7B-Instruct-Turbo | Llama-3-8B-Instruct-Lite |
|---|---|---|
| accuracy at N=1 | 40.8% | 33.3% |
| accuracy at N=64 | 50.6% | 34.0% |
| backfire rate, problems where N=64 is worse than N=1 | **47%** [32, 62] | **66%** [51, 81] |
| oracle gate gain over fixed N=64 | +7.4 pp | +11.4 pp |
| fraction of that ceiling captured by an agreement gate | ~0% | 2.7% |
| plurality correct in the top confidence bin | 56.3% | 50.0% |

The paper's own limitations name what is untested: 47 problems, one benchmark,
two models, wide bootstrap intervals, calibration bins of 13 to 18 problems,
and both models small and non-reasoning, with reasoning-tuned models untested
because they may be better calibrated.

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
the single most promising signal for the paper's key open problem requires new
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

A row is eligible only if **its result stands alone as a contribution distinct
from arXiv:2608.11403**. The test is one sentence: state what the row
contributes that the backfire paper does not. If that sentence is thin, the row
is ineligible, and the honest home for the work is a revision of the existing
paper rather than a new entry.

This bar exists because the cheapest failure available to this project is to
spend its remaining credits reproducing a published result on more problems and
calling it a paper.

**One sentence per row:**

- **A.** Contributes the backfire rate across three difficulty tiers rather
  than one, which is the generalisation the published paper's own limitations
  section asks for and therefore reads as its missing table rather than as a
  separate result. **Thin.**
- **B.** Contributes the first backfire measurement on a reasoning-tuned
  policy, which the published paper names as untested, but at M=8 it cannot
  reach the N at which backfire was defined and a third of its samples never
  answer. **Thin as executed, not thin in principle.**
- **C.** Contributes the finding that a reasoning study and a non-reasoning
  study of the same phenomenon cannot be compared at any token budget, which is
  a methods result the backfire paper does not contain. **Not thin, but already
  established for free**, from stored data, in `notes/predecessor_cap.md`.

### Costing basis

`$0.00971` per sample for a reasoning model at a 16,384 cap, measured 2026-08.
`$0.000161` (Qwen) and `$0.0000996` (Llama) per sample for a non-reasoning
model at 2048, from the predecessor's recorded 2026-05 pricing snapshot at
`pilot/config.py:54` and `scripts/run_model2_sampling.py:55`. **That snapshot
is three months old and must be re-verified before any run**, per `03` section
4.4. `M=96` where a grid reaching N=64 needs a CI at its endpoint, per `02`
section 2.

### The table

| | **A. Non-reasoning, cap 2048, three tiers** | **B. Reasoning, one model, one tier, large cap** | **C. Both, two registered studies, no cross-comparison** |
|---|---|---|---|
| **Sizing** | 3 tiers x 47 problems, M=96, 2 models = 27,072 samples | 47 problems, M=8, 1 model = 376 samples | A plus B as sized here |
| **Cost** | **$3.53** | **$3.65** | **$7.18** |
| **Credits needed above $6** | none, $2.47 margin | none, $2.35 margin | **$1.18**, and $37.81 if B is to reach N=64 |
| **What it buys** | The backfire rate on 141 problems across three tiers, comparable to the published numbers because the cap and the answer rate both match | An answer rate and a truncation rate for a reasoning policy, plus a curve that tops out at N=4 with a CI | Both of the above, plus a documented incomparability between them |
| **What it forecloses** | The reasoning-model question entirely, at this budget | Any comparison to the published numbers, and any claim at the N where backfire is defined | Nothing extra, but it spends the margin that the capability probe and the inevitable re-run need |
| **Answers the paper's central question** (a deploy-time signal separating confidently-correct from confidently-wrong) | **No.** Nothing in A is a new signal | **No** | **No** |
| **Plausible venue** | Workshop table, or a v2 of the existing entry | None standalone. A technical note at best | Workshop methods note |
| **Eligible** | **No** | **No** | **No** |

### No row clears the bar

Not one of the three is eligible, and the reason is the same in all three
cases: **none of them touches the question the published paper names as
central.** A and C are affordable and thin. B is affordable only in a form that
measures nothing, and the form that would measure something costs $43.81
against $6 available.

Padding one of them into eligibility would mean attaching a gate analysis to a
scope that was not designed for it, and the resulting paper would be a
generalisation table with a gate bolted on.

### The alternative: v2 of 2608.11403, not a new entry

The honest move is a revision of the existing paper. It is already accepted at
the COLM 2026 Workshop on Efficient Reasoning, the problem set is the same 47
problems, and the extension below is comparable to the published runs by
construction: same cap, same prompt, same provider, answer rates matching at
0.99.

**The smallest credible extension**, in the order it would be run:

| Step | What | Samples | Cost |
|---|---|---|---|
| 1 | Capability probe, both models, confirming `top_logprobs >= 2` is honoured and re-verifying the price snapshot | ~4 | under $0.01 |
| 2 | Re-sample the published 47 problems, both models, N=64, cap 2048, retaining per-token logprobs and the answer span | 6,016 | **$0.78** |
| 3 | Margin gate against agreement gate, paired per problem, from stored rows | 0 | $0 |

**Total: about $0.79, leaving $5.20 of the $6.** It answers the paper's own key
open problem with the paper's own problem set, it is comparable to the
published numbers under `02` section 7.1 without an argument, and every number
it produces is recomputable from stored artifacts because `04`'s retention
policy is what the samples are collected under.

Two things it does not do, stated so the maintainer is choosing with them in
view. It says nothing about reasoning models, which stay out of reach at this
budget. And it stands or falls on whether the provider returns a runner-up
logprob, which is why step 1 exists and why it comes first.

If the margin gate fails to beat the agreement gate, that is a publishable
negative result on the paper's own central question, and it costs $0.79 to
find out.

---

**Sections 5 onward are deliberately unwritten.** Hypotheses, thresholds,
success criteria, the halt conditions and the falsification plan follow the
row, not the other way round.
