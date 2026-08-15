# When Self-Consistency Backfires, v2

**Draft, v2 of arXiv:2608.11403.** Merged manuscript: the original's results
carried over, its interpretation revised, new sections integrated.

**Status of numbers.** Every figure is either quoted from v1 (marked as such
and not recomputed), produced by `derive.py` from the stored raw records, or
marked `[BLANK]`. A `[BLANK]` marks a quantity this project does not have.
No sentence describing a compute-matched comparison appears anywhere, because
no `budget_matched` rows exist and doc 2 forbids writing one without them.

v1 read from `paper/backfire_preprint.pdf`, cited as arXiv:2608.11403.

**Data availability.** Derived, question-free data reproducing every number in
this paper is archived open access at **10.5281/zenodo.21933418** (CC BY 4.0). The raw per-sample
store, including model chains of thought, is archived at **10.5281/zenodo.21933422** as a
**restricted, request-access** record, on the same terms as GPQA; it is not
open data, for the reason given in section 5.6.

---

## Abstract

Self-consistency by majority vote reduces per-problem accuracy on most GPQA
Diamond problems for small instruction-tuned models: 56.6 percent of problems
for Qwen2.5-7B and 65.7 percent for Llama-3-8B. The obvious remedy is a
verifier-free confidence gate that decides which problems to vote on. This
paper reports that the most natural repair to that remedy also fails, and
separates three signal failures that v1 treated as one.

A token-entropy gate fails for a measurement reason rather than a substantive
one: a per-token average over a chain averaging 602 tokens is dominated by
fluency. Measured, the chain average sits 0.0005 nats from the average over
non-answer tokens and 0.1695 nats from the answer token's own value. We therefore measure confidence
at the answer span itself, where that dilution cannot apply. **On
Qwen2.5-7B-Instruct-Turbo, 198 problems at 64 samples each, a sample whose
answer contradicts its own problem's plurality still emits that answer at a
median margin of 20.52 nats, with 75.7 percent of such samples above 10 nats.**
Both quantities were pre-registered with thresholds fixed in advance and tested
once on 69 problems that no exploratory analysis had read; both passed. **The
unit is the whole result.** Pooled across the benchmark the same margin does
separate correct from incorrect samples, by +0.0604 on the fraction above 10
nats [+0.0183, +0.1017], excluding zero; measured within each problem and
paired across its own samples it does not, at -0.0168 [-0.0527, +0.0182],
crossing zero. So the claim is not that token log-probabilities carry no
information. It is that a signal with genuine across-question discrimination
is close to useless for the **within-question** decision self-consistency
actually poses: which of several disagreeing samples of the same problem to
trust. The disagreement lives
upstream, in which chain was written, and the answer token reads out a chain
that has already committed. **We did not find this result in our search of the
prior literature**, though the dilution it corrects for, and the practice of
measuring at the answer span, are both established.

The plurality-agreement gate's failure, unlike the other two, remains without a
mechanism. It is not token-level, so neither dilution nor saturation explains
it, and we report it as an open problem rather than absorbing it into an
account that does not cover it.

These new claims rest on **one model**. A registered second-model replication
was sampled and could not be evaluated: its cap was selected from a probe of
eight non-random problems that proved unrepresentative, the run's answer rate
came in at 0.8931 against a registered comparability condition of 0.9950, and
scoring a pool selected for finishing fastest would have violated the rule this
paper argues for. We report that rejection rather than the result.

We separately report that on **hosted serverless inference at a small budget**,
three reasoning-native models could not be evaluated at all, for three distinct
and separately measured reasons: no serverless route at any price, no
comparable answer rate at any affordable cap, and zero extractable answers with
generation consuming the entire budget. All three models are downloadable, so
this bounds what a metered per-token API buys rather than what is knowable, and
we name open weights on fixed-cost compute as the route a follow-up should
take. Total project spend was $4.67, itemised. Derived data is archived openly at
10.5281/zenodo.21933418; the raw store is archived at 10.5281/zenodo.21933422 under request-access.

## Changes from v1

For readers who cited the original. **The headline results are unchanged. What
moved is the explanation of why the gates fail.**

### Corrections to claims made in v1

| v1 claim | status in v2 | why |
|---|---|---|
| §4.4 title and thesis, "confidence does not track correctness" | **CORRECTED** | v1 inferred one mechanism from two gates failing together. The failures have different causes and one of them is a measurement artefact. See §4.4. |
| §5, "Both gates read confidence, but confidence on these problems does not indicate correctness" | **CORRECTED, narrowed to a unit** | False as stated across questions: pooled, the answer-token margin separates correct from incorrect by +0.0604 [+0.0183, +0.1017], and independent work reports AUROC 0.62 to 0.80 for the same quantity across questions. Within a problem, paired, it does not: -0.0168 [-0.0527, +0.0182]. The defensible claim is the within-question one. |
| Abstract, "we do not test reasoning-native models, which we flag as the central open question" | **PARTLY ANSWERED, and rescoped** | Not open in the same way: on hosted serverless inference at a small budget it is unmeasurable, and §5 reports three separately measured walls. It remains open for the open-weights route. |
| §6 Limitations, the entropy gate's failure grouped with agreement's under one "known mechanism" | **SEPARATED** | The entropy gate was reading a diluted statistic. That is miscounted evidence, not evidence about confidence. |

### Additions

| new material | section |
|---|---|
| Answer-token margin, the "richer signal" v1's Limitations named as future work | §4.4, §4.5 |
| The reasoning wall, three models, scoped to hosted serverless inference | §5 |
| A registered replication that the paper's own comparability rule rejected | §6 |
| Thread A, a reconstructed few-sample estimator | §7 |
| Corrections and disclosures | §10 |

