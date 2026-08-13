# Candidate for a future registration: per-problem completion length

**This is a candidate, not a finding.** Nothing here is registered, no tag is
cut, and no hypothesis below has been tested on a set that was not already
read. The measurement in section 1 is real and was made for another purpose;
everything after it is a design sketch.

## 1. What is measured, and why it stands out

On the v1 store, 198 GPQA Diamond problems at 64 samples each on
Qwen2.5-7B-Instruct-Turbo, the between-problem variance of **mean completion
length** is **119.66 times** what a homogeneous null predicts at that many
samples per problem. Between-problem sd 205.50 tokens against a full-set mean
of 602.21.

It was computed to calibrate a cost projection (doc 2 section 5.3.1), not to
look for a signal. That is worth saying because it means the number was not
selected for being large.

**It is the strongest per-problem structure measured anywhere in this
project**, by a factor of five over the next:

| quantity | ratio to a homogeneous null | source |
|---|---|---|
| **mean completion length** | **119.66x** | Qwen, 198 problems, 12,672 samples, v1 store |
| per-problem accuracy | 24.9x | Qwen, 151 confirmatory problems |
| completion-length mode membership | 5.65x | MiniMax, 47 problems, `notes/max_tokens_estimate.md` |

Note the third row is the same underlying variable seen through a coarser lens
on a different model and a much smaller set. The first row is not a
replication of it and should not be reported as one.

## 2. Why it is the cheapest signal available

Every signal this project has tried needed something the provider had to agree
to supply. Completion length needs nothing.

| | needs logprobs | needs depth above 1 | needs an answer span | needs a reasoning field | provider-specific parsing |
|---|---|---|---|---|---|
| answer-token margin | yes | yes, depth 5 | yes | no | **yes, two shapes** |
| localised entropy | yes | yes | yes | no | yes |
| mean token entropy | yes | no | no | no | yes |
| reasoning-token count | no | no | no | **yes** | yes |
| **completion length** | **no** | **no** | **no** | **no** | **no** |

It is a single integer in the `usage` block of every response from every
provider, present in every sample this project or its predecessor has ever
stored, including the ones that truncated and the ones that returned no
parseable answer. It is available on models that refuse logprobs entirely,
which is most of the ones this account cannot reach. It costs nothing extra to
collect and it is already collected.

Two of the three signals above are also the ones whose failure is now
understood, which is the comparison that makes this candidate interesting
rather than merely convenient:

- **The entropy gate failed on aggregation, not on confidence**
  (`notes/entropy_signal.md`). The quantity was averaged into a scalar before
  the question was asked of it.
- **The answer-token margin has almost no dynamic range.** Median 24.25 nats
  across the v1 store, 79 percent of samples above 10 nats, and MD1 and MD2
  passed on the holdout precisely because the distribution is saturated: even
  a sample contradicting its own problem's plurality emits its answer at a
  median 20.5 nats. A gate needs spread, and a variable pinned near its
  ceiling has none. MD1 and MD2 are descriptive claims and are sound as such;
  the margin's weakness is as a routing signal, not as a description.

Completion length has the spread that both of those lack, and it is measured
on the axis the project's question is actually about, which is how much
compute a problem consumes.

## 3. The hypothesis worth designing later

Stated loosely on purpose, because tightening it into a registrable form is
the work that has not been done:

> Does per-problem mean completion length predict **where a problem's
> accuracy-versus-N curve peaks**, or **whether the problem backfires** at
> all?

That is the project's durable question rather than a side question. The
predecessor's published result is that self-consistency backfires on 56.6 and
65.7 percent of problems depending on the model, and the open part has always
been which problems, knowable in advance and cheaply. A per-problem property
carrying 120 times the between-problem structure of chance, obtainable from
one sample's usage block, is a better candidate for that than either signal
whose failure is now explained.

Things a real registration would have to settle, none of which are settled:

- Whether length is measured on one draw, on a few, or as a per-problem mean,
  and what it costs at each. The point of a cheap signal is spoiled if it
  needs 64 samples to estimate.
- Whether the relationship survives controlling for per-problem accuracy.
  Long problems may simply be hard problems, and "hard problems backfire" is
  a weaker and possibly already known claim. This is the control that decides
  whether the hypothesis is interesting.
- Which direction is predicted, fixed before looking. Both are arguable:
  longer chains as more room to go wrong, or longer chains as genuine
  difficulty where extra samples help most.
- What the curve-peak outcome variable is, given that the aggregate curve on
  GPQA Diamond is flat across the grid (0.52 points) and the whole question
  has to be per-problem.
