# Outline: v2 of arXiv:2608.11403

Ordered by what survived `notes/prior_work.md`, not by the order the work was
done. **Every verdict is a blank.** A number appears below only where it is
already computed, registered and reported; anything from the margin-v2 store
carries its resolution explicitly. The margin-v2 store produced no evaluable
verdict, for the reason recorded in `notes/v2_comparability_failure.md`, so
there is nothing left pending from it.

Working title, to be replaced: *Where the disagreement lives: localized
confidence does not resolve self-consistency's failures on hard problems.*

## Framing, decided by the prior-work search

The v1 paper's result was that majority vote hurts the majority of hard
science problems for small models. The obvious follow-up is "so use a
confidence signal to decide when to vote", and this paper is the negative
answer to that, made carefully enough to be worth having.

**Lead with commitment. Demote dilution to methods.** Three papers already
own the dilution observation and the localization fix. What is not owned is
that localization, done properly, still does not help, because the answer
token is saturated whether the sample is in the majority or the minority.

## 1. Introduction

- v1 established backfire at 56.6 and 65.7 percent of problems on two models.
  Cite as prior, not as contribution.
- The natural fix: gate on confidence. State the fix, state that this paper
  tests it and it does not work, in the abstract.
- Contributions, in order:
  1. A registered, held-out **commitment** result, on **one model**:
     dissenting samples are as saturated as agreeing ones.
  2. The **reasoning wall**, three models measured, with the bill.
  3. A **methodological rule**: comparability keys on answer rate, not on
     matched caps, with a test enforcing it.
  4. Thread A, a negative result on a reconstructed estimator.

## 2. The commitment result (LEAD)

The registered claims, pre-registered at `argmax-prereg-margin-desc-v1.0`
before the holdout was read.

| | reported |
|---|---|
| MD1, median margin among dissenting samples | 20.5232, one-sided 95 percent lower bound 18.8376, threshold 15.0, **PASS** |
| MD2, fraction above 10 nats among dissenting | 0.7567, bound 0.7105, threshold 0.60, **PASS** |
| problems clearing the three-dissenter floor | 64 of 69 |
| answer rate on the store | 0.9950 [0.9936, 0.9961] |

- Exposed set reproduces the holdout closely, 20.52 against 20.62 and 0.757
  against 0.749. Report both, say which was registered.
- **The reading**: a sample contradicting its own problem's plurality still
  emits that answer at roughly 800 million to one. The disagreement self
  consistency exploits is not at the answer token. It is upstream, in which
  chain got written.
- **The honest counterweight, in the same subsection, not buried**: the
  fraction above 10 nats does separate correct from incorrect samples,
  +0.0589 with an interval excluding zero. Across-sample discrimination is
  real and small. The claim is about the within-problem routing decision.
- **Engage arXiv:2606.29490 here, not in related work.** Cal-LP is the same
  quantity at the same locus and reaches AUROC 0.62 to 0.80 across questions.
  We agree with it on its unit. State the unit difference explicitly:
  across-question discrimination against within-question routing.

### 2.1 There is no second model. Say so here, once.

**The risk this section previously carried as open is now the outcome.** The
second-model replication was registered, sampled, and could not be evaluated.
It moves to section 4.3 as a comparability failure, which is where it is
informative.

What section 2 must therefore state plainly, in the results and again in the
abstract: **the commitment result rests on one model.** Qwen2.5-7B-Instruct,
198 GPQA Diamond problems, 12,672 samples, with the claims decided on a
69-problem holdout no exploratory analysis had read. Not two models, not a
family, not a replication. A registered, held-out, single-model result.

Do not soften this with "preliminary" or "we expect it to generalise". The
reason there is no second model is itself reported, in 4.3, and it is a
better sentence than any hedge.

MD3 and MD4 remain **registered and unevaluated** under
`argmax-prereg-margin-desc-v2.0`. If a reader looks up the tag they must find
the reason, so the tag is cited here and resolved in 4.3.

## 3. Mechanism and instrumentation (METHODS, not results)

Everything the prior-work search showed is owned. Two pages at most.