**v2 closes a limitation v1 stated about itself.** v1's Limitations said:
"Richer signals such as final-answer log-probability margins or confidence
dynamics across samples could behave differently, and our negative result does
not rule them out. Evaluating final-answer margins requires per-token
log-probability arrays, which our pipeline did not store." This paper stores
them and evaluates that signal. It does not behave differently in the way that
sentence hoped.

### Unchanged

Every result in §3, §4.1, §4.2 and §4.3, all pre-registered verdicts from v1,
and every number in Tables 1, 2 and 3. **No v1 result was recomputed,
re-estimated, or withdrawn.** v2 adds a run; it does not revise v1's data.

---

## 1. Introduction

*(v1 text, retained; two paragraphs added at the end.)*

Inference-time compute is a primary lever for LLM reasoning, and
self-consistency, sample several chains of thought and return the plurality
answer, is among the simplest and most widely used techniques in this family
(Wang et al., 2023). It is commonly assumed to be a low-risk accuracy boost.

That assumption fails on hard problems. When a model places its highest
probability on an incorrect answer across independent samples, more samples
only entrench the wrong vote. We call this backfire. We then ask the question a
cost-conscious practitioner would ask: can a cheap, verifier-free signal
computed from a few samples tell you which problems to vote on and which to
skip?

**New in v2.** v1 tested two such signals, plurality agreement and token-level
entropy, found both fail, and offered one explanation for both. This version
tests a third, the answer-token log-probability margin, which v1's own
Limitations named as the obvious next candidate and could not evaluate because
its pipeline stored only a mean entropy scalar. We collect the per-token
arrays, measure the margin at the answer span, and report that it also fails.

The three failures do not share an explanation, and separating them is the main
interpretive change in this version. One is a measurement artefact, one has a
mechanism we can state and test, and one remains unexplained.

## 2. Setup

*(v1 text, retained in substance; a new subsection added for the margin
instrumentation.)*

**Dataset and design.** The full GPQA Diamond benchmark (Rein et al., 2024),
198 graduate-level multiple-choice questions in biology, chemistry and physics.
Pre-registered confirmatory design: 47 problems exploratory, 151 confirmatory.
Hypotheses and thresholds locked and git-tagged before any confirmatory
analysis, at `backfire-prereg-v1.0`. Exploratory, confirmatory and pooled
values are reported throughout; PASS/FAIL is decided on the confirmatory set
only.

**Models.** Two instruction-tuned models from different families, served on
Together AI: Qwen2.5-7B-Instruct-Turbo and Meta-Llama-3-8B-Instruct-Lite. Both
small (7 to 8B) and non-reasoning. N = 64 samples per problem, temperature 0.7,
a single locked prompt template byte-identical across runs as verified by
SHA-256. Five-pass answer extraction; parse rate 99.5 percent (Qwen) and 98.6
percent (Llama).

**Metrics, routing and gates, uncertainty.** As v1: `MV acc(N)` is expected
majority-vote accuracy over N samples with ties broken uniformly at random,
estimated by Monte Carlo. Backfire is `mv_gain < 0`. The oracle routes each
problem to the best N across {1, 2, 4, 8, 16, 32, 64} using ground truth and is
an upper bound, not a deployable method. The agreement gate returns the probe
plurality when its fraction over k samples is at least tau, else votes at
N = 64. The entropy gate returns the probe plurality when mean per-token
entropy over k = 4 probe samples falls below a threshold, else votes at N = 64.
95 percent intervals are problem-level bootstrap, 1000 iterations, seed 42.

### 2.1 New in v2: the answer-token margin

v1 retained only a mean per-token entropy scalar, which is why it could not
evaluate a margin. This version re-samples Qwen2.5-7B-Instruct-Turbo on all
198 problems at M = 64, cap 2048, requesting log-probabilities at depth 5, and
stores the full response object. 12,672 samples.

The **answer-token margin** is the log-probability of the emitted option letter
minus that of the highest-scoring alternative option letter, at the answer
position.

**Censoring.** The provider returns the top k alternatives per token, k = 5 in
practice, and five slots need not contain every option letter.

- **Two or more option letters present: measured.** The second-highest present
  option is a returned value and any absent letter lies at or below the
  smallest returned value, so no absent letter can outrank it. The margin is
  exact.
- **Fewer than two present: right-censored** at the top letter minus the
  smallest returned log-probability, and recorded as a bound.
- **Never imputed.** Filling a missing letter at the censoring bound would
  understate the margin exactly on the problems where the model is most
  certain, which are the ones a confidence gate cares about most.

**12,344 measured, 265 right-censored, and 63 with no margin at all**, summing
to 12,672. The 63 are exactly the samples from which no answer was extracted:
with no answer span there is no answer token to measure at. They are the same
63 that give the answer rate of 0.9950, they are recorded rather than dropped,
and they are never scored as incorrect.

**Comparability with v1's runs.** The new run's answer rate is 0.9950 [0.9936,
0.9961] against v1's published 0.9946 [0.9932, 0.9958] for the same model, a
difference of 0.0004 with almost entirely overlapping intervals. The two runs
therefore describe the same output population, not merely the same prompts.

**Split discipline for the new claims.** Exposure was tracked per analysis: 129
problems were read by some exploratory analysis and 69 were not. The claims in
§4.5 were registered with thresholds fixed, at
`argmax-prereg-margin-desc-v1.0`, before those 69 were examined, and were
examined once.

## 3. Pre-Registered Confirmatory Results

*(v1, UNCHANGED. No number in this section was recomputed.)*

