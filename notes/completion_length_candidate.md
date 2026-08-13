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

This is as clean a version of the second as the data could have produced.
Length and accuracy are not merely non-collinear, they are **essentially
orthogonal**: both correlations sit within 0.005 of zero, both intervals are
near-symmetric about zero, and accuracy accounts for no measurable part of
length's spread. The residual sd is unchanged to one decimal place, because
there is nothing to remove. **Long problems are not hard problems on this
store.**

So the 119.66x between-problem structure in section 1 is not per-problem
difficulty wearing a different name. Whatever it is, accuracy does not explain
it, and a hypothesis built on it would not be a restatement of a known result.

Three cautions on how far this goes. It is one model on one benchmark whose
per-problem accuracy is itself extreme at 24.9x a null. Near-zero correlation
rules out a **linear or monotone** relationship, not a non-monotone one, and a
U-shape in length against difficulty would show up exactly like this. And a
confound cleared is not a hypothesis supported: nothing here says length
predicts anything about curve shape, only that if it does, the prediction is
not accuracy in disguise.

**Not designing it now.** The remaining questions in section 3 are untouched,
and this result closes exactly one of them.