- **Dilution, two sentences and citations.** Averaging over 613 tokens with
  one answer token measures fluency. Cite SAR (arXiv:2307.01379) for the
  premise, Murray and Chiang (arXiv:1808.10006) for the root, and
  arXiv:2505.19060 for length-invariant estimation. Do not present it as a
  finding.
- **What it buys us**: it rules out "you measured in the wrong place" as the
  explanation for the negative result in section 2. That is the only reason
  it is in the paper.
- The margin definition and its **censoring rule**: measured when two or more
  option letters are in the top k, right-censored at `top - kth` otherwise,
  never imputed. Report 12,344 measured and 265 censored.
- Cite CIKM 2025 "One-Token Deep" for the same locus and a different claim.
- **The two-shape logprob defect**, briefly, as a reproducibility note:
  response shape is a property of the model, not the provider, and a parser
  validated on one model is unvalidated on the next.

## 4. The reasoning wall (OWN SECTION)

Reframed after the search. Not "reasoning models cannot be evaluated
cheaply", which overclaims, but the excluded region measured.

- **Open by citing arXiv:2608.12150.** Budget-dependent rankings on GPQA
  Diamond at 198 items, reversals at p < 0.01, three-tier truncation
  analysis. It is the stronger paper on the general claim and it
  **deliberately excludes reasoning-native models** because `max_tokens`
  semantics change for them. That exclusion is this section's subject.
- Three models, three measured walls, each by real request:

| model | wall | measured |
|---|---|---|
| QwQ-32B | unreachable | `model_not_available`, no serverless route |
| MiniMax-M2.7 | never at a comparable cap | 0.6460 at 16,384; 0.2649 at the published 2048 |
| Qwen3.5-9B | nothing at any affordable cap | 0.0000 at 2048 and 4096, mean completion equal to the cap exactly; 0.5938 at 8192 |

Reference: Qwen2.5-7B at 2048 answers 0.9950 over 12,672 samples.

- **The door**: two thinking controls honoured and indistinguishable. Then
  the point that matters, that a reasoning model with reasoning disabled is a
  second non-reasoning model, so the purchasable replication is not the one
  wanted.
- **The bill.** 148 probe samples, $0.1347 against a $0.15 ceiling, against
  $1.79 projected for the run itself; $4.6676 realized across all phases.
  arXiv:2608.12150 reports 56,476 API calls and no monetary cost. Argue that
  reporting the cost of a negative is itself the contribution, in a
  literature where a single multi-model effort runs to $40,000.
- **Caveat the bill honestly, or it repeats the failure it criticises.** The
  ledger is complete against the raw store (14,073 = 14,073) and every row
  recomputes from `usage_raw` and its named snapshot to the cent. It is
  **not** provider-confirmed: Together documents no balance or usage
  endpoint, and the dashboard is the only source. Either a human records the
  dashboard figures beside the ledger before submission, or the paper says
  plainly that the bill is a computed estimate reconciled against itself.
  Citing the predecessor's unverifiable $3.9234 while presenting an
  unverified figure is not available.
- The probe caught the null-margin defect before 3,168 samples inherited it.

### 4.1 Comparability keys on answer rate, not on matched caps

The rule, with the test behind it. Distinguish from arXiv:2608.12150's
three-tier filtering: theirs is applied post hoc to an existing comparison,
ours is a design constraint applied before sampling, which is why v2 was
sampled at 6144 against v1's 2048. It did not succeed, and 4.3 reports that
as the section's main result rather than as an aside.

### 4.2 Projections from small probes

The calibration: between-problem variance of mean completion length at
119.66x a homogeneous null, so a k-problem probe carries that spread and not
sampling noise. Uplift for 95 percent coverage: 34.9 percent at k=4, 22.7 at
k=8, 15.2 at k=16, 10.0 at k=32. Report both underestimates, 5.4 and 13.8
percent, **and the v2 run's own overrun**, which at +65.3 percent on mean
completion is far outside the k=8 spread and is the strongest single argument
for drawing probe problems at random rather than by lowest id.

### 4.3 A fourth wall: the rule cost us a registered replication

The strongest material in the paper, because it is the only place the
methodology is shown paying its own price rather than being recommended.
Full detail in `notes/v2_comparability_failure.md`.

- Registered at `argmax-prereg-margin-desc-v2.0`, tagged before any
  confirmatory sample existed, thresholds held at 15.0 and 0.60 after a
  stratification check found no accuracy dependence.
