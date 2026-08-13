# max_tokens: a censored-data estimate, not a decision

Status: **estimate only. `max_tokens` remains `[BLOCKED: Step 0]`.** Nothing
here has been written into a config, and nothing here should be until a human
accepts or rejects it. The headline finding is that the estimate is weaker than
the method implies, and section 3 says where it stops being usable.

Scope: `MiniMaxAI/MiniMax-M2.7` on 47 GPQA Diamond problems through the phase
14b prompt. It is not a statement about any other model or prompt.

## Provenance

| What | Value |
|---|---|
| Source repo | `github.com/u7k4rs6/self-consistency-backfire` |
| Source path | `outputs/samples_qwq/*.jsonl`, 47 files |
| Read at commit | `a7f168e685b2eecf4793e2b635a6c801b6192d91` |
| Records | 404 |
| Censoring point | 16,384 output tokens, the probe's `max_tokens` |
| Date | 2026-08-13 |
| Access | read-only; nothing in that repo was modified |

Fitting code is not committed here. It is a one-off over another repository's
artifacts, and the numbers below are reproducible from the record fields
`output_tokens`, `input_tokens`, `full_response` and `extracted_answer` by the
procedure described in section 2.

---

## 1. The censoring set is not the no-answer set

Three sets, three different sizes. They overlap heavily and are not the same
set, and the difference is the interesting part.

| Set | Definition | Count |
|---|---|---|
| censored | `output_tokens >= 16384` | 142 |
| empty | `full_response` is empty or whitespace | 141 |
| unparseable | `extracted_answer == "UNPARSEABLE"` | 143 |

**Censored against empty:**

| | empty | not empty | total |
|---|---|---|---|
| **censored** | 139 | 3 | 142 |
| **not censored** | 2 | 260 | 262 |
| **total** | 141 | 263 | 404 |

**Censored against unparseable:**

| | unparseable | parseable | total |
|---|---|---|---|
| **censored** | 141 | 1 | 142 |
| **not censored** | 2 | 260 | 262 |
| **total** | 143 | 261 | 404 |

Four cells matter:

- **3 censored but non-empty.** They hit the cap and still emitted visible
  text; one of the three yielded a parseable answer. So hitting the cap does
  not guarantee an empty answer, and a truncation flag is not a proxy for a
  missing one.
- **2 empty but not censored, at 10 and 9,164 output tokens, both with zero
  characters of visible text.** These are a different failure from truncation.
  The 9,164-token case spent 9k tokens and stopped on its own without emitting
  anything visible: the model finished and produced nothing, which is a
  completion failure, not a budget failure. Raising `max_tokens` would not fix
  it. The 10-token case is an immediate empty return.
- **260 in neither cell**, the clean completions.

For the fit below, the censoring indicator is `output_tokens >= 16384` and
nothing else. Using "no answer" as the indicator would have censored two
records that were not truncated and left one truncated record uncensored.

---

## 2. The fit

Right-censored maximum likelihood on `output_tokens`, with the 142 records at
16,384 contributing `log S(16384)` rather than a density, and the other 262
contributing `log f(x)`. Two families, two parameters each.

No scipy in this environment, so the optimiser is a hand-written Nelder-Mead
over the censored log-likelihood. It was validated before use, because an
unvalidated optimiser is a way to get a confident wrong answer:

| Check | Result |
|---|---|
| Lognormal MLE on the uncensored subset against the closed form | mu 7.781807124342979 both ways, sigma 0.9180563109003499 both ways |
| Weibull recovery on 4,000 synthetic draws, k=1.3, lambda=9000, censored at 16,384 (11.3 percent censored) | k 1.3114, lambda 8,993.7 |

**Both parameter sets, as requested:**

| Family | Parameters | Log-likelihood | AIC |
|---|---|---|---|
| Lognormal | mu 8.8375, sigma 1.6948 | -2675.90 | **5355.81** |
| Weibull | k 0.7085, lambda 13,063.88 | -2705.91 | 5415.82 |

