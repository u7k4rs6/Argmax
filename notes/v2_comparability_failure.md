# margin-v2 does not meet its registered comparability condition

**MD3 and MD4 remain registered under `argmax-prereg-margin-desc-v2.0` and are
NOT evaluated.** They are not withdrawn, not falsified, and not tested. The
store that exists cannot decide them, and this note records why so that the
tag reads as unevaluated rather than as forgotten.

## What was registered

Cap 6144 was chosen under doc 2 section 7.1, which keys comparability on
answer rate rather than on matched caps. The registered reference is
`md_v2_answer_rate_reference = 0.9950`, the v1 answer rate over 12,672
samples. A 32-sample probe at cap 6144 measured answer rate **1.0000** with
truncation **0.0000**, and that measurement is what licensed the cap.

## What the run actually produced

1,253 of 3,168 samples, 79 of 198 problems, before the sampler was terminated:

| | probe, n=32 | run, n=1253 |
|---|---|---|
| answer rate | 1.0000 | **0.8931** [0.8747, 0.9090] |
| truncation | 0.0000 | **0.2905** |
| mean completion | 2055.1 | **3396.9**, +65.3 percent |

**0.8931 against a registered 0.9950 is not a near miss.** Roughly one sample
in nine returns no extractable answer, and 29 percent hit the ceiling.

## Config drift ruled out before the selection story was accepted

The obvious alternative was that the thinking control lapsed. It did not:

| check | result |
|---|---|
| distinct `param_hash` across all 1,253 samples | **1**, and it is `89bdcf2e54986835b4448654...`, the thinking-off config computed before launch |
| `usage.reasoning_tokens` nonzero | **0 samples**, across both run ids |
| `max_tokens` | 6144 on every sample |
| reasoning or reasoning_content field returned | 0 samples |

(`split_ok` reads true on all 1,253, which looks alarming and is not: the
sampler sets it alongside `split_method: none`, meaning no split was
attempted rather than that one succeeded.)

The request was byte-identical throughout. **The instrument was not
misconfigured. The probe measured what it measured, correctly, on the wrong
problems.**

## The cause, measured directly

The sampler iterates problem-major, so the run re-sampled the probe's own 8
problems first, at M=16, under the confirmatory config. That gives a direct
comparison the probe could not give itself:

| problems, in iteration order | n | mean completion | truncation |
|---|---|---|---|
| **0 to 7, the probe set** | 128 | **2082.9** | **0.0312** |
| 8 to 15 | 128 | 2938.5 | 0.2422 |
| 16 to 39 | 384 | 3922.1 | 0.3750 |
| 40 to 78 | 613 | 3438.0 | 0.3018 |
| **probe set** | 128 | **2082.9** | 0.0312 |
| **everything else** | 1125 | **3546.4** | 0.3200 |

The probe set reproduces the probe almost exactly, 2082.9 against 2055.1 and
truncation near zero. **Every other band is longer, and the rest of the
benchmark runs 1.703 times the probe set's mean completion.**

So the probe was not noisy and was not unlucky. It was **precise about an
unrepresentative slice.** The 8 lowest-id GPQA Diamond problems are
substantially shorter than the benchmark, and nothing in a within-probe
statistic could have revealed that.

### Why the calibration did not catch it

Doc 2 section 5.3.1 puts the 95 percent uplift at k=8 at 22.7 percent, from
resampling the 198 v1 per-problem means, with a fifth percentile of -18.53
percent. The observed error is **-65.3 percent on mean completion**, far
outside that interval.

That is not a failure of the calibration. It is the calibration being applied
to the wrong thing. **The uplift table describes a random draw of k problems.
A fixed lowest-id slice is not a random draw, and its error is not
resampleable even in principle**, because there is only one such slice and it
is the same one every time. The same section already records the fix, that
probe problems are drawn at random with a recorded seed. This run is the
evidence for it, arriving one run too late.

## Why MD3 and MD4 are not evaluated on this store

Not because 1,253 of 3,168 samples is too few. Because of **what** is missing.

At 29 percent truncation the pool that would be scored is **selected for
finishing fastest**. Samples that would have taken longer are absent, and
they are absent non-randomly: they are the ones on the harder or more
discursive problems, which are precisely the ones a claim about margins among
incorrect samples is about. Scoring the survivors would produce a number about
the subset of samples that fit inside 6144 tokens and would report it as a
number about the model.

That is the exact confound doc 2 section 7.1 and doc 4 section 4.1 exist to
prevent. Section 7.1 says comparability is keyed on answer rate because
matching caps across models with different length distributions compares two
different output populations wearing one name. Section 4.1 requires the answer
rate beside every accuracy for the same reason. **Evaluating MD3 and MD4 here
would violate both rules in the same paper that argues for them.**

There is no rescue available at this store either. Scoring unanswered samples
as incorrect does not help, because the claims are defined over incorrect
samples and an unanswered sample has no margin to contribute. Restricting to
problems with low truncation reintroduces the selection at the problem level.

## The money, which removes the choice anyway

