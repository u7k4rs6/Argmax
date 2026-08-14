# Where the disagreement lives

**Draft, v2 of arXiv:2608.11403.** Structure follows `notes/outline_v2.md`,
which was ordered by `notes/prior_work.md` rather than by the order the work
was done.

**Status of numbers in this file.** Every figure is either produced by
`derive.py` from the stored raw records and reproducible by the falsification
suite, or marked `[BLANK]`. A `[BLANK]` is not a placeholder to be filled with
a plausible value; it marks a quantity this project does not have. Sentences
describing a compute-matched comparison are absent entirely, because no
`budget_matched` rows exist yet and doc 2 forbids writing one without them.

Predecessor cited throughout as arXiv:2608.11403, read from
`paper/backfire_preprint.pdf`.

---

## Status: this is an addendum, not yet the manuscript

**Confirmed by inspection.** This file contains only the new material. A v2
replaces arXiv:2608.11403 rather than supplementing it, so it must carry that
paper's abstract, setup, and results with the new work integrated. It does not
yet. The original is 4,232 words in seven sections:

| original section | present here | disposition on merge |
|---|---|---|
| Abstract | rewritten below, provisional | replace |
| 1 Introduction | partly | merge; framing changes below |
| 2 Setup | **absent** | carry over, extend with margin instrumentation |
| 3 Pre-Registered Confirmatory Results | **absent** | carry over unchanged |
| 4.1 Backfire affects the majority of problems | **absent** | carry over unchanged |
| 4.2 The oracle upper bound is real but not reachable | **absent** | carry over, add the flat-aggregate-curve caveat |
| 4.3 Two verifier-free gates fail to capture it | **absent** | carry over, **reinterpret** |
| 4.4 Why: confidence does not track correctness | **absent** | carry over, **substantially revise** |
| 5 Discussion | **absent** | rewrite around the new material |
| 6 Limitations | partly | merge |
| 7 Conclusion | **absent** | rewrite |

Merging is the next task. Nothing below should be read as final ordering.

### What the original's framing must change, because the new work reinterprets it

Four changes, in descending order of how much they alter a claim.

1. **Section 4.4's title and thesis, "confidence does not track correctness",
   is now too strong and partly misdiagnosed.** The original inferred a single
   mechanism from the joint failure of two gates. The new work separates them:
   the **token-entropy** gate failed on **aggregation**, because a per-token
   average over roughly 613 tokens is dominated by fluency and the answer token
   is one of them, and that is a measurement artefact rather than a fact about
   confidence. Repairing the aggregation, by measuring at the answer span,
   produces a signal that still fails, but for a different reason: saturation.
   The merged section must present these as two failures with two causes, not
   one thesis with two witnesses.

2. **The correctness claim needs a unit attached.** "Confidence does not track
   correctness" is false as stated at the across-question unit: our own margin
   separates correct from incorrect samples by +0.0589 with an interval
   excluding zero, and Kumaran (arXiv:2606.29490) reports AUROC 0.62 to 0.80
   for the same quantity across questions. What we can defend is the
   within-question claim. The merged text must say **which** decision the
   signal fails at rather than asserting a general absence of information.

3. **The abstract's "we do not test reasoning-native models, which we flag as
   the central open question" must become a scoped negative result.** It is no
   longer open in the same way: on hosted serverless inference at these
   budgets, it is unmeasurable, and section 4 reports three separate walls.
   The open question survives, but it is now open **for the open-weights
   route**, not open in general.

4. **Model coverage becomes asymmetric and must be labelled everywhere.** The
   original's backfire result covers two models from different families. The
   new registered claims cover **one**. A merged paper carrying both must not
   let the reader infer that everything here rests on two models.

Two smaller items. Section 4.2's oracle headroom should note that the
**aggregate** accuracy curve over the grid spans only 0.52 points, so the
14-to-17 point headroom is entirely per-problem and an aggregate reading of it
is wrong. And the original's own pre-registration split (47 exploratory, 151
confirmatory) should be reported alongside the disclosure that three of the 50
exploratory ids sit inside the confirmatory 151.

---

## Abstract

Self-consistency by majority vote reduces per-problem accuracy on most GPQA
Diamond problems for small instruction-tuned models: 56.6 percent of problems
for Qwen2.5-7B and 65.7 percent for Llama-3-8B (arXiv:2608.11403). The obvious
remedy is a verifier-free confidence gate that decides which problems to vote
on. This paper reports that the most natural repair to that remedy also fails,
and separates two failures the earlier work treated as one.