Lognormal wins by 60.0 AIC, which is decisive on the usual reading, so the
lognormal is used as the primary below. That comparison only says which of the
two is less bad. Neither is good, and the diagnostics say so:

| | empirical | lognormal | Weibull |
|---|---|---|---|
| P(X <= 1,000) | 0.0916 | 0.1274 | 0.1495 |
| P(X <= 2,000) | 0.2574 | 0.2328 | 0.2325 |
| P(X <= 4,000) | **0.4678** | **0.3742** | **0.3510** |
| P(X <= 8,000) | 0.5792 | 0.5352 | 0.5066 |
| P(X <= 12,000) | 0.6287 | 0.6284 | 0.6100 |
| P(X <= 16,000) | **0.6485** | **0.6905** | **0.6848** |
| censored fraction at 16,384 | **0.3515** | 0.3046 | 0.3091 |

Two misfits, both in the same direction. The fits put 9 to 12 points too little
mass below 4,000 tokens, and they under-predict the censored fraction by 4 to 5
points when that fraction is directly observed. A censored MLE that cannot
reproduce the censored fraction it was fitted to is misspecified.

The likely reason is visible in the histogram: the distribution is bimodal, a
mass of short completions that answer quickly and a mass that thinks until the
budget runs out, with a thin middle. No two-parameter unimodal family
represents that, so the fit compromises by inflating the body and thinning the
low end.

---

## 3. What the fit says, and where it stops being usable

### The numbers, with bootstrap intervals

1,000 nonparametric bootstrap resamples of the 404 records, censoring indicator
carried with each record, refit end to end, seed 20260813.

**Lognormal, the AIC-preferred fit:**

| Quantity | Estimate | 95 percent bootstrap interval |
|---|---|---|
| median | 6,888 | 5,811 to 8,459 |
| p95 | 111,876 | 77,303 to 168,443 |
| p99 | 355,085 | 219,536 to 596,288 |
| mean | 28,959 | 20,111 to 44,677 |

**Weibull, for comparison:**

| Quantity | Estimate | 95 percent bootstrap interval |
|---|---|---|
| median | 7,788 | 6,619 to 9,365 |
| p95 | 61,460 | 48,842 to 79,150 |
| p99 | 112,761 | 86,552 to 149,958 |
| mean | 16,349 | 13,328 to 20,579 |

**The `max_tokens` at which predicted truncation falls below 1 percent is the
p99 and is the same number.** Truncation at a cap `c` is `P(X > c)`, so a
1 percent truncation target is by definition the 99th percentile. They are not
two pieces of evidence, and reporting them as two would double-count one
extrapolation.

### The extrapolation warning, stated plainly

**p95, p99 and the 1-percent cap are extrapolations past the censoring point
and carry far more uncertainty than the intervals above suggest.**

- The data end at 16,384. The lognormal p95 is 6.8 times that, and its p99 is
  21.7 times it. Nothing in the sample constrains the shape out there.
- The two families disagree by a factor of **1.8 at p95** and **3.1 at p99**,
  and their bootstrap intervals do not overlap at either. The bootstrap
  measures sampling variability at a fixed family; it does not measure the
  choice of family, which is the larger error here.
- The family that wins on AIC is the one that fits the body, and the body is
  exactly the part of the data that says nothing about the tail.

### What is identified without a model

With 35.1 percent censored from the top, every quantile up to **p = 0.6485** is
identified nonparametrically, and nothing above it is.

| Quantity | Distribution-free value |
|---|---|
| median | **4,655** |
| p55 | 6,069 |
| p60 | 9,257 |
| p64 | 13,972 |
| p95 | not identified; **> 16,384** is all that can be said |
| p99 | not identified; **> 16,384** |
| mean | not identified; **>= 8,005**, since E[X] >= E[min(X, 16384)] |