All four pre-registered hypotheses pass on the 151 confirmatory problems.
Thresholds were fixed before any confirmatory analysis and set with margin on
the permissive side of the exploratory point estimates rather than at them, so
each is a genuine prediction rather than a restatement.

| Hyp | Prediction (both models) | Qwen2.5-7B | Llama-3-8B | Result |
|---|---|---|---|---|
| PH1 | backfire rate >= 33% | 60.3% [53.0, 68.2] | 65.6% [58.3, 73.5] | PASS |
| PH2 | agree gate capture <= 10% | 0.8% [-89.1, 68.1] | -1.6% [-92.9, 74.2] | PASS |
| PH3 | top-agree-bin acc. <= 70% | 51.2% (n=43) | 14.3% (n=21) | PASS |
| PH4 | entropy gate capture <= 10% | 0.5% | 0.9% | PASS |

Table 1: Confirmatory hypotheses (n = 151). Captures here are measured against
the binary {N = 1, N = 64} oracle relative to an `MV acc(64)` baseline, which
is why they are much smaller than the grid-oracle captures in §4.3. PH2's
intervals are wide enough to be consistent with capture well above the 10
percent threshold: the pre-registered decision rule is on the point estimate,
and the intervals are reported alongside it.

## 4. Results

### 4.1 Backfire affects the majority of problems, precisely estimated

*(v1, UNCHANGED.)*

Pooled backfire rate 56.6 percent [49.5, 63.6] for Qwen and 65.7 percent
[59.1, 71.7] for Llama. Expanding from 47 to 198 problems roughly halved the
interval width and both rates sit well above the 33 percent threshold.

**The aggregate and per-problem pictures diverge.** Voting barely moves
aggregate accuracy (Qwen 0.342 to 0.369, Llama 0.273 to 0.313) while harming
the majority of problems individually. The worst single problem loses 47 points
(Qwen) or 46 (Llama); a few gain as much as 66 or 70. The asymmetry is real but
rare.

| Domain | Qwen n | Qwen backfire | Llama n | Llama backfire |
|---|---|---|---|---|
| Biology | 19 | 36.8% | 19 | 42.1% |
| Chemistry | 93 | 66.7% | 93 | 68.8% |
| Physics | 86 | 50.0% | 86 | 67.4% |
| Pooled | 198 | 56.6% | 198 | 65.7% |

Table 2: Per-domain backfire rate (pooled 198). Reported descriptively; the
per-domain counts, biology especially, are too small to support claims about
why backfire concentrates where it does.

### 4.2 The oracle upper bound is real but not reachable

*(v1 results UNCHANGED; one caveat added.)*

A grid oracle routing each problem to the best majority-vote accuracy across N
in {1, 2, 4, 8, 16, 32, 64} reaches 0.482 (Qwen) and 0.439 (Llama), a ceiling
14 points above N = 1 for Qwen and 17 for Llama. It marks how much accuracy a
perfect per-problem routing decision could recover. It is an upper bound, not a
method.

**Added in v2.** That headroom is entirely per-problem and must not be read as
aggregate. Measured on the confirmatory 151, the whole aggregate accuracy curve
across the grid spans **0.52 accuracy points**. A reader who takes 14 to 17
points as recoverable aggregate headroom has misread the quantity: the ceiling
comes from routing individual problems in opposite directions, and those
movements very nearly cancel in the mean.

### 4.3 Two verifier-free gates fail to capture it

*(v1, UNCHANGED. The title still says two: v2 adds a third **signal**, not a
third gate, and builds no margin gate. See §4.4.)*

Neither cheap gate recovers the headroom. The agreement gate (k = 8, tau =
0.75) reaches 0.368 accuracy for Qwen and 0.312 for Llama against 0.369 and
0.313 for fixed-budget voting at N = 64, differences of 0.0006 and 0.0014. We
report these magnitudes rather than a significance claim, having computed no
paired test.

Measured against `MV acc(1)`, the agreement gate captures 18.7 percent of
available grid-oracle headroom for Qwen and 23.4 percent for Llama. Those
figures credit the gate with headroom that voting alone already recovers.
Measured against `MV acc(64)`, which isolates what the routing decision adds
over simply voting, capture is PH2 in Table 1: 0.8 percent for Qwen and -1.6
percent for Llama. **What the gate buys relative to a flat N = 64 is compute,
not accuracy.**

Every gate-versus-baseline comparison uses fixed-budget voting at a flat
N = 64. **We do not compute a compute-matched baseline**, in v1 or in v2.

The entropy gate is evaluated entirely within the confirmatory 151, since
log-probabilities existed only for that split. Its threshold was selected
in-sample on that same set, so its reported capture is optimistic. It captures
0.2 percent of grid-oracle headroom for Qwen and 31.2 percent for Llama. Mean
per-token entropy modestly predicts which problems backfire (AUC 0.631 Qwen,
0.523 Llama), but predictive signal does not translate into routing accuracy,
because the gate cannot act on it without misclassifying enough problems to
erase the gain. Across all 22 operating points swept, none beats fixed-budget
meaningfully.

### 4.4 Why: three signals, three different failures

**This section replaces v1's §4.4, "Why: confidence does not track
correctness".** v1 offered a single account for two failing gates. With a third
signal measured, that account no longer holds as stated: the three failures
have three different statuses, and only one of them is explained by
miscalibration.

#### Signal 1: plurality agreement. Fails, and we cannot say why.

*(v1 evidence, UNCHANGED.)*

| Confidence bin | Qwen n | Qwen frac correct | Llama n | Llama frac correct |
|---|---|---|---|---|
| [0.25, 0.50) | 56 | 33.9% | 79 | 30.4% |
| [0.50, 0.75) | 83 | 27.7% | 84 | 33.3% |
| [0.75, 1.00] | 59 | 52.5% | 35 | 28.6% |

