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
and labelled so. That spends v2 for this purpose. After it, a confirmatory
test of the length hypothesis needs problems this project has not sampled: a
different benchmark, or a different model on the same 198 with the length
question fixed in advance. GPQA Diamond's 198 are then fully read for length
on both models, and no amount of care recovers that.

This is the right trade. Reporting the diagnostics of a paid confirmatory run
is not optional, and a candidate hypothesis does not get to make a run's own
results unreportable.