A token-entropy gate fails for a measurement reason rather than a substantive
one: a per-token average over a chain of roughly 613 tokens is dominated by
fluency, and the answer token is one of them. We therefore measure confidence
at the answer span itself, where that dilution cannot apply. **On
Qwen2.5-7B-Instruct-Turbo, 198 problems at 64 samples each, a sample whose
answer contradicts its own problem's plurality still emits that answer at a
median margin of 20.52 nats, with 75.7 percent of such samples above 10 nats.**
Both quantities were pre-registered with thresholds fixed in advance and tested
once on 69 problems that no exploratory analysis had read; both passed. The
same margin does separate correct from incorrect samples across the benchmark,
by 0.0589 on the fraction above 10 nats with an interval excluding zero, so the
claim is not that token log-probabilities carry no information. It is that a
signal with genuine across-question discrimination is close to useless for the
**within-question** decision self-consistency actually poses: which of several
disagreeing samples of the same problem to trust. The disagreement lives
upstream, in which chain was written, and the answer token reads out a chain
that has already committed. **We did not find this result in our search of the
prior literature**, though the dilution it corrects for, and the practice of
measuring at the answer span, are both established.

These claims rest on **one model**. A registered second-model replication was
sampled and could not be evaluated: its cap was selected from a probe of eight
non-random problems that proved unrepresentative, the run's answer rate came in
at 0.8931 against a registered comparability condition of 0.9950, and scoring a
pool selected for finishing fastest would have violated the rule this paper
argues for. We report that rejection rather than the result.

We separately report that on **hosted serverless inference at a small budget**,
three reasoning-native models could not be evaluated at all, for three distinct
and separately measured reasons: no serverless route at any price, no
comparable answer rate at any affordable cap, and zero extractable answers with
generation consuming the entire budget. All three models are downloadable, so
this bounds what a metered per-token API buys rather than what is knowable, and
we name open weights on fixed-cost compute as the route a follow-up should
take. Total project spend was $4.67, itemised.

## 1. Introduction

arXiv:2608.11403 established that majority voting over sampled chains reduces
accuracy on 56.6 and 65.7 percent of GPQA Diamond problems, depending on the
model. That is prior work and is cited, not claimed, here.

The natural response is selective voting: compute a confidence signal per
sample, and use it to decide which samples to trust or whether to vote at all.
The signal most readily available from any provider is the model's own token
probability. **This paper tests that response and reports that it fails, for a
reason that is not the one usually given.**

The usual reason offered is that sequence-averaged confidence is diluted by
high-confidence filler tokens. That is true, it is already established (section
3), and it is not our finding. We measure confidence at the answer token
itself, where dilution cannot apply, and it still does not separate the samples
that a voting procedure must separate.

### Contributions

1. **A registered, held-out commitment result on one model.** A sample whose
   answer contradicts its own problem's plurality emits that answer at a
   median margin of 20.52 nats. The disagreement self-consistency exploits is
   not located at the answer token.
2. **The reasoning wall, scoped to hosted serverless inference.** Three
   reasoning-native models, three distinct and separately measured failures to
   evaluate, with an itemised bill, and the open-weights route named as what a
   follow-up uses.
3. **A methodological rule with a test behind it**: comparability between
   models is keyed on answer rate, not on matched token caps.
4. **Thread A**, a negative result on a reconstructed few-sample estimator.

We also report, in section 7, the case where rule 3 rejected one of our own
registered results.

## 2. The commitment result

### 2.1 Setup

198 GPQA Diamond problems, Qwen2.5-7B-Instruct-Turbo, M = 64 samples per
problem, cap 2048, logprobs at depth 5. 12,672 samples.

The **answer-token margin** is the log-probability of the emitted option letter
minus that of the highest-scoring alternative option letter, at the answer
position. Censoring rule and its justification are in section 3.

Split discipline: 129 problems were exposed to exploratory analysis and are
recorded as such in `notes/exploration_ledger.md`. **69 problems were never
read by any exploratory analysis.** The claims below were registered at
`argmax-prereg-margin-desc-v1.0`, with thresholds fixed, before those 69 were
examined, and were examined once.

### 2.2 Registered claims and verdicts

| id | quantity, over samples dissenting from their problem's plurality | estimate | one-sided 95% lower bound | registered threshold | verdict |
|---|---|---|---|---|---|
| **MD1** | per-problem median margin | **20.5232** | 18.8376 | 15.0 | **PASS** |
| **MD2** | per-problem fraction above 10 nats | **0.7567** | 0.7105 | 0.60 | **PASS** |