The nonparametric median is 4,655. Both fits put the median at 6,888 and 7,788,
which are 48 and 67 percent higher than a quantity the data determine outright.
That is the cleanest statement of how much to trust the fitted tail: the fits
are wrong about a number that does not need fitting.

### The predicted truncation rate at budgets near the data

This is the part of the fit worth using, because it interpolates or extrapolates
by a factor of 2 to 4 rather than 20.

| Budget | Lognormal truncation | Weibull truncation |
|---|---|---|
| 16,384 (measured: **0.3515**) | 0.3046 | 0.3091 |
| 24,576 | 0.2265 | 0.2091 |
| 32,768 | 0.1787 | 0.1468 |
| 49,152 | 0.1231 | 0.0775 |
| 65,536 | 0.0919 | 0.0435 |
| 131,072 | 0.0411 | 0.0060 |

Both fits under-predict at the one budget where truth is known, by 4 to 5
points, so read these as optimistic.

**The practical reading: there is no affordable budget at which this model stops
truncating on this benchmark.** Doubling the budget to 32,768 still leaves 15 to
18 percent truncated, and the 1-percent target sits somewhere between 113k and
355k tokens, which no serverless endpoint will serve and the cost model cannot
carry. The design question is therefore not "which `max_tokens` avoids
truncation" but "which truncation rate is acceptable, and is it counted". The
schema already answers the second half: `truncated`, `hit_ceiling` and
`outcome_class` exist so that a truncated sample is a measurement rather than a
silent loss.

---

## 4. Cost sanity check

**The pricing constants reproduce the recorded spend exactly.** Using the stored
token totals, 141,744 input and 3,234,042 output, at $0.30/M input and $1.20/M
output:

    141,744 x 0.30/1e6  +  3,234,042 x 1.20/1e6  =  $3.9233736

against the $3.9233736 stored in `qwq_probe_results.json`, a difference of
exactly zero, and $0.00971132 per sample against the $0.00971 reported. The
pricing constants are confirmed, so any gap below is the fit's.

**The fit reconstructs the observed cost to within 5 to 8 percent.** The
comparison has to be against the *censored* mean, not the fitted mean, because
the provider billed `min(X, 16384)` and never billed the tail it refused to
generate:

| Quantity | Lognormal | Weibull | Observed |
|---|---|---|---|
| E[min(X, 16384)] | 8,416 | 8,664 | **8,005** |
| cost per sample at that mean | $0.01020 | $0.01050 | **$0.00971** |
| E[X], uncapped | 28,959 | 16,349 | not observable |
| cost per sample uncapped | $0.03486 | $0.01972 | not observable |

The 5 to 8 percent overstatement of the capped mean is the same misfit section 2
found, seen through the cost model: the fits put too much mass in the middle of
the body. It is small enough to confirm the fit is not wildly broken and large
enough to confirm it is not exact.

The uncapped row is the one to be careful with. **The two families disagree by a
factor of 1.8 on what an uncapped run would cost**, $0.0349 against $0.0197 per
sample, and that disagreement is entirely tail extrapolation. Any budget plan
that quotes a per-sample cost above 16,384 tokens is quoting a number the data
do not contain.

---

## 5. What a paid probe would still have to confirm

The audit answered what the stored data can answer. Three things it cannot,
in the order they block a decision:

1. **The truncation rate at the budget actually chosen.** Everything above
   16,384 is extrapolation from a misspecified fit that already under-predicts
   at the one budget it can be checked against. This is the only number that
   must be measured rather than modelled.
2. **Whether the tail is lognormal-heavy or Weibull-light.** It decides the
   uncapped cost per sample within a factor of 1.8 and the 1-percent budget
   within a factor of 3.
3. **Whether `finish_reason` and a runner-up logprob depth arrive at all**, per
   `notes/phase14b_token_audit.md`. Unrelated to the tail, but the probe is
   being bought either way and doc 4 s2 wants the capability probe to do both
   jobs.