- Cap 6144 chosen under the section 4.1 rule from a 32-sample probe measuring
  answer rate **1.0000**, truncation **0.0000**.
- The run: answer rate **0.8931** [0.8747, 0.9090], truncation **0.2905**,
  mean completion **+65.3 percent**, over 1,253 samples on 79 problems.
- **Config drift ruled out first**: one `param_hash` across all 1,253 samples
  matching the thinking-off config, zero nonzero `reasoning_tokens`, cap 6144
  throughout. The instrument was correct.
- **The cause, measured**: the sampler re-sampled the probe's own 8 problems
  first, and they reproduce the probe at 2082.9 mean completion and 0.0312
  truncation, against **3546.4 and 0.3200 for the other 1,125 samples**. The
  rest of the benchmark is **1.703x** the probe set. The probe was precise
  about an unrepresentative slice.
- **Why the k=8 uplift of 22.7 percent did not cover a 65.3 percent error**:
  that table describes a *random* draw of 8 problems. A fixed lowest-id slice
  is not a random draw and its error is not resampleable, because there is one
  such slice and it is the same one every time.
- **The decision**: MD3 and MD4 are registered and **not evaluated**. At 29
  percent truncation the scored pool is selected for finishing fastest, which
  is the confound sections 4.1 and 3 exist to prevent. Evaluating them would
  have broken, in this paper, the rule this paper argues for.
- The money made it moot anyway: $1.71 to finish against a reconstructed
  balance of $1.29 to $1.43.

**Land the point explicitly.** A methodological rule that never rejects
anything is decoration. This one rejected a result its own authors had
registered, sampled and paid for, and the alternative was one footnote away.

## 5. Thread A

Negative result on a reconstructed few-sample estimator, registered at
`argmax-prereg-threadA-v1.0`. Verdicts `[PENDING WRITE-UP]`, they exist in
`notes/thread_a.md` and go in from there, not from memory. Include the
post-hoc shrinkage baseline **labelled post hoc**, and the resolution floor
of 0.0161 so a pass smaller than its own resolution is visible as such.

## 6. Corrections and disclosures

A real section, not a footnote. From `files/01-prd.md`'s disclosure list plus
what has accumulated:

1. The superseded-draft citation, and the falsification test now enforcing
   citation provenance.
2. Three per-problem properties described as independent when the within-model
   correlation is -0.2614 [-0.3912, -0.1156]. Doc 2 section 7.2.1 carries
   both readings with sample sizes.
3. The margin-v1 concurrency change mid-run, the resulting between-problem
   confound, and the three manifests marked `reconstructed`.
4. The option-order claim corrected after tagging, with `prompt_hash` equal
   across both stores for all 198 verified.
5. The answer-rate pairing rule not covering notes until a quintile table fell
   through the gap.
6. The v2 cap chosen from 8 non-random problems, the resulting 0.8931 answer
   rate against a registered 0.9950, and MD3/MD4 left registered and
   unevaluated. Cross-reference 4.3.

## 7. Limitations

- One benchmark, GPQA Diamond, 198 problems.
- **One model.** The second-model replication was registered, sampled and
  could not be evaluated (4.3). Cross-family replication was never purchasable
  either: four of five priced candidates refused serverless requests.
- Total spend under $6. State it. It is the reason for several design choices
  and hiding it would make those choices look arbitrary.
- The completion-length U (accuracy 0.4441, 0.3400, 0.2218, 0.3316, 0.4098 by
  length quintile) is **exploratory, suggestive, and not established** at
  quadratic p = 0.083. Two mechanisms ruled out, truncation selection and
  within-problem bimodality. It goes in limitations or future work, never in
  results, and the reader is told it was found on an exposed set with its
  sharpest contrast chosen after the fact.

## What must be true before drafting prose

1. DONE. The v2 decision is recorded in `notes/v2_comparability_failure.md`:
   registered, unevaluated, cause measured.
2. Every `[PENDING]` above resolves to a number produced by `derive.py` and
   checked by the falsification suite.
3. Every compute-matched sentence carries a `claim_id` resolving to rows in
   `budget_matched`. No claim is registered without rows.