Table 3: Calibration by agreement bin (pooled 198). Confidence is the plurality
fraction over all samples.

Even the highest-agreement bin is far from reliable: Qwen's plurality is
correct 52.5 percent of the time there, and Llama's only 28.6 percent, lower
than its own low-agreement bin. Llama's accuracy is not monotone in agreement,
rising then falling across the three bins.

**What v2 changes here is the status of the explanation, not the evidence.**
Plurality agreement is computed over *answers*, not over tokens. Neither
dilution nor answer-token saturation can apply to it: it never touches a
log-probability. The account developed below for the other two signals
therefore says nothing about this one.

**Agreement's failure remains without a mechanism, and we state that as an open
problem rather than absorbing it.** We can describe it, in Table 3, and we
cannot explain it. Calling it an instance of general overconfidence, as v1 did,
is a label rather than an account: it does not predict that Llama's top bin
should be *worse* than its bottom one, and it does not say what would have to
be true for agreement to work on some other benchmark. **This is the largest
unresolved question in the paper**, and it is as unresolved in v2 as in v1. The
difference is that v1's framing made it look answered.

#### Signal 2: mean token entropy. Miscounted evidence, not evidence about confidence.

The entropy gate averaged a per-token quantity over the whole chain. In the
margin-v1 store that chain averages **602.21 tokens**, of which the answer
token is **one**. (v1's own figure of roughly 613 is from the predecessor's
store; the two are the same model at the same cap and the small difference is
not load-bearing.)

**Measured rather than asserted**, over 2,560 samples on 40 problems drawn with
a recorded seed, using per-token entropy over the returned top-5 alternatives:

| quantity | nats |
|---|---|
| mean over the **whole chain**, which is what the gate thresholded | **0.2232** |
| mean over **non-answer tokens** | **0.2237** |
| at the **answer token** | **0.0536** (median **0.0000**) |

The chain average sits **0.0005 nats** from the non-answer average and
**0.1695 nats** from the answer token's own value. The answer token is
0.1700 nats below the prose it is averaged with [-0.1778, -0.1619].

So the gate's statistic is, to four decimal places, a measurement of the prose.
A gate thresholding it is thresholding fluency. The answer token's median
entropy of exactly zero is the same saturation that §4.5 registers, visible in
a second statistic.

**This is a measurement artefact and should not be reported as a fact about
confidence.** v1's §4.4 treated the entropy gate's failure as a second witness
for "confidence does not track correctness". It is not a witness at all: the
quantity being thresholded was not a measurement of the model's confidence in
its answer.

That averaged confidence is diluted by high-confidence filler is established
rather than new. It is the motivating premise of relevance-weighted uncertainty
estimation (Duan et al., 2024), and the target of recent length-invariant
estimators. The related pathology in machine translation is that sentence-level
model probability produces both a beam problem and a brevity problem, which
Murray and Chiang (2018) trace to **label bias** and correct with a sentence
level term, finding a per-word reward slightly better than length
normalization. That is a different mechanism from ours and we cite it as a
precedent for correcting a length-coupled score, not as the same finding.
Measuring at the answer span instead is likewise established, in that line and
in windowed and claim-conditioned confidence. **We adopt the fix rather than
proposing it.**

Its role here is narrow: it closes off "you measured in the wrong place" as an
explanation for the next result.

#### Signal 3: the answer-token margin. Fails on saturation, with a mechanism.

Measured at the answer token, where dilution cannot apply, the signal is
saturated. §4.5 gives the registered test. The mechanism it supports:

**The answer token is a near-deterministic readout of a chain that has already
committed.** A sample whose answer contradicts the plurality of its own problem
still emits that answer at a median 20.52 nats, odds of roughly 800 million to
one against the nearest alternative option. Dissenting samples are as committed
as agreeing ones. The variance self-consistency exploits therefore does not
live at the answer token; it lives upstream, in which chain got written.

This is a mechanism rather than a restatement because it is falsifiable and was
registered in advance: had dissenting samples been measurably less certain than
agreeing ones, the thresholds in §4.5 would have failed.

#### Summary, and what this does to v1's thesis

| signal | token-level? | fails? | status of the explanation |
|---|---|---|---|
| plurality agreement | no | yes | **none. Open problem.** |
| mean token entropy | yes | yes | measurement artefact: the statistic was diluted |
| answer-token margin | yes | yes | mechanism: saturation, registered and tested |

**v1's "confidence does not track correctness" is retired as a unifying
thesis.** One of the three failures is not about confidence, one is about
confidence in a way v1 did not state, and one is unexplained. This section must
not be read as though every failure now has an account. Two of three do.

### 4.5 The commitment result, registered and held out

Registered at `argmax-prereg-margin-desc-v1.0` with thresholds fixed, then
tested once on the 69 problems no exploratory analysis had read.

| id | quantity, over samples dissenting from their problem's plurality | estimate | one-sided 95% lower bound | registered threshold | verdict |
|---|---|---|---|---|---|
| **MD1** | per-problem median margin | **20.5232** | 18.8376 | 15.0 | **PASS** |
| **MD2** | per-problem fraction above 10 nats | **0.7567** | 0.7105 | 0.60 | **PASS** |

64 of 69 problems carried at least three dissenting samples; 5 were excluded by
the registered rule and are counted, not imputed. Answer rate on the store,
reported beside these quantities as required: 0.9950 [0.9936, 0.9961]. The
holdout reproduces the exposed set closely, 20.52 against 20.62 and 0.757
against 0.749; only the holdout figures were registered.