64 of 69 problems carried at least three dissenting samples; 5 were excluded
by the registered rule and are counted, not imputed.

**Answer rate, reported beside the accuracy-bearing quantities as doc 4
section 4.1 requires:** 0.9950 [0.9936, 0.9961], against the published Qwen
figure of 0.9946 [0.9932, 0.9958]. 12,344 margins measured, 265
right-censored.

The holdout reproduces the exposed set closely: 20.52 against 20.62, and
0.757 against 0.749. Both are reported; only the holdout figures were
registered.

### 2.3 Reading

A sample that contradicts the plurality of its own problem still emits its
answer at a median of 20.5 nats, which is odds of roughly 800 million to one
against the nearest alternative option. **Dissenting samples are as committed
as agreeing ones.**

The implication for selective voting is direct. The variance that
self-consistency exploits does not live at the answer token. It lives upstream,
in which chain got written, and the answer token is a near-deterministic
readout of a chain that has already committed.

### 2.4 The counterweight, stated here rather than buried

The margin is not devoid of information about correctness. Across samples, the
fraction above 10 nats separates correct from incorrect samples by **+0.0589**,
with a cluster-bootstrap interval excluding zero. That is a real effect and it
is small.

**We therefore do not claim that token log-probabilities are uninformative**,
and any reading of this paper that reaches that conclusion has overshot. The
claim is narrower and is about a unit: a signal with genuine **across-question**
discriminative power is close to useless for the **within-question** routing
decision that self-consistency actually poses.

This distinction matters because it reconciles our result with recent work
reaching an apparently opposite conclusion. Kumaran (arXiv:2606.29490) reports
that calibrated log-probability confidence behaves as an answer-evidence signal
coupled to correctness, at AUROC 0.62 to 0.80. That quantity, a
temperature-scaled softmax over the option letters, is ours at the same locus.
Its unit is not: every result there is trial-level across questions, with one
answer drawn per question, and the design never conditions on samples that
disagree with each other because it never has two samples of one question to
compare. **We agree with that paper on its unit and report a different one.**

## 3. Mechanism and instrumentation

This section exists to rule out an alternative explanation for section 2, not
to make a claim.

### 3.1 Dilution is real, established, and not ours

Averaging a per-token log-probability over a chain of roughly 613 tokens, of
which the answer token is one, produces a number dominated by fluency rather
than by the answer. This is the motivating premise of relevance-weighted
uncertainty estimation (Duan et al., SAR, arXiv:2307.01379), a restatement in a
new setting of the length pathology long known in machine translation (Murray
and Chiang, arXiv:1808.10006), and the target of recent length-invariant
estimators (arXiv:2505.19060). Measuring at the answer span rather than the
sequence average is likewise established, in SAR, in DeepConf's windowed
confidence, in claim-conditioned probability, and in CIKM 2025's
"one-token-deep" analysis of multiple-choice uncertainty.

**We adopt the fix rather than proposing it.** Its only role here is to close
off the objection that section 2's negative result is an artefact of measuring
in the wrong place. It is not: we measured in the right place and the signal is
still saturated.

### 3.2 The margin and its censoring rule

The provider returns the top k alternatives per token, k = 5 in practice. Five
slots need not contain every option letter.

- **Two or more option letters present: measured.** The second-highest present
  option is a returned value, and any absent letter is at or below the smallest
  returned value, so it cannot outrank it. The margin is exact.
- **Fewer than two present: right-censored** at the top letter minus the
  smallest returned logprob. Recorded as a bound.
- **Never imputed.** Filling a missing letter at the censoring bound would
  understate the margin exactly on the problems where the model is most
  certain, which are the ones a confidence gate cares about most.

12,344 measured, 265 censored.

### 3.3 A reproducibility note: response shape is a property of the model

Together returns logprobs in two shapes, and which one arrives is decided by
the model, not the provider: parallel arrays for Qwen2.5-7B, OpenAI-nested for
Qwen3.5-9B. A parser written against the first does not fail loudly on the
second; it finds no alternatives and returns nothing. This produced a null
margin on every sample of the second model, with no error raised anywhere,
and was caught by a 32-sample probe rather than after a 3,168-sample run.

A parser validated on one model is unvalidated on the next.

## 4. The reasoning wall, on hosted serverless inference

### 4.0 Scope, stated before the measurements

