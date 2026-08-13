# Thread A's premise fails: GPQA Diamond is mixed for both models

Thread A tests whether Chen et al. 2024's scaling model breaks when the
easy/hard mixture it relies on is absent, using GPQA Diamond as the uniformly
hard case. That requires the benchmark to be uniformly hard **for the models
being run**, not for a human expert.

It is not. On per-problem single-sample accuracy across all 198 problems, both
models show heterogeneity 17 to 25 times what a single homogeneous rate
produces, with a mass of problems solved almost always and a mass solved almost
never. **The premise is false as stated, for both models, and not marginally.**

Read-only against the predecessor's confirmatory stores. No API calls.

## Provenance

| What | Value |
|---|---|
| Source repo | `github.com/u7k4rs6/self-consistency-backfire` |
| Read at commit | `a7f168e685b2eecf4793e2b635a6c801b6192d91` |
| Stores | `outputs/samples/` (Qwen, 13,058 samples), `outputs/samples_model2/` (Llama, 12,672) |
| Problems | 198 each, 64 samples per problem (Qwen: 64 to 103) |
| Date | 2026-08-13 |

Note this covers **all 198**, not the 151 with logprobs. Accuracy needs only
the extracted answer and the ground truth, both stored for every sample.

## 1. The distribution of per-problem accuracy

| | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| pooled accuracy | 0.3406 | 0.2684 |
| per-problem mean | 0.3393 | 0.2684 |
| sd | **0.2955** | **0.2292** |
| min | 0.0000 | 0.0000 |
| p5 | 0.0000 | 0.0156 |
| p25 | 0.0938 | 0.0781 |
| median | 0.2636 | 0.2109 |
| p75 | 0.5385 | 0.4219 |
| p95 | 0.9266 | 0.7102 |
| max | **1.0000** | 0.9375 |

Binned:

| accuracy | Qwen problems | Llama problems |
|---|---|---|
| exactly 0.00 | **12** | **6** |
| 0.00 to 0.05 | 23 | 31 |
| 0.05 to 0.25 | 63 | 77 |
| 0.25 to 0.50 | 48 | 48 |
| 0.50 to 0.75 | 22 | 27 |
| 0.75 to 0.95 | 20 | 9 |
| above 0.95 | **10** | 0 |

Qwen solves 10 problems on more than 95 percent of samples and 12 problems on
none. That is not a benchmark of uniform difficulty for this model.

## 2. Against a homogeneous null

The null is the premise: one rate for the whole benchmark, with per-problem
variation arising only from drawing 64 samples. 10,000 permutations, each
resampling every problem's successes binomially at the pooled rate with its own
sample count.

| | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| observed variance of per-problem accuracy | **0.0873** | **0.0525** |
| null variance, mean | 0.00343 | 0.00307 |
| null variance, 95th percentile | 0.00403 | 0.00359 |
| **variance ratio** | **25.5x** | **17.1x** |
| p, variance | **< 0.0001** | **< 0.0001** |
| problems at accuracy <= 0.05 or >= 0.95 | **45** | **37** |
| null expectation for that count | 0.0000 | 0.0004 |
| p, extremes | **< 0.0001** | **< 0.0001** |

Sampling noise at 64 draws produces a variance of about 0.003. The data show
0.087 and 0.053. The null produced 45 extreme problems in **none of 10,000
draws**, and produced any at all in essentially none.

## 3. Unimodal against two components

Fitting per-problem accuracy directly:

| | Qwen: one Gaussian | Qwen: two | Llama: one | Llama: two |
|---|---|---|---|---|
| AIC | 82.10 | **4.60** | -18.51 | **-85.63** |
| delta AIC favouring two | | **77.50** | | **67.11** |
| component means | 0.339 | **0.089** and **0.516** | 0.268 | **0.058** and **0.369** |
| component weights | | 0.415 and 0.585 | | 0.323 and 0.677 |

Both models split into a hard component the model almost never gets right and a
much easier component: on Qwen, 41.5 percent of problems at a mean accuracy of
0.089 alongside 58.5 percent at 0.516.

**One caution on this section, and it does not rescue the premise.** A
two-Gaussian fit beating one Gaussian shows the distribution is not normal
around a single centre. It does not prove exactly two discrete classes; a
continuous spread of difficulty would also win this comparison. The
distribution-free result in section 2 is the load-bearing one, and it refutes
homogeneity whichever shape the heterogeneity has. Chen et al.'s mechanism
needs a spread of per-query difficulty, and a spread is what is there.

## 4. What this does to Thread A

**The discriminating case Thread A was designed around does not exist in this
benchmark for these models.** GPQA Diamond is hard for expert humans and
google-proof by construction, and that is what "uniformly hard" was reaching
for. For a 7 to 8B policy sampling at temperature 0.7, it is a mixture: some
problems are effectively solved and some are effectively impossible.

Three ways forward, none of them chosen here:

1. **Drop Thread A as specified.** Its premise is refuted on the only two
   models this project can reach, and refuting your own premise before
   sampling is the cheapest possible outcome.
2. **Reformulate it as a test of the mechanism rather than its absence.** The
   mixture is present and now measured, with component weights and means. That
   makes GPQA Diamond a case where Chen et al.'s estimator **should** work, and
   testing whether it does is a different and still-live question. It is not
   what the kickoff brief specified.
3. **Find a genuinely unmixed task for these models.** Nothing in this project
   has one, and establishing that a task is unmixed for a given model requires
   exactly the measurement above, so it is a prerequisite rather than an
   assumption.

**The scope table's row A rests on the specification, so its eligibility is
now in question again.** Row A was marked eligible on the strength of Thread A
testing a mechanism claim by removing the mixture. The mixture cannot be
removed by choosing this benchmark. Under option 2 the row may still be
eligible, on a different sentence; under option 1 it is not.

## 5. Two heterogeneity results, one benchmark

This is the second per-problem property found in this data. The first, in
`notes/max_tokens_estimate.md` section 7, is that completion length is a
two-component mixture and which component a sample lands in is a property of
the problem, at 5.65 times its permutation null. This one is per-problem
accuracy at 17 to 25 times its null.

They are different axes and neither implies the other, but together they say
the same thing about experimental design on this benchmark: **per-problem
structure dominates, and any analysis that pools problems is averaging over a
mixture whose components differ by more than the effects being measured.**
Doc 2 section 7.1 already forbids pooling across answer rates for this reason.
The same argument applies to pooling across difficulty, and no document in this
repository currently says so.