| | |
|---|---|
| realized to date, all phases | **$4.6676** |
| v2 cost per sample, measured | $0.000894 |
| remaining 1,915 samples at that rate | **$1.71** |
| implied balance, from the $2.55 stated remaining at v1 completion | **$1.29** |
| implied balance, on the most generous reconstruction | $1.43 |

**Short by $0.28 to $0.42.**

The $1.71 estimate is itself uncertain, and not in a direction that can be
signed. **The 119 unsampled problems are unknown.** The sampled bands do not
trend: 16 to 39 averages 3922.1 and 40 to 78 averages 3438.0, so position
does not predict length beyond the probe set being short. What the bands show
is that the **between-band spread is wide**, from 2082.9 to 3922.1, so an
average over the 79 problems reached is a weak predictor of the 119 not
reached. The $0.000894 rate is also held down by the cheap probe-set problems
at the front.

**The shortfall holds regardless.** Covering it would need the remaining
problems to be cheaper than everything measured after the probe set, and the
gap is 16 to 25 percent of the remaining cost under either balance
reconstruction. The conclusion does not depend on the estimate being precise.

### The balances are reconstructed, and that is a defect in a claimed contribution

An itemised bill is one of this project's stated contributions, cited against
the predecessor's unverifiable $3.9234. **It currently rests on the same kind
of number.**

What is verified, and it is not nothing:

| check | result |
|---|---|
| ledger rows against raw sample records | **14,073 = 14,073**, difference 0 |
| every row's `cost_usd` recomputed from `usage_raw` and its named pricing snapshot | **$4.667639 = $4.667639**, 0 rows disagreeing |
| per-model totals | Qwen2.5-7B: 12,672 samples, 3,742,976 in, 7,631,158 out, $3.4122. Qwen3.5-9B: 1,401 samples, 368,961 in, 4,770,703 out, $1.2554 |

So the ledger is internally consistent, complete against the raw store, and
reproducible from stored token counts. **What it is not is confirmed by the
provider.** Every figure is `tokens x snapshot price`, and it inherits any
error in the snapshot, any rounding Together applies, and any minimum-charge
or rounding rule not in the snapshot.

**No programmatic route exists.** Checked rather than assumed: `/v1/models`
authenticates and returns 200 on this key, and every plausible billing path
under both `api.together.xyz` and `api.together.ai` returns the dashboard's
404 page. The credits documentation describes only the web billing settings
and documents no endpoint. The dashboard itself redirects to sign-in, and this
agent has no session and will not be given credentials.

**Owed, and the only thing that closes it:** a human reads three numbers off
the Together billing dashboard, total spend to date, current balance, and the
date, and they are recorded here beside the ledger figure with the
discrepancy stated. Until then the bill is a computed estimate that
reconciles against itself, and the draft must describe it that way rather
than as a verified invoice. **A reconstruction presented as an audit is the
predecessor's failure repeated with better bookkeeping.**

## Restricting to the problems that do answer is not available

The obvious rescue is to keep the v2 problems whose own answer rates reach
0.995 and evaluate MD3 and MD4 on those. **It must not be attempted.** It is
not the "shown insensitive" branch of doc 2 section 7.1, and it does not
rescue the comparison.

Section 7.1 permits proceeding when a result is **shown insensitive** to the
comparability threat. That means the threat varies and the answer does not.
This restriction does not vary the threat, it removes the affected units, and
those units are not a random subset. **Which samples answer is a property of
the problem**, exactly as completion length is: the between-band spread above
runs from 0.0312 truncation on the probe set to 0.3750 on problems 16 to 39.
Keeping the problems that answer therefore **changes which problems are
compared** rather than changing how they are compared. The result would be a
statement about the subpopulation of GPQA Diamond problems that fit inside
6144 tokens on this model, presented as a statement about the model, and the
subpopulation is different for v1, which does not have the constraint at all.

**This is the same argument this project already made against restricting
MiniMax-M2.7 to its answered subpopulation** (`notes/predecessor_cap.md`,
`notes/reasoning_wall.md`). At 0.6460 answer rate at 16,384 and 0.2649 at
2048, comparing MiniMax's answered samples against Qwen's near-complete ones
compares two different sets of problems wearing one benchmark's name. The v2
case is the same argument at a milder rate, and a rule that applies at 0.2649
and not at 0.8931 is a rule chosen after seeing which way it cuts.

The per-problem restriction is worse than the pooled version in one respect.
It is invisible in the output: a table of 40-odd problems with answer rates of
0.995 and above looks like a clean comparison, and the reader cannot see the
problems that were dropped or that dropping them was the analysis.

## What this costs, stated plainly

**The rule cost its authors a registered replication.**

The second-model replication of the margin claims is not happening on this
budget. MD3 and MD4 were registered before sampling, thresholds were held
after a stratification check, the tag was cut with no confirmatory sample in
existence, and the discipline was followed exactly. It was followed right up
to the point where it said the data could not be used, and then it was
followed there too.