**The claim in this section is about hosted serverless inference, and it does
not hold for open weights on owned or free compute.** Stated first because
unscoped it has a one-line rebuttal, and the rebuttal is correct.

All three models below are **downloadable**. Nothing here says a
reasoning-native model cannot be evaluated on GPQA Diamond. It says that on a
metered, per-token, hosted API at a small budget, three of them could not be:
one had no serverless route at any price, one never reached a comparable
answer rate at any cap we could afford, and one returned nothing at all at any
affordable cap.

**What the constraint actually is.** Serverless pricing charges per output
token, and reasoning-native models emit a great many of them. That makes the
cost of a fixed experiment scale with the model's verbosity rather than with
the size of the benchmark, and 198 problems at M = 16 becomes unaffordable at
the caps these models need. The wall is a property of **the billing model**
meeting **the generation length**, not of the models being hard to run.

**The route a follow-up should take is therefore open weights on fixed-cost
compute**, where the marginal cost of an output token is zero and the binding
constraint becomes wall-clock and memory instead. Kaggle's free tier, for
example, offers two T4 GPUs at 32 GB total with roughly 30 GPU-hours per week,
which is enough for a 7 to 9B model in reduced precision and long generations,
though not for a 32B model without quantisation or offload. Under that budget
the caps that defeated us here are affordable, and the questions this section
had to abandon become answerable. What changes is not the science but the
denominator.

We report the serverless walls because they are what this project met and
because they are unreported elsewhere, not because they bound the problem.

### 4.1 Position relative to prior work

That token budgets change evaluation outcomes is established. Budget-dependent
ranking reversals have been reported on GPQA Diamond at the same 198 items,
significant at p < 0.01, with a three-tier truncation analysis
(arXiv:2608.12150). That paper is stronger than this one on the general claim.

**It deliberately excludes reasoning-native models**, naming o1, DeepSeek-R1
and QwQ, on the stated grounds that their dual-stream architecture changes the
semantics of `max_tokens`. This section reports that excluded region.

### 4.2 Three models, three measured walls

Each established by a real request, never inferred from a price list or a model
card.

| model | wall | measurement |
|---|---|---|
| **QwQ-32B** | unreachable | `model_not_available`; no serverless route |
| **MiniMax-M2.7** | never at a comparable cap | answer rate 0.6460 at cap 16,384; 0.2649 at the published 2048 |
| **Qwen3.5-9B** | nothing at any affordable cap | answer rate **0.0000** at 2048 and at 4096, with **mean completion equal to the cap exactly**; 0.5938 at 8192 |

Reference: Qwen2.5-7B-Instruct-Turbo at cap 2048 answers **0.9950** over
12,672 samples.

The Qwen3.5-9B row is the sharpest. Every one of 52 samples at 2048 and 4096
ran to the ceiling, and at 4096 the visible channel received 38 characters.
The model card recommends 32,768 output tokens for general queries, so the
published study's 2048 is a sixteenth of this model class's own lower
recommendation. This is not a model failing at a reasonable cap; it is a cap
fixed before this class of model was the default.

### 4.3 The wall has a door, and the door changes the experiment

Together honours a thinking control on Qwen3.5-9B. Two spellings, the model
card's `chat_template_kwargs {"enable_thinking": false}` and the provider's
`reasoning {"enabled": false}`, are both accepted and indistinguishable in
effect: mean completion 1537.3 against 1532.8 at cap 2048, identical
truncation, no reasoning field returned either way.

**A reasoning model with reasoning disabled is a second non-reasoning model.**
What became purchasable was therefore not the replication that was wanted, and
we do not describe it as one.

### 4.4 The bill

| | samples | spend |
|---|---|---|
| capability gate, five candidates | 5 | under $0.01 |
| cap probe, 2048 / 4096 / 8192 | 84 | $0.1032 |
| thinking-control probe | 32 | $0.0137 |
| cap probe at 6144, thinking off | 32 | $0.0178 |
| **probe total** | **148** | **$0.1347** |
| margin-v1, the one complete run | 12,672 | $3.4122 |
| margin-v2, incomplete (section 5) | 1,253 | $1.2554 minus probes |
| **realized, all phases** | **14,073** | **$4.667639** |

arXiv:2608.12150 reports 56,476 API calls and no monetary cost. We report the
ledger because the negative results in this paper are only interpretable
alongside what was affordable.

