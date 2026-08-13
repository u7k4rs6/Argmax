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

_(regime check, manifest check, extraction and answer rate follow)_
