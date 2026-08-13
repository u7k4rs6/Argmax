# margin-v1: the run, and how its regime check must be read

The one paid phase. 198 GPQA Diamond problems at M=64, Qwen2.5-7B-Instruct-Turbo,
cap 2048, logprobs at depth 5. It buys the answer-token margin and localised
entropy over the answer span, and nothing else.

**This section is written before the regime numbers are computed**, so that the
reading is fixed before the result is seen.

## The concurrency regimes, and why the comparison is confounded

The run was stopped once to raise concurrency from 4 to 16 after measuring 0.4
samples per second, which was 8.3 hours for the phase. Concurrency is not in
`param_hash` and changes nothing a sample contains, but hosted inference is not
batch invariant, so the store holds two regimes and a reader is entitled to see
the split.

**The sampler iterates problem-major.** `phase.py` builds its work list as

    for problem in problems:
        for index in range(M):

so it fills one problem's 64 samples before starting the next, and the stored
sample indices are contiguous per problem. That is the fact that decides how
the regime check can be read.

Measured at the boundary, with 2,182 samples stored across 35 problems:

| | problems |
|---|---|
| entirely at concurrency 4 | **11** |
| entirely at concurrency 16 | 23 |
| **spanning both regimes** | **1** |

The single straddling problem has 44 samples at concurrency 4 (indices 0 to 43)
and 20 at concurrency 16.

**So the regime comparison is between problems, not within them.** Any
difference in completion tokens, truncation rate, answer distribution or margin
between the two regimes is confounded with problem identity, and per-problem
accuracy on this benchmark varies at 24.9 times a homogeneous null
(`notes/mixture_premise.md`). Eleven problems against twenty-three is a
difference of samples and of subject matter at once, and the two cannot be
separated from this data.

The only unconfounded evidence available is that one straddling problem, which
is a paired comparison at n=1. It is worth looking at and it decides nothing.

**Therefore:** the regime check establishes whether the regimes differ, and a
difference is not evidence about batch invariance. Removing the confound needs
a deliberate interleaved re-draw, which is a separate and small spend: 20
problems at 8 samples per regime is about 320 samples, roughly $0.09. Not run
unprompted.

## Provenance of the manifests

Three run ids share this store, and their manifests are not all of a kind:

| run_id | samples | concurrency | manifest |
|---|---|---|---|
| `margin-smoke-20260813T162734` | 4 | 4 | **reconstructed** |
| `margin-v1-20260813T162932` | 744 | 4 | **reconstructed** |
| `margin-v1-20260813T170156` | the rest | 16 | contemporaneous |

The first two were written after their runs ended, from the ledger and the
stored records, because the smoke run's manifest was refused by the validator
(an M=2 pool under a grid topping at 64) and the second run was stopped to
raise concurrency before it could write one. A manifest assembled afterwards is
not a contemporaneous record, and `record_provenance` on each says which it is.

The third run's manifest will lack `concurrency_by_model`, because the process
loaded `phase.py` before that field existed. An empty mapping means the run
predates the field, not that concurrency was zero.

## Results

### Manifest check

Every manifest reads `max_tokens: 2048`, matching the published runs. No stop
condition.

### Regime check, read under the confound fixed above

| | concurrency 4 (n=748) | concurrency 16 (n=11,924) | difference |
|---|---|---|---|
| mean completion tokens | 647.6 | 599.4 | **+48.2** |
| truncation rate | 0.0013 | 0.0019 | -0.0006 |
| answer rate | 0.9987 | 0.9948 | +0.0039 |
| margin median | 24.000 | 24.000 | 0.000 |
| mean margin | 20.819 | 20.774 | +0.045 |

Margin distributions are indistinguishable, medians identical to three
decimals. The one apparent difference is 8 percent of completion length, and
**the straddling problem reverses its sign**: within that single problem, mean
completion is 945.9 at concurrency 4 against 969.0 at 16, so **-23 tokens
where the between-groups comparison gives +48**. Accuracy on one problem is not
reported. Suggestive at 44 draws against 20, not weighted.

Read as: no evidence the regimes differ, and the only number that looked like
a difference is better explained by which eleven problems fell before the
boundary. Not a batch-invariance result in either direction.

### Answer rate, doc 4 s4.1

| | rate | 95 percent interval |
|---|---|---|
| **Argmax** | **0.9950** | [0.9936, 0.9961] |
| published Qwen | 0.9946 | [0.9932, 0.9958] |

Difference +0.0004, intervals almost entirely overlapping. Comparability with
the published numbers holds on the output population, not only on the matched
prompts. Produced by `derive`, the same path `test_recompute.py` covers.

Store totals: 12,672 samples, $3.4122, 12,344 margins measured, 265 censored.

### The registered descriptive claims, on the 69 unexposed problems

One look, under `argmax-prereg-margin-desc-v1.0`. 64 of 69 problems carried at
least three dissenting samples; 5 were excluded by the registered rule.

| id | quantity | estimate | one-sided 95% lower bound | threshold | verdict |
|---|---|---|---|---|---|
| **MD1** | median margin, dissenting samples | 20.5232 | **18.8376** | 15.0 | **PASS** |
| **MD2** | fraction above 10 nats, dissenting | 0.7567 | **0.7105** | 0.60 | **PASS** |

Headroom above threshold: +3.84 nats and +0.11.

Both pass on problems no exploratory analysis had read, and the holdout
reproduces the exposed set closely: 20.52 against 20.62, and 0.757 against
0.749. **A sample that contradicts its own problem's plurality still emits its
answer at a median of 20.5 nats**, which is roughly 800 million to one. It is
certain given the chain it has just written, and the disagreement between
samples lives upstream in which chain got written.

The two-sample equivalence is not registered and not reported: it needed a
2.89-nat band at this n, which would pass on noise.