**The bill is computed, not confirmed.** Every row is stored token counts
multiplied by a dated price snapshot. The ledger is complete against the raw
store (14,073 rows against 14,073 sample records) and every row recomputes to
$4.667639 with no disagreements, so it is internally consistent and
reproducible. Together documents no balance or usage endpoint, and a dashboard
reading of the remaining balance ($1.16 on 2026-08-14) cannot close the loop:
a balance alone cannot distinguish an undercounting ledger from an unrecorded
starting figure. **Provider total spend, to compare against $4.667639:**
`[BLANK]`. Until that is recorded the bill is described as computed and
unconfirmed, and we note that the predecessor's unverifiable $3.9234 is the
failure this is trying not to repeat.

### 4.5 Comparability is keyed on answer rate, not on matched caps

Two models at the same cap with different length distributions produce two
different output populations wearing one benchmark's name. MiniMax-M2.7 at the
published 2048 answers 0.2649; comparing its answered samples against Qwen's
near-complete ones compares two different sets of problems.

**Rule.** Two conditions are comparable when their answer rates match, and the
answer rate is published beside every accuracy. Enforced by a test over both
structured artifacts and prose tables in this repository.

This differs from the post-hoc filtering used in arXiv:2608.12150 in when it
applies: it is a design constraint on what to sample, not a repair applied to
an existing comparison. Section 5 is what happened when we applied it to
ourselves.

### 4.6 Projecting cost from a small probe

Mean completion length is a per-problem property at **119.66 times** the
variance a homogeneous null produces. A probe over k problems therefore
inherits that between-problem spread, and taking more samples per problem does
not reduce it.

Resampling the 198 per-problem means, 20,000 trials per k:

| k problems | median error | 5th percentile | uplift for 95% coverage |
|---|---|---|---|
| 4 | -1.21% | -25.87% | 34.9% |
| 8 | -0.53% | -18.53% | **22.7%** |
| 16 | -0.35% | -13.20% | 15.2% |
| 32 | -0.17% | -9.10% | 10.0% |

Probes are near-unbiased in the median, yet just over half underestimate at
every k, because per-problem means are right-skewed. **A ceiling set at the
projection is therefore wrong about half the time**; it is set at the
calibrated upper bound for the k actually used.

## 5. When the rule rejected our own registered result

The second-model replication, registered as
`argmax-prereg-margin-desc-v2.0` and **not evaluated**.

MD3 and MD4 restated the section 2 mechanism keyed on correctness rather than
plurality, with thresholds 15.0 nats and 0.60 set below the v1 exposed
estimates of 21.5365 and 0.7617 so that each was a prediction. The tag was cut
before any confirmatory sample existed. A stratification check found no
dependence of either quantity on per-problem accuracy, so the thresholds were
held rather than recalibrated.

**Cap selection failed, and not randomly.** A 32-sample probe at cap 6144
measured answer rate 1.0000 and truncation 0.0000. The run measured **0.8931**
[0.8747, 0.9090] and truncation **0.2905**, with mean completion 65.3 percent
above projection.

Config drift was ruled out before the selection explanation was accepted: one
`param_hash` across all 1,253 samples, matching the thinking-off configuration;
zero nonzero reasoning-token counts; cap 6144 throughout.

The cause is measurable because the sampler iterates problem-major and so
re-sampled the probe's own problems first:

| problems, iteration order | n | mean completion | truncation |
|---|---|---|---|
| **the 8 probe problems** | 128 | **2082.9** | 0.0312 |
| every other problem reached | 1,125 | **3546.4** | 0.3200 |

The probe reproduced itself and was **precise about an unrepresentative
slice**: the rest of the benchmark runs 1.703 times longer. The k=8 uplift of
22.7 percent could not have covered a 65.3 percent error, because that table
describes a **random** draw of 8 problems and a fixed lowest-id slice is not
one. Its error is not resampleable, because there is one such slice and it is
the same every time.

**Consequence.** At 29 percent truncation, the pool that would be scored is
selected for finishing fastest, and those samples are missing non-randomly.
Scoring them would produce a number about the subset of samples that fit inside
6144 tokens and report it as a number about the model, which is the confound
sections 3 and 4.5 exist to prevent. **MD3 and MD4 are therefore registered and
unevaluated.** They are not withdrawn and not falsified.

Nor was the replication recoverable at a different cap. A right-censored fit
to the 1,253 samples puts the cap required for the registered 0.9950 answer
rate near 41,000 output tokens and the corresponding run at about $4.19, with
$1.16 remaining. Even a 0.95 rate, which would still fail the condition,
requires roughly 16,268 tokens and $3.84. **The replication was not lost by
choosing 6144; it was not purchasable at any cap on this budget.** The
extrapolation is long and mildly optimistic about completion, which pushes the
required cap up rather than down; the conclusion does not depend on it, since
even a 16,384 cap chosen without any fitting exceeds the balance.