#### The two units, measured

The margin is not devoid of information about correctness, and the difference
between the two units is not an argument we make about the result. It is the
result.

Fraction of samples above 10 nats, correct minus incorrect, cluster bootstrap
over problems at 10,000 resamples:

| unit | population | estimate | 95% interval | |
|---|---|---|---|---|
| **pooled, sample-level** | all 198 problems; 4,283 correct and 8,322 incorrect samples with measured margins | **+0.0604** | [+0.0183, +0.1017] | **excludes zero** |
| **per-problem, paired** | the 186 problems carrying at least one of each | **-0.0168** | [-0.0527, +0.0182] | **crosses zero** |

Pooled, correct samples sit above 10 nats 0.8228 of the time against 0.7624
for incorrect. Paired within a problem, the difference reverses sign and
cannot be distinguished from zero.

**On the population split.** 186 rather than 198 because a paired difference is
undefined where a problem has no correct or no incorrect sample: 2 problems are
all-correct and 10 all-incorrect. Those 12 contribute to the pooled row and not
the paired one. Neither row uses the 129-problem exposed set or the 121-problem
subset that appear elsewhere in this project for different statistics; both are
computed over the full store.

**We therefore do not claim that token log-probabilities are uninformative**,
and any reading of this paper reaching that conclusion has overshot. Across
questions the margin carries a real, small signal. Within a question it does
not carry one we can detect, and within a question is where a router stands.

This makes the reconciliation with recent work a measurement rather than an
argument. Kumaran (2026) reports that calibrated log-probability confidence
behaves as an answer-evidence signal coupled to correctness, at AUROC 0.62 to
0.80. That quantity, a temperature-scaled softmax over the option letters, is
ours at the same locus. Its unit is not: every result there is trial-level
across questions, with one answer drawn per question, and the design never
conditions on samples that disagree with each other, because it never has two
samples of one question to compare. **Our pooled row reproduces the direction
that paper reports. Our paired row is the one it never measured.**

**No margin gate was built.** We measured the signal and report that it cannot
support the routing decision. We did not construct a margin-thresholded gate
and evaluate its accuracy, which is why §4.3 remains a two-gate result.

## 5. The reasoning wall, on hosted serverless inference

v1's Limitations reported that a preliminary reasoning-native evaluation had
samples exhausting the output budget on hidden reasoning, and left the question
open. This section reports what happened when we tried to close it.

### 5.0 Scope, stated before the measurements

**The claim is about hosted serverless inference and does not hold for open
weights on owned or free compute.** Stated first because unscoped it has a
one-line rebuttal, and the rebuttal is correct.

All three models below are downloadable. Nothing here says a reasoning-native
model cannot be evaluated on GPQA Diamond. It says that on a metered per-token
hosted API at a small budget, three of them could not be.

**What the constraint actually is.** Serverless pricing charges per output
token, and reasoning-native models emit a great many. The cost of a fixed
experiment therefore scales with the model's verbosity rather than with the
size of the benchmark. The wall is a property of the billing model meeting the
generation length, not of the models being hard to run.

**The route a follow-up should take is open weights on fixed-cost compute**,
where the marginal cost of an output token is zero and the binding constraint
becomes wall-clock and memory. Kaggle's free tier offers two T4 GPUs at 32 GB
total with roughly 30 GPU-hours per week, enough for a 7 to 9B model in reduced
precision at long generations, though not for a 32B model without quantisation
or offload. Under that budget the caps that defeated us are affordable. What
changes is not the science but the denominator.

### 5.1 Position relative to prior work

That token budgets change evaluation outcomes is established. Guedes de Souza
and Panisson (2026) vary the generation budget across seven levels from 64 to
4,096 tokens, over four models and three benchmarks including GPQA Diamond at
the same 198 items, 56,476 inferences in total, and report that **model
rankings reverse across budgets on all benchmarks (p < 0.01, McNemar)**, with
3 to 19 percent of items non-monotone even after controlling for truncation
through a three-tier analysis over all items, per-model completed items, and
commonly completed items. That work is stronger than this on the general claim.

Two things about it define this section's scope. First, **it deliberately
excludes dedicated reasoning models**, naming o1, DeepSeek-R1 and QwQ, while
describing its own four as open-weight reasoning models: the exclusion is
specifically of hidden chain-of-thought architectures, which is exactly our
three. Second, **its budget grid stops at 4,096 tokens.** Qwen3.5-9B returns an
answer rate of 0.0000 at 2048 and at 4096, so across that entire grid the
measurement this paper reports does not exist at all. Ranking reversal is a
statement about which model wins; ours is that below a threshold nothing is
measured.

### 5.2 Three models, three measured walls

Each established by a real request, never inferred from a price list.

| model | wall | measurement |
|---|---|---|
| QwQ-32B | unreachable | `model_not_available`; no serverless route |
| MiniMax-M2.7 | never at a comparable cap | answer rate 0.6460 at cap 16,384; 0.2649 at the published 2048 |
| Qwen3.5-9B | nothing at any affordable cap | answer rate **0.0000** at 2048 and 4096, **mean completion equal to the cap exactly**; 0.5938 at 8192 |

Reference: Qwen2.5-7B-Instruct-Turbo at cap 2048 answers 0.9950 over 12,672
samples.

Every one of 52 samples at 2048 and 4096 ran to the ceiling, and at 4096 the
visible channel received 38 characters. The model card recommends 32,768 output
tokens for general queries, so v1's 2048 is a sixteenth of this model class's
own lower recommendation. This is not a model failing at a reasonable cap; it
is a cap fixed before this class of model was the default.

### 5.3 The door, and what it changes