The alternative was available and it was cheap: score the 79 problems, report
MD3 and MD4 with a footnote about truncation, and let a reader who does not
check the answer rate take the numbers at face value. Doc 4 section 9.1 exists
because that footnote is exactly what gets dropped.

## What survives

| | |
|---|---|
| MD1 and MD2, v1 | **unaffected**. Registered, held-out, passed, one model |
| the commitment result | stands on v1 alone, one model, and the draft says so |
| MD3 and MD4 | **registered and unevaluated**, cause recorded here |
| the 1,253 samples | kept. Raw is append-only, and they are the evidence for everything above |
| the reasoning wall | strengthened. This is a fourth measured wall, and the most expensive |
| the 69-problem holdout | untouched on both models |

The v2 store is not waste. It is the measurement that shows a cap chosen from
8 non-random problems fails on 198, which is a result about probe design that
no successful run would have produced. It belongs in the reasoning-wall
section, not in a replication section.

## A random-draw cap probe: costed, guarded, not run

Authorised conditionally at roughly $0.20, **only if the dashboard confirms
enough balance**. The dashboard could not be reached and no human has read it,
so **the precondition is unmet and nothing was sampled.** Spending on the
strength of the same reconstruction this note has just called insufficient
would contradict the section above.

### The guard, written before any such probe runs

**A usable cap is not permission to evaluate MD3 or MD4.** Whatever a future
probe returns, those claims stay registered and unevaluated. The reason is not
that 6144 was the wrong cap. It is that **the store at a usable cap does not
exist**, and no cap-probe result creates one. A reader arriving later at a
line reading "cap 12288 reaches answer rate 0.97" must not take it as licence
to score the 1,253 samples that were drawn at 6144 under 29 percent
truncation. Those samples remain selected for finishing fastest, and a
different cap's answer rate says nothing about them.

If a full run at a usable cap is ever purchased, it is a new phase against a
new registration, and it cites this note.

### What it would cost, which is not $0.20

Projected from a right-censored lognormal fit to the 1,253 v2 samples,
mu = 8.0521, sigma = 1.0000, median 3140 tokens:

| cap | P(complete) | E[completion tokens] | $/sample | 128 samples |
|---|---|---|---|---|
| 8192 | 0.8312 | 3887 | 0.001022 | **$0.1308** |
| 12288 | 0.9138 | 4385 | 0.001146 | **$0.1467** |

16 problems x 8 samples x 2 caps = 256 samples, **$0.2775**, and **$0.3197**
once the k=16 uplift of 15.2 percent from doc 2 section 5.3.1 is applied, as
that section now requires. That is 60 percent over the stated $0.20. The
ceiling for such a run is $0.32 above realized, not $0.20.

### The result it would have bought, for free

The fit answers the question the probe was for without spending anything, and
the answer is unfavourable:

| target completion rate | cap required | $/sample | full 198 x 16 run |
|---|---|---|---|
| 0.900 | 11,312 | 0.001124 | **$3.56** |
| 0.950 | 16,268 | 0.001212 | **$3.84** |
| 0.990 | 32,159 | 0.001306 | **$4.14** |
| **0.995, the registered reference** | **41,272** | 0.001322 | **$4.19** |

**No affordable cap reaches the registered comparability condition.** Meeting
0.9950 needs roughly 41,000 output tokens per sample and a $4.19 run, against
a reconstructed balance of $1.29 to $1.43. Even 0.95, which would still fail
the condition, needs 16,268 tokens and $3.84.

So the replication was not lost by choosing 6144. **It was not purchasable at
any cap on this budget**, and the 6144 choice determined only how the failure
presented. That is the number section 4.3 needed, and it is a stronger version
of the section's point than a probe result would have been.

**Caveats, because this is an extrapolation.** The fit is to a store censored
at 6144 with 29 percent of samples censored, so predictions at 41,000 tokens
extrapolate far beyond the data. The fitted sigma landing on exactly 1.0000
suggests the optimiser found a flat region, and the fit predicts 0.7489
completion at 6144 against 0.7095 observed, so it is mildly optimistic about
completion. Both push the required caps **up**, not down. The qualitative
conclusion does not rest on the fit's precision: even at 16,384, a cap chosen
without any fitting, the run costs $3.84 and the balance is under $1.50.

## Do not

- Do not evaluate MD3 or MD4 on this store.
- Do not re-register the same claims at a larger cap as if v2.0 had not
  happened. If a future budget allows it, that is v3.0 and it cites this note
  for why v2.0 was not evaluated.
- **Do not restrict to the problems whose answer rates reach 0.995.** See the
  section above. It changes which problems are compared, it is the argument
  already rejected for MiniMax, and it hides the analysis in the output.
- **Do not read a cap-probe result as permission to evaluate MD3 or MD4.** A
  usable cap does not create a store at that cap. The 1,253 samples remain
  drawn at 6144 under 29 percent truncation whatever a probe says.
- Do not move or delete `argmax-prereg-margin-desc-v2.0`. It is a correct
  record of a claim that was properly registered and could not be tested.