A random-draw cap probe at 8192 and 12288 was specified and costed and **not
run**. No measurements exist at those caps.

**The point.** A methodological rule that never rejects anything is decoration.
This one rejected a result its own authors had registered, sampled and paid
for, and the alternative was a single dropped footnote away.

## 6. Thread A

A reconstructed few-sample estimator, registered at
`argmax-prereg-threadA-v1.0`, evaluated on the predecessor's confirmatory 151
problems. Paired per-problem regret difference, estimator minus naive baseline;
negative favours the estimator.

| id | k | difference | 95% CI | verdict |
|---|---|---|---|---|
| **TA1** | 8 | **-0.0213** | [-0.0335, -0.0091] | **PASS** |
| TA2a | 4 | -0.0186 | [-0.0332, -0.0041] | PASS, registered as underpowered |
| TA2b | 16 | -0.0040 | [-0.0085, +0.0004] | **FAIL** |

TA1 passes by more than the resolution that produced it: the registered floor
`ta1_resolution_floor` is 0.0161 against an observed 0.0213. **TA2b fails by
0.0004**, and is reported as a failure rather than rounded into the pattern of
the other two.

A shrinkage baseline was added **post hoc** and is labelled as such throughout:
at k = 4 and k = 16 every shrinkage strength is worse than the plain baseline,
and at k = 8 the weakest shrinkage helps slightly. It is not registered and
decides nothing.

## 7. Corrections and disclosures

Recorded as a section rather than a footnote.

1. **A superseded predecessor draft was cited** in place of the published
   preprint, and its headline numbers disagree. A falsification test now scans
   every document in the repository for citations to superseded drafts.
2. **Three per-problem properties were described as independent** before being
   tested. Within one model at n = 127, per-problem accuracy against the
   sub-2-nat margin tail gives -0.2614 [-0.3912, -0.1156], excluding zero. The
   one-factor reading rested on three correlations near 0.3 at n = 30 with
   every interval crossing zero, one of which used a cross-model length proxy.
   Both readings are retained with their sample sizes.
3. **The margin-v1 run changed concurrency mid-run**, and because the sampler
   iterates problem-major the resulting regime comparison is between problems
   rather than within them. It is reported as confounded and decides nothing.
   Three manifests are marked `reconstructed` rather than contemporaneous.
4. **An option-order claim was corrected after tagging.** Options are shuffled
   by `random.Random(row_index)`, reproducing the predecessor's shuffle;
   `prompt_hash` is equal across both model stores for all 198 problems,
   verified.
5. **The answer-rate pairing rule did not cover prose tables** until a quintile
   table of accuracies was published in a note without them. The rule and its
   test now cover markdown.
6. **The v2 cap was chosen from 8 non-random problems**, giving the failure in
   section 5. Probe problems are now drawn at random with a recorded seed.

## 8. Limitations

- **One benchmark**, GPQA Diamond, 198 problems.
- **The reasoning wall is a serverless result.** All three models are
  downloadable, and on fixed-cost compute the caps that defeated us are
  affordable. The section bounds what a metered API buys at this budget, not
  what is knowable.
- **One model** for the registered claims. The second-model replication was
  registered, sampled and could not be evaluated (section 5). Cross-family
  replication was never purchasable: four of five priced candidates in the 7 to
  9B range refused serverless requests.
- **Total spend under $6.** Stated because several design choices are
  unintelligible without it.
- **The bill is unconfirmed by the provider** (section 4.4).
- An exploratory **U-shaped relationship between per-problem completion length
  and accuracy** (0.4441, 0.3400, 0.2218, 0.3316, 0.4098 by length quintile)
  is suggestive and **not established**: the shape-agnostic quadratic term
  gives p = 0.083. Two mechanisms were ruled out, truncation selection and
  within-problem bimodality. It was found on an already-exposed set with its
  sharpest contrast chosen after inspection, and it appears here rather than in
  results for that reason.

## What is not in this draft, and why

- **No compute-matched comparison sentence.** Doc 2 requires each to carry a
  `claim_id` resolving to rows in the `budget_matched` table. No such rows
  exist, so no such sentence is written.
- **No MD3 or MD4 verdict.** Section 5.
- **No abstract.** Written last, from the body.
- **No provider-confirmed spend total.** `[BLANK]` in section 4.4.