Together honours a thinking control on Qwen3.5-9B. Two spellings are accepted
and indistinguishable in effect: mean completion 1537.3 against 1532.8 at cap
2048, identical truncation, no reasoning field returned either way.

**A reasoning model with reasoning disabled is a second non-reasoning model.**
What became purchasable was not the replication that was wanted, and we do not
describe it as one.

### 5.4 Comparability is keyed on answer rate, not on matched caps

Two models at the same cap with different length distributions produce two
different output populations wearing one benchmark's name. MiniMax-M2.7 at
2048 answers 0.2649; comparing its answered samples against Qwen's
near-complete ones compares two different sets of problems.

**Rule.** Two conditions are comparable when their answer rates match, and the
answer rate is published beside every accuracy.

### 5.5 The bill

| | samples | spend |
|---|---|---|
| probes: capability gate, caps, thinking control | 148 | $0.1346 |
| margin run on the v1 model, including its 4-sample smoke run | 12,672 | $3.4123 |
| second-model run, excluding its probes (§6) | 1,253 | $1.1207 |
| **realized, all phases** | **14,073** | **$4.6676** |

Rows are disjoint: the 148 probe samples are not counted again in the
second-model row. Ledger total to full precision is $4.667639.

**The bill, reconciled against the provider.**

| | |
|---|---|
| ledger, 14,125 sampled requests | **$4.697153** |
| provider billing export, this key, unrounded quantity x unit price | **$4.701169** |
| provider, sum of rounded per-line amounts | $4.69 |
| **difference** | **$0.004017, 0.085 percent**, ledger lower |

The residual is roughly 4,600 unrecorded tokens on one model and 11,000 on the
other. A client-side ledger writes a row when a response **arrives**, so it
cannot see a request that was issued, billed, and then abandoned. This project
has three such boundaries: a mid-run concurrency change, the SIGTERM that
stopped the v2 run at concurrency 16, and an interrupted probe. **That is a
property of the accounting method, not a discrepancy to explain away**: the gap
is one-sided by construction and scales with concurrency times interruptions.

**The reconciliation is only possible because the key was dedicated.** The same
billing account carries a second key with **$0.292479** of unrelated Aug 10 to
11 spend, including a model this project never used, and all twelve line items
across both keys sum to **$4.99**. A shared key would have made the Argmax bill
unseparable from that. A security rule turned out to be an accounting rule.

### 5.6 A gated benchmark cannot have its chains published

An infrastructure constraint we did not anticipate and found by running the
check rather than by reasoning about it.

Doc-level policy in this project is that benchmark question text is never
committed: the sample record stores `prompt_hash` and never the prompt. A
pre-release leakage check reduces the gated question source to hashed n-grams
and scans the release tree for them. Run over the margin-v1 store it reports
**5,669 hits across 198 files, 12,672 lines and 129,247 fingerprints, and
blocks the release**; run over the full raw release tree it reports **20,376**.

The cause is not a stored prompt. It is `raw_text`: **the model restates the
question inside its own chain of thought.** The request never carried the
question into storage; the response did.

The consequence generalises past this project. **A chain-of-thought sample
store on a gated benchmark cannot be published verbatim**, however careful the
storing pipeline is, because the leak is authored by the model rather than by
the pipeline. Redaction rules written for what a project writes do not cover
what the model writes back. This sits awkwardly beside reproducibility: the
raw store is what regenerates every derived number, and it is the artifact that
cannot be released.

Our resolution is a two-part release, a derived-only public artifact
(10.5281/zenodo.21933418, open, CC BY 4.0) and a gated raw one (10.5281/zenodo.21933422, restricted with
request-access), on the same access terms as the benchmark. We flag it because
every paper that publishes reasoning traces on a gated benchmark faces it, and
we have not seen it stated.

### 5.7 Projecting cost from a small probe

Mean completion length is a per-problem property at **119.66 times** the
variance a homogeneous null produces. A probe over k problems inherits that
between-problem spread, and taking more samples per problem does not reduce it.

| k problems | median error | 5th percentile | uplift for 95% coverage |
|---|---|---|---|
| 4 | -1.21% | -25.87% | 34.9% |
| 8 | -0.53% | -18.53% | **22.7%** |
| 16 | -0.35% | -13.20% | 15.2% |
| 32 | -0.17% | -9.10% | 10.0% |

Probes are near-unbiased in the median, yet just over half underestimate at
every k, because per-problem means are right-skewed. A ceiling set at the
projection is therefore wrong about half the time.

## 6. When the comparability rule rejected our own registered result

The second-model replication, registered as `argmax-prereg-margin-desc-v2.0`
and **not evaluated**.

MD3 and MD4 restated the §4.4 mechanism keyed on correctness rather than
plurality, with thresholds 15.0 nats and 0.60 set below the exposed estimates
of 21.5365 and 0.7617 so each was a prediction. The tag was cut before any
confirmatory sample existed.

**Cap selection failed, and not randomly.** A 32-sample probe at cap 6144
measured answer rate 1.0000 and truncation 0.0000. The run measured **0.8931**
[0.8747, 0.9090] and truncation **0.2905**.

Config drift was ruled out before the selection explanation was accepted: one
`param_hash` across all 1,253 samples matching the thinking-off configuration,
zero nonzero reasoning-token counts, cap 6144 throughout.

The cause is measurable because the sampler iterates problem-major and so
re-sampled the probe's own problems first:

| problems, iteration order | n | mean completion | truncation |
|---|---|---|---|
| the 8 probe problems | 128 | 2082.9 | 0.0312 |
| every other problem reached | 1,125 | 3546.4 | 0.3200 |