### The smallest run that would confirm item 1

**139 completions at the candidate budget**, one sample per request, on the same
problems and prompt. That is the sample size for a binomial proportion at
plus or minus 5 percentage points, 95 percent confidence, near a 10 percent
truncation rate; at a 35 percent rate the same precision needs 350, and plus or
minus 10 points needs 88.

Estimated cost at the same prices, using E[min(X, c)] from both fits, which
agree closely at this range:

| Candidate budget | Expected billed output per sample | 139 completions |
|---|---|---|
| 16,384 | 8,416 to 8,664 | $1.42 to $1.46 |
| 32,768 | about 12,200 | **about $2.05** |

That probe needs no tail model: it measures the truncation rate at the budget
directly, which is the quantity that decides the design.

### The run that is not worth buying

**Distinguishing the two fitted tails requires about 2,100 completions**, which
is the sample size to separate 0.1787 from 0.1468 at 32,768 with 80 percent
power. At roughly $0.025 per sample at that budget that is about $50, more than
the whole phase 14b probe cost, to answer a question that only matters if
somebody wants an uncapped cost figure. Item 2 should be treated as permanently
unresolved unless something else forces it, and the cost model should carry the
factor-of-1.8 range instead of a point estimate.

---

## 6. The two-component mixture

Section 2 found the unimodal fits misspecified and named the reason: the
distribution is bimodal, a mass of completions that answer quickly and a mass
that thinks until the budget runs out. The response is not a better unimodal
family. It is a mixture with a component for each mode.

Five parameters: a mixing weight and a lognormal for each component, fitted by
right-censored maximum likelihood with the same Nelder-Mead, from four starting
points to reduce the chance of a local optimum.

### 6.1 Validation, on the same terms as before

Synthetic censored mixture data, known parameters, 4,000 draws, 22.6 percent
censored at 16,384:

| Parameter | True | Recovered |
|---|---|---|
| weight, fast | 0.600 | 0.591 |
| mu, fast | 7.200 | 7.173 |
| sigma, fast | 0.600 | 0.606 |
| mu, slow | 9.800 | 9.806 |
| sigma, slow | 0.800 | 0.776 |

The estimator recovers a mixture it is given. What it does with the real data
is therefore about the data, not about the optimiser.

### 6.2 The fit, and how it compares

| Model | Parameters | Log-likelihood | AIC |
|---|---|---|---|
| Lognormal | 2 | -2675.90 | 5355.81 |
| Weibull | 2 | -2705.91 | 5415.82 |
| **Two-component lognormal mixture** | **5** | **-2633.94** | **5277.87** |

The mixture wins by 78 AIC over the better unimodal fit, having paid for three
extra parameters.

### 6.3 IDENTIFIED: the fast component and the mixing weight

The fast mode lies essentially entirely below the censoring point, so it is
observed rather than extrapolated, and the weight is pinned by the censored
fraction.

| Quantity | Estimate | 95 percent bootstrap interval, 400 reps |
|---|---|---|
| weight on the fast mode | 0.538 | 0.363 to 0.680 |
| mu, fast | 7.726 | 7.562 to 7.931 |
| sigma, fast | 0.771 | 0.479 to 0.954 |
| fast-mode median | **2,266 tokens** | 1,923 to 2,781 |
| fast-mode p99 | 13,617 tokens | 6,314 to 24,385 |
| P(fast sample exceeds 16,384) | **0.0051** | |

Two honest qualifications on the word identified:

- The fast mode's **p99 is inside the cap at the point estimate and its
  bootstrap upper bound is not**, 24,385 against a cap of 16,384. So "the fast
  mode lies entirely below the cap" is true of the fitted distribution and not
  quite true of every resampled world. The identified claim is the median and
  the body, not the last percentile.