- A non-trivial baseline, the same requirement the "predicts beyond k"
  hypothesis already carries.

## 4. Why it is not being registered now

The plain reason: **there is no clean set left to register it against.**

| set | status |
|---|---|
| v1 exposed, 129 problems | burned by exploration, including the analysis that produced the 119.66x figure |
| v1 holdout, 69 problems | spent, one look, on MD1 and MD2 under `argmax-prereg-margin-desc-v1.0` |
| v2, 198 problems, in flight | the only clean confirmatory set, and **reporting its completion lengths spends it** |

The temptation is precise and worth naming: the v2 sampler is running right
now, its manifest carries a registered tag, and a hypothesis about completion
length could be registered before it lands and tested on data nobody has read.
That would be legitimate on the letter of the split discipline and wrong on
its substance. **The design has not been done.** Every open question in
section 3 would be answered by whatever the data turned out to support, which
is the failure the split discipline exists to prevent, wearing a tag that
makes it look like the opposite.

A tag cut to beat a running sampler is a tag cut without thinking.

**Consequence, recorded rather than deferred:** v2's completion lengths are
reported as ordinary run diagnostics when it lands, treated as **exploratory**
and labelled so.

### What that does and does not spend

**Correction.** An earlier version of this section said the 198 would then be
"fully read for length on both models, and no amount of care recovers that".
That is too strong and it misapplies doc 2 section 8.1, under which exposure
is **analysis-specific**: what an analysis exposes is the question it asked,
not every question that could be asked of the same column.

Reporting the **marginal** distribution of completion length exposes the
marginal. It does not expose the **joint** of length with outcome, which is
where the hypothesis lives:

| quantity | status after v2's diagnostics are reported |
|---|---|
| length marginal: mean, sd, quantiles, truncation | **exposed**, reported as an exploratory run diagnostic |
| length by per-problem accuracy | **unread** |
| length by curve shape or peak N | **unread** |
| length by whether a problem backfires | **unread** |

So the rule for v2 is narrow and enforceable: **report the distribution, do not
cross it with anything.** No correlation against per-problem accuracy, no
split by curve shape, no backfire contrast, on the v2 store. The ledger
records the joint as unread so a later analyst can see it was preserved
deliberately rather than by oversight.

A confirmatory test of the length hypothesis on v2 would still have to reckon
with the marginal having been seen, which is a weaker constraint than the
whole set being burned and is the sort of thing a registration states rather
than something that forecloses one.

This is the right trade. Reporting the diagnostics of a paid confirmatory run
is not optional, and a candidate hypothesis does not get to make a run's own
results unreportable. It does not have to cost more than it costs.

## 5. Design information: is length just difficulty?

**This is not a test of the hypothesis in section 3.** It is a check on a
confound, run on the v1 **exposed 129** which are already spent, precisely so
that it costs nothing. **Accuracy here is a covariate, not the outcome.** The
outcome variable of the real hypothesis is curve shape or backfire, and
neither is touched here or anywhere on a clean set.

Per-problem mean completion length against per-problem single-sample accuracy,
129 problems, answer rate 0.9943 over them, cluster bootstrap over problems at
10,000 resamples:

| | estimate | 95 percent interval |
|---|---|---|
| Pearson r | **-0.0019** | [-0.1809, +0.1789] |
| Spearman r | **+0.0046** | [-0.1761, +0.1825] |

| | value |
|---|---|
| length variance explained by accuracy, r squared | **0.0000** (95 percent up to 0.0425) |
| **length variance independent of accuracy** | **1.0000** (95 percent from 0.9575) |
| residual length sd after removing accuracy | **190.7 tokens**, against a raw sd of 190.7 |

Length mean 589.2 sd 190.7; accuracy mean 0.3487 sd 0.3072.

**Which reading this supports.** The two readings set out in advance were: if
length and accuracy are near-collinear, the hypothesis is "hard problems
backfire" restated and probably should not be registered; if length carries
substantial independent variance, there is something worth designing.

The second, on the linear reading. Both correlations sit within 0.005 of zero,
both intervals are near-symmetric about zero, and accuracy accounts for no
measurable part of length's spread. The residual sd is unchanged to one
decimal place, because there is nothing to remove.

**Correction to the first version of this section, which said length and
accuracy were "essentially orthogonal" and that "long problems are not hard
problems".** Both statements were too strong, and the caution listed
immediately below them turned out to be the live case. The shape was checked
and it is not flat.

## 6. The shape: a U, suggestive and not established