The probe reproduced itself and was **precise about an unrepresentative
slice**: the rest of the benchmark runs 1.703 times longer. The k = 8 uplift of
22.7 percent could not cover a 65.3 percent error, because that table describes
a **random** draw of 8 problems, and a fixed lowest-id slice is not one.

**Consequence.** At 29 percent truncation the pool that would be scored is
selected for finishing fastest, and those samples are missing non-randomly.
Scoring them would produce a number about the subset of samples fitting inside
6144 tokens and report it as a number about the model. **MD3 and MD4 are
therefore registered and unevaluated.** Not withdrawn, not falsified.

Nor was the replication recoverable at another cap. A right-censored fit to the
1,253 samples puts the cap required for the registered 0.9950 answer rate near
41,000 output tokens and the run at about $4.19, against $1.16 remaining; even
a 0.95 rate, which would still fail the condition, requires roughly **16,268**
tokens and **$3.84**. **The replication was not lost by choosing 6144; it was
not purchasable at any cap on this budget.**

**The point.** A methodological rule that never rejects anything is decoration.
This one rejected a result its own authors had registered, sampled and paid
for.

## 7. Thread A: a reconstructed few-sample estimator

Registered at `argmax-prereg-threadA-v1.0`, evaluated on v1's confirmatory 151.
Paired per-problem regret difference, estimator minus naive baseline; negative
favours the estimator.

| id | k | difference | 95% CI | verdict |
|---|---|---|---|---|
| **TA1** | 8 | **-0.0213** | [-0.0335, -0.0091] | **PASS** |
| TA2a | 4 | -0.0186 | [-0.0332, -0.0041] | PASS, registered as underpowered |
| TA2b | 16 | -0.0040 | [-0.0085, +0.0004] | **FAIL** |

TA1 passes by more than the resolution that produced it: the registered floor
is 0.0161 against an observed 0.0213. **TA2b fails by 0.0004** and is reported
as a failure rather than rounded into the pattern of the other two.

A shrinkage baseline was added **post hoc** and is labelled as such: at k = 4
and k = 16 every shrinkage strength is worse than the plain baseline, and at
k = 8 the weakest helps slightly. It is not registered and decides nothing.

## 8. Discussion

*(v1 text retained where its claims survive; the "why the gates fail"
paragraph is replaced.)*

**Why backfire occurs.** *(v1, unchanged.)* On hard problems the model's
sampling distribution concentrates on a wrong answer, so voting locks in the
error. Backfire is not a sampling artifact; it reflects the per-problem answer
distribution. GPQA distractors are designed to be plausible, which amplifies
the effect.

**Why the gates fail. (REPLACED.)** v1 said: "Both gates read confidence
(agreement, or low entropy), but confidence on these problems does not indicate
correctness." That sentence is withdrawn as stated. The entropy gate was not
reading confidence; it was reading a diluted average dominated by prose. The
margin, which does read confidence at the right place, fails because the answer
token is saturated whether or not the sample agrees with its own plurality. And
the agreement gate's failure is explained by neither account. Three signals,
three statuses, set out in §4.4.

**Positioning.** *(v1, retained.)* Prior work established that self-consistency
helps where models have higher baseline accuracy; we show it hurts the majority
of problems on a hard benchmark. Adaptive-consistency early stopping is
essentially our agreement gate, validated on easier datasets where backfire is
rare. Chen et al. (2024) attribute non-monotone majority-vote accuracy to a
mixture of easy and hard queries and estimate the optimal call count from few
samples; we measure the fraction of individual problems harmed rather than the
shape of the aggregate curve, which matters because aggregate accuracy here is
nearly flat while a majority of problems degrade underneath it. Tan et al.
(2025) study self-consistent errors and find consistency-based detectors fail
on exactly those cases, arguing for an external verifier; their setting is
error detection rather than compute allocation, but the conclusion converges
with ours.

**Added in v2.** The external-signal direction v1 pointed to is now better
motivated, and for a sharper reason than v1 could give. It is not merely that
the model's own confidence is miscalibrated. It is that at the answer token
there is almost no variance left to read: the sample has committed, and the
information that would distinguish a right chain from a wrong one was consumed
upstream. A signal read at the end of a chain is reading a decision, not a
deliberation. That argues for signals read *earlier* in the chain, not only for
signals external to it.

**Implications.** On hard inputs, do not assume self-consistency is safe, and
do not expect agreement, token entropy, or an answer-token margin to tell you
when it is. We tested all three and all three fail.

## 9. Limitations

*(v1 limitations retained; those v2 resolves are marked; new ones added.)*

**Retained from v1, unchanged.** Llama is near chance (0.273 single-sample,
just above the 0.25 baseline), so Qwen is the stronger demonstration and Llama
corroborates the direction. One benchmark, GPQA Diamond, graduate-level
science. The 47-problem exploratory subset was easier than the full benchmark
(Qwen N = 1 accuracy 0.418 against 0.342 pooled). Monte Carlo boundary
sensitivity: 14 of Qwen's 151 confirmatory problems have exactly zero gain, and
because backfire is defined strictly as `mv_gain < 0` the sensitivity is
one-sided and the rate can only rise. The oracle is an upper bound and the
fraction-captured ratio is noisy. The entropy threshold was selected in-sample,
so its capture is optimistic.

**Resolved in v2.** v1's "Limited gate family" limitation said final-answer
log-probability margins could behave differently and could not be evaluated
because per-token arrays were not stored. They are stored and evaluated in §4.4
and §4.5. The signal does not behave differently in the way that sentence
hoped.