- The weight's interval is wide, 0.363 to 0.680. What is tight is the censored
  fraction the mixture implies, because that is what the data measure directly.
  The split between "slow but under the cap" and "fast with a long tail" is
  where the width comes from.

### 6.4 NOT IDENTIFIED: the slow component's upper tail

**No p99 is reported for the slow component, and none should be.** Every
observation of the slow mode above 16,384 is a record saying "at least 16,384",
so the data contain no information about the shape out there. The fitted
`sigma_slow` of 2.769 and the implied slow-mode median of 112,636 tokens are
what the likelihood settles on, not what the data show.

The profile makes the emptiness visible. Fixing `sigma_slow` and refitting
everything else:

| sigma, slow | log-likelihood loss | implied censored fraction | slow-mode p99 |
|---|---|---|---|
| 0.3 | -10.11 | 0.3515 | 311,783 |
| 0.5 | -10.09 | 0.3514 | 178,590 |
| 0.7 | -10.06 | 0.3515 | 398,153 |
| 0.9 | -10.06 | 0.3515 | 955,677 |
| 1.2 | -10.08 | 0.3515 | 3,916,139 |
| 1.6 | -7.10 | 0.3416 | 1,702,172 |
| 2.0 | -2.04 | 0.3438 | 3,939,834 |

Every row reproduces the censored fraction to three decimals. The implied slow
p99 spans a factor of **twelve**, from 312 thousand to 3.9 million tokens,
across rows the data barely distinguish. The likelihood is also non-monotone in
`sigma_slow`, which says the constrained surface is itself poorly determined
rather than merely flat.

The data determine **what fraction of samples are slow**. They say essentially
nothing about **how slow**, and no budget decision may rest on the second.

### 6.5 The two checks the unimodal fits failed

Section 2 rejected the unimodal fits on two grounds. The mixture is held to the
same two:

| Check | Truth | Lognormal | Weibull | **Mixture** |
|---|---|---|---|---|
| censored fraction at 16,384 | 0.3515 | 0.3046 | 0.3091 | **0.3523** |
| nonparametric median | 4,655 | 6,888 | 7,788 | **4,621** |

Both pass, and not by a little: the median is within 0.7 percent of a quantity
the data determine outright, where the unimodal fits were 48 and 67 percent
high. The body agrees too, at every point where section 2 found the unimodal
fits off:

| | empirical | mixture |
|---|---|---|
| P(X <= 1,000) | 0.0916 | 0.0979 |
| P(X <= 2,000) | 0.2574 | 0.2680 |
| P(X <= 4,000) | 0.4678 | 0.4667 |
| P(X <= 8,000) | 0.5792 | 0.5892 |
| P(X <= 12,000) | 0.6287 | 0.6266 |
| P(X <= 16,000) | 0.6485 | 0.6462 |

The mixture is the right shape. It still cannot tell you where to put
`max_tokens`, because the budget question lives in the tail it does not
identify.

---

## 7. Is the mode a property of the problem, or of the sample?

This is the part that may outlive the budget question. If a completion's mode
is decided by the problem, the mode is a feature of the problem and a candidate
predictor. If it is decided per sample, it is noise.

Mode membership is assigned by posterior responsibility under the fitted
mixture. It is close to a hard split: only 53 of 404 samples fall between 0.2
and 0.8, and the most fast-leaning censored sample has responsibility 0.0078,
so every censored sample is slow, as the model requires. 245 samples are fast
and 159 are slow.

### 7.1 The distribution across problems

47 problems, 8 to 11 samples each. Fraction of a problem's samples in the fast
mode:

| Fast fraction | Problems |
|---|---|
| exactly 0.00 | **8** |
| 0.01 to 0.24 | 5 |
| 0.25 to 0.49 | 2 |
| 0.50 to 0.74 | 4 |
| 0.75 to 0.99 | 12 |
| exactly 1.00 | **16** |