Per-problem mean completion length in quintiles, accuracy within each, cluster
bootstrap over problems at 10,000 resamples. **The answer rate is in the same
table** under doc 4 section 9.1, and it is the column that decides whether the
right arm is a shape or a selection effect:

| quintile | n | mean length | accuracy | 95 percent interval | answer_rate | truncation | hit_ceiling |
|---|---|---|---|---|---|---|---|
| 1 shortest | 25 | 356.2 | **0.4441** | [0.3123, 0.5784] | **0.9819** | 0.0000 | 0.0000 |
| 2 | 26 | 486.9 | 0.3400 | [0.2326, 0.4569] | 0.9964 | 0.0024 | 0.0024 |
| 3 middle | 26 | 568.8 | **0.2218** | [0.1340, 0.3233] | 1.0000 | 0.0000 | 0.0000 |
| 4 | 26 | 640.9 | 0.3316 | [0.2248, 0.4460] | 0.9970 | 0.0024 | 0.0024 |
| 5 longest | 26 | 884.3 | **0.4098** | [0.2957, 0.5331] | 0.9958 | 0.0060 | 0.0060 |

Length ranges by quintile: 166 to 430, 437 to 528, 528 to 610, 610 to 682,
725 to 1197.

### The truncation mechanism, ruled out rather than assumed

Long problems against a 2048 cap are where truncation should concentrate, so
this is the specific alternative explanation for the right arm, not a
speculative one. It does not hold:

- **The answer rate does not fall with length.** The lowest rate is in the
  **shortest** quintile at 0.9819, not the longest at 0.9958. Whatever costs
  answers here, it is not running out of budget.
- **Truncation is 0.60 percent at its worst**, in Q5, and identical to
  `hit_ceiling` in every quintile, which is the expected relationship and a
  check that neither column is measuring something else.
- **Both arms survive scoring unanswered samples as incorrect.** Scored that
  way rather than excluded:

| quintile | accuracy excluding unanswered | accuracy scoring unanswered incorrect | change | answer_rate |
|---|---|---|---|---|
| 1 | 0.4441 | 0.4294 | -0.0148 | 0.9819 |
| 2 | 0.3400 | 0.3371 | -0.0029 | 0.9964 |
| 3 | 0.2218 | 0.2218 | +0.0000 | 1.0000 |
| 4 | 0.3316 | 0.3311 | -0.0005 | 0.9970 |
| 5 | 0.4098 | 0.4093 | -0.0005 | 0.9958 |

| contrast | excluding unanswered | scoring unanswered incorrect |
|---|---|---|
| Q5 minus Q3, right arm | +0.1880 [+0.0354, +0.3375] | **+0.1875** [+0.0349, +0.3431] |
| Q1 minus Q3, left arm | +0.2224 [+0.0591, +0.3825] | **+0.2076** [+0.0472, +0.3644] |

Both still exclude zero, and the right arm moves by 0.0005. **The right arm is
not a selection effect from truncation.** The left arm is the one that moves
at all, by 0.0148, because the shortest quintile is where the unanswered
samples are, which is the opposite of the mechanism that was worth ruling out.

Both extremes above the middle, near-symmetric arms. Tested by direct
resampled contrasts rather than by reading the overlap of those intervals,
which is the fallacy this repository already removed once from `classify_curve`:

| contrast | difference | 95 percent interval | |
|---|---|---|---|
| Q1 minus Q3, short vs middle | **+0.2224** | [+0.0564, +0.3834] | excludes zero |
| Q5 minus Q3, long vs middle | **+0.1880** | [+0.0323, +0.3414] | excludes zero |
| Q1 minus Q5, short vs long | +0.0344 | [-0.1473, +0.2130] | crosses zero, arms symmetric |
| Q1+Q5 minus Q2+Q3+Q4 | +0.1288 | [+0.0208, +0.2392] | excludes zero |

**But the shape-agnostic test does not reach significance.** Fitting a
quadratic in standardised length:

| term | estimate | 95 percent bootstrap | permutation p |
|---|---|---|---|
| linear | -0.02654 | | |
| **quadratic** | **+0.03050** | [-0.00617, +0.06487] | **0.083** |

Positive as a U requires, and it does not clear 0.05 against 10,000 label
shuffles.

**How to read the disagreement.** The quintile contrasts are the more
favourable analysis and the less trustworthy one: quintile boundaries and,
worse, the Q1+Q5-against-the-middle contrast were chosen **after** seeing the
bin means, on a set that was already exposed. The quadratic term was not
chosen that way and is the honest global test. **So: a U-shape is suggestive,
consistently signed, and not established at n=129.**