**Partly resolved and rescoped.** v1's "Two small, non-reasoning models" left
reasoning-native evaluation as the central open question. §5 reports it is
unmeasurable on hosted serverless inference at a small budget and names the
open-weights route. The question remains open there.

**New in v2.**

- **The new claims rest on one model.** The registered second-model replication
  was sampled and could not be evaluated (§6). Cross-family replication was
  never purchasable: four of five priced candidates in the 7 to 9B range
  refused serverless requests.
- **Agreement's failure has no mechanism** (§4.4). This is the largest
  unresolved question in the paper, and v2 makes it more visible rather than
  smaller.
- **The reasoning wall is a serverless result**, not a statement about what is
  knowable.
- **The bill is unconfirmed by the provider** (§5.5).
- **No compute-matched baseline**, in v1 or v2. Every gate comparison is
  against a flat N = 64.
- **No margin gate was built**, so the margin's failure is inferred from the
  signal's distribution rather than measured as a routing outcome.
- An exploratory **U-shaped relation between per-problem completion length and
  accuracy** (0.4441, 0.3400, 0.2218, 0.3316, 0.4098 by length quintile) is
  suggestive and **not established**: the shape-agnostic quadratic term gives
  p = 0.083. Two mechanisms were ruled out, truncation selection and
  within-problem bimodality. It was found on an already-exposed set with its
  sharpest contrast chosen after inspection.

## 10. Corrections and disclosures

1. **A superseded predecessor draft was cited** in place of the published
   preprint. A falsification test now scans every document in the repository.
2. **Three per-problem properties were described as independent** before being
   tested. Within one model at n = 127, per-problem accuracy against the
   sub-2-nat margin tail gives -0.2614 [-0.3912, -0.1156], excluding zero.
3. **The margin run changed concurrency mid-run**; because the sampler iterates
   problem-major the resulting regime comparison is between problems rather
   than within them, and it decides nothing. Three manifests are marked
   `reconstructed`.
4. **An option-order claim was corrected after tagging.** Options are shuffled
   by `random.Random(row_index)`, reproducing v1's shuffle; `prompt_hash` is
   equal across both model stores for all 198 problems, verified.
5. **The answer-rate pairing rule did not cover prose tables** until a quintile
   table of accuracies was published without them.
6. **The v2 cap was chosen from 8 non-random problems** (§6). Probe problems are
   now drawn at random with a recorded seed.
7. **v1's own split has a leak:** 3 of its 50 exploratory ids sit inside the
   confirmatory 151. Disclosed here; v1's verdicts are not recomputed.
8. **v1's Setup describes uniform-random tie-breaking; its code breaks ties
   lexicographically.** Found while reproducing v1's figures from an archived
   derived view: `_plurality` sorts the tied answers and returns the first.
   The published numbers follow the code. Quantified rather than only stated:

   | | Qwen2.5-7B | Llama-3-8B-Lite |
   |---|---|---|
   | problems with a full-pool plurality tie | **5 of 198** | **2 of 198** |
   | N=64 subsets where the correct answer is in a tie | 47 | **0** |
   | MV acc(64), lexicographic | 0.3686 | 0.3131 |
   | MV acc(64), uniform random, 5,000 seeds | mean 0.3726, sd 0.0051 | identical, no variance |
   | percentile of the lexicographic result | **31.7** | not applicable |
   | backfire, lexicographic | 112/198 | 130/198 |
   | backfire, uniform random | mean 111.0, range 109 to 113 | identical, no variance |

   **Llama is entirely unaffected.** Neither of its two tied problems has the
   correct answer among the tied letters, and no N=64 subset anywhere in its
   pool puts the correct answer in a tie, so its 0.313 and 65.7 percent are
   convention-independent.

   **Lexicographic is not a biased choice on this dataset.** The correct
   answer is A on 48 problems, B on 51, C on 47 and D on 52 after the
   row-index shuffle, chi-square 0.343 on 3 degrees of freedom against 7.815
   at 5 percent. So the earliest letter carries no systematic advantage here,
   not merely none in expectation. The lexicographic result sits at the 32nd
   percentile of the random distribution: inside it, slightly unlucky, not an
   outlier.

   **It is a third-decimal effect and it changes no conclusion.** Across
   5,000 uniform-random seeds Qwen's backfire count spans 109 to 113 of 198,
   every value far above the 33 percent pre-registered threshold and every
   value a majority; MV acc(64) spans 0.3619 to 0.3833, and MV acc(1) is
   0.3419, so voting still lifts the aggregate slightly under every seed while
   harming most problems individually. The convention moves MV acc(64) by
   about 0.004 and the backfire count by about one problem. **No registered
   verdict, and no claim in either version of this paper, depends on which
   rule is used.** v1's verdicts are not recomputed.

## 11. Conclusion

On hard reasoning problems, self-consistency backfires on the majority of
problems, pre-registered and confirmed on the full GPQA Diamond benchmark for
Qwen and corroborated by a second family from a near-chance baseline. **That
result is unchanged from v1.**

What has changed is the explanation for why cheap verifier-free gates cannot
recover the headroom. v1 attributed it to confidence not tracking correctness.
With a third signal measured at the right place, that account no longer covers
the evidence. The entropy gate was reading a diluted statistic rather than a
confidence signal. The answer-token margin, read where dilution cannot apply,
fails because the answer token is saturated: a sample that contradicts its own
problem's plurality is as committed as one that agrees with it, so the variance
a router would need has already been spent upstream. And the agreement gate's
failure is explained by neither, and remains open.

Recovering the headroom likely requires a signal external to the model's own
samples, or one read earlier in the chain than the answer. Whether
reasoning-native models escape any of this remains open, and on hosted
serverless inference at a small budget it is not measurable at all.