Mean 0.643, standard deviation 0.399. **24 of 47 problems are at one extreme or
the other**: 8 problems where no sample ever answered fast, 16 where every
sample did.

### 7.2 The permutation test

Under a per-sample null, mode labels are exchangeable across problems at fixed
per-problem sample counts. 10,000 permutations:

| Statistic | Observed | Null mean | Null 95th percentile | p |
|---|---|---|---|---|
| variance of per-problem fraction | **0.1590** | 0.0281 | 0.0378 | **< 0.0001** |
| problems at 0.00 or 1.00 | **24** | 0.67 | 2 | **< 0.0001** |

The observed variance is **5.65 times** the per-sample null. The null produces
24 extreme problems in none of 10,000 draws; its 95th percentile is 2.

**Mode membership is a property of the problem.** Not marginally, and not in a
way that needs a delicate test.

### 7.3 What it predicts, and what it does not

The obvious next step is to ask whether the fast fraction predicts accuracy. It
appears to, spectacularly, and the appearance is an artifact:

| Statistic | All samples | Answered samples only |
|---|---|---|
| accuracy, fast-mode samples | 0.9061 (n=245) | 0.9098 (n=244) |
| accuracy, slow-mode samples | **0.0881** (n=159) | **0.8235** (n=17) |
| r, per-problem fast fraction against accuracy | **0.856** | **0.099** |

The left column is the predecessor's coercion, not a finding. 142 of the 159
slow samples have no answer at all, and every unanswered sample in that store
is recorded as `correct = false`. So "slow samples are wrong" decodes to "slow
samples were truncated, produced nothing, and were scored wrong", which doc 4
section 3.6 forbids for exactly this reason.

Among samples that actually produced an answer, the gap collapses: 0.9098
against 0.8235, Wilson intervals 0.867 to 0.940 and 0.590 to 0.938, heavily
overlapping on 17 slow observations. The per-problem correlation falls from
0.856 to 0.099.

**What the mode predicts is whether a sample answers at all, not whether the
answer is right.** At this cap the per-problem fast fraction is very nearly the
per-problem answer rate, which is the quantity doc 4 section 4.1 now requires be
published beside every accuracy. This analysis is where that requirement earns
its place: a per-problem property decides who votes, 8 problems of 47 have no
voters at all, and their accuracy is undefined rather than zero.

Whether the mode predicts where an accuracy-versus-N curve peaks is not settled
here and cannot be, because 8 problems contribute no answered samples and the
rest contribute a truncated view. It is a hypothesis worth registering before
Argmax's own data exist, not a result: **problems whose samples answer fast are
a different population from problems whose samples think to the cap, and
pooling them is pooling two experiments.**

---

## What a human is being asked to accept

Not a value for `max_tokens`. Five statements:

1. The identified facts: median demand 4,655 tokens, at least 35.1 percent
   truncation at 16,384, mean demand at least 8,005 tokens.
2. That the fitted tail is not usable for choosing a truncation-free budget.
   The unimodal fits miss the median by 48 to 67 percent and disagree by 3x at
   p99. The mixture fixes the body and does not fix the tail: the slow
   component's p99 moves by a factor of twelve across refits the data barely
   distinguish, which is why no p99 is reported for it.
3. That the design should therefore pick a budget, measure its truncation rate
   with about 139 completions, and count truncation as a first-class outcome
   rather than trying to eliminate it.
4. That the population is two populations. A fast mode with median 2,266 tokens
   carrying 54 percent of the weight, and a slow mode whose tail this data
   cannot see.
5. That which mode a sample lands in is **a property of the problem**, at 5.65
   times the per-sample null and p below 0.0001, and that what it predicts is
   the answer rate rather than the accuracy. Eight of 47 problems produced no
   answer at all at this cap.

`max_tokens` stays `[BLOCKED: Step 0]` until someone decides which truncation
rate is acceptable. That is a judgement about the experiment, not a
quantity this data can supply.