### The bimodality reading, tested and not supported

A per-problem mean over 64 samples averages away shape. **A problem whose
samples split between short and long lands mid-range by construction**, so the
middle quintile could be enriched for split problems rather than for
consistently middling ones, and the U would then be about consistency rather
than about length. This is not speculative here: this project already found
within-problem length bimodality on another model, with mode membership a
per-problem property at 5.65x its null (`notes/max_tokens_estimate.md`).

Within-problem sd of completion length, by quintile of per-problem mean:

| quintile | n | mean length | within-problem sd | 95 percent interval | CV, sd over mean | answer_rate |
|---|---|---|---|---|---|---|
| 1 shortest | 25 | 356.2 | 66.7 | [59.7, 74.0] | 0.1944 | 0.9819 |
| 2 | 26 | 486.9 | 95.6 | [77.2, 126.4] | 0.1976 | 0.9964 |
| 3 middle | 26 | 568.8 | **110.5** | [96.0, 127.7] | **0.1940** | 1.0000 |
| 4 | 26 | 640.9 | 143.8 | [118.2, 178.3] | 0.2243 | 0.9970 |
| 5 longest | 26 | 884.3 | 198.4 | [175.2, 221.1] | 0.2264 | 0.9958 |

**Within-problem sd does not peak in the middle. It rises monotonically with
mean length**, which is the ordinary scale relationship and nothing more:
sd against mean length gives r = **+0.6064** [+0.4517, +0.7873], excluding
zero. The CV removes that scale effect and is close to flat at 0.194 to 0.226,
with the middle quintile carrying the **lowest** value of the five.

Contrasts, since the question was specifically whether the middle is enriched:

| contrast | within-problem sd | CV |
|---|---|---|
| Q3 minus Q1+Q5 | -23.30 [-49.99, +4.29] | -0.01672 [-0.04920, +0.01781] |
| Q3 minus all others | -16.16 [-38.03, +6.33] | -0.01687 [-0.05067, +0.01831] |

All four cross zero, and **all four are negative**: the middle quintile is if
anything the most internally consistent, not the least. The enrichment the
mechanism predicts would be a positive contrast, and the point estimates run
the other way.

Within-problem sd is also unrelated to per-problem accuracy: r = **+0.0123**
[-0.1621, +0.1966], and on the CV +0.0732 [-0.1592, +0.2636]. Both cross zero.
So consistency of length does not track difficulty either.

**Reading: the U is not about consistency.** Whatever the middle quintile is,
it is not a pile of split problems averaging into the middle. The eventual
hypothesis is not redirected by this, and the label on the U is unchanged:
suggestive, not established. One mechanism that would have changed what the
shape means has been ruled out, which raises no confidence in the shape
itself.

Two limits. Within-problem sd is a coarse summary of shape and would not
distinguish a bimodal problem from a merely dispersed one; the bimodality
finding this tests against was mode membership on a fitted mixture, on a
different model, and that fit was not repeated here. And a contrast crossing
zero at n=26 per bin is weak evidence of absence.

### What this does to section 5

The near-zero linear correlation no longer licenses "accuracy does not explain
length". It licenses only that **no monotone relationship exists**, which is a
weaker claim, and the quintile pattern is a concrete alternative explanation
for the zero rather than a hypothetical one.

What survives, and it is the part that mattered for the confound question:
length is **not** per-problem difficulty on a monotone scale, so a hypothesis
built on length would not be "hard problems backfire" restated. A U would make
length a genuinely different axis from accuracy rather than the same one, since
difficulty relates to accuracy monotonically by construction. Both readings of
the shape therefore point the same way on the confound, which is the only
question section 5 was asked to answer.

What does not survive is any claim that length and accuracy are unrelated.
They may be related in a way a correlation cannot see.

**Not designing it now, and the U is a reason for more caution rather than
less.** A shape that appears at p = 0.083 on an exposed set, with its most
striking contrast selected after the fact, is exactly the kind of result that
looks like a discovery and replicates at chance. It is recorded so that a
future design tests it as a prediction on a clean set instead of rediscovering
it.

Three standing cautions, unchanged. This is one model on one benchmark whose
per-problem accuracy is itself extreme at 24.9x a null. The whole of sections
5 and 6 runs on the **exposed 129**, which is why it was free. And a confound
cleared is not a hypothesis supported: nothing here says length predicts
anything about curve shape, only that if it does, the prediction is not
difficulty in disguise.
