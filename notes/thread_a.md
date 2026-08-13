# Thread A on stored data, under split discipline

Thread A reformulated asks whether a few-sample estimator of the optimal call
count lands where a full run measures the optimum, on a benchmark whose
easy/hard mixture is present and quantified. It is computable from the
predecessor's stored samples and costs nothing.

Read-only against `self-consistency-backfire` at `a7f168e6`, model
`Qwen/Qwen2.5-7B-Instruct-Turbo`, the only one still reachable. No API calls.

**Two findings lead, because they bound what the registered verdict means.**
The registered result follows them, unchanged.

---

## Finding 1. The mixture is present and the aggregate curve is still flat

Chen et al.'s estimator exists to locate the turn in a rise-then-fall aggregate
curve, and attributes that turn to a mixture of easy and hard queries within a
task. On the confirmatory 151, the mixture is emphatically present and the
curve does not turn:

| N | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| aggregate accuracy | 0.3193 | 0.3196 | 0.3238 | 0.3241 | 0.3234 | 0.3235 | **0.3245** |

| Quantity | Confirmatory 151 | Exploratory 47 |
|---|---|---|
| pooled single-sample accuracy | **0.3192** | 0.4153 |
| between-problem variance against a homogeneous null | **24.9x** | 24.1x |

The whole grid spans **0.52 accuracy points**, so the maximum aggregate regret
any method can incur is 0.0052 and the optimal call count is undefined for any
practical purpose. On the exploratory split the curve is monotone increasing to
the grid boundary instead, which is a different shape and the same conclusion.

**So mixture presence is necessary for the non-monotonicity Chen et al. model,
and it is not sufficient.** At 24.9 times the homogeneous null this benchmark
has as much within-task difficulty structure as anyone could ask for, and the
easy component's gains still cancel the hard component's losses at every grid
point rather than turning the curve over. A benchmark can satisfy the premise
of that model and still present nothing for it to find.

This is why the registered design measures per-problem regret. It is also why
the aggregate question is not merely unanswered here but unaskable: any test of
"did the estimator find the aggregate optimum" passes trivially when every
grid point is within half a point of optimal.

## Finding 2. TA1 bounds a verifier-free estimator from above and does not measure one

**The estimator is given ground-truth labels for its `k` samples.** So is every
baseline. A deploy-time signal has none: that is the entire difficulty of the
problem the published study leaves open, and its finding is that the
verifier-free signals it tested move accuracy less than 0.002.

What follows from that, and what does not:

- **A pass is an upper bound.** If a labelled estimator with k samples per
  problem could not beat a labelled naive baseline, no verifier-free version
  of it could. The converse does not hold, so a pass says the mechanism has
  headroom to be worth attempting without labels, not that it works without
  them.
- **The gap between the bound and a deployable method is not small.** Labels
  are what make the per-problem estimate possible at all here; strip them and
  the estimator has only agreement structure, which is the signal the published
  study measured and found insufficient.
- **Nothing in this note is a routing method.** It is a measurement of how much
  of the per-problem headroom is reachable when difficulty is known, which
  bounds what any signal for estimating difficulty could deliver.

---

## The registered result

Run at `argmax-prereg-threadA-v1.0`, on the 151 confirmatory problems, with the
frozen configuration. The runner checks the tag exists and refuses otherwise.
Verdicts as registered, unchanged.

Per-problem regret, lower is better. `always_max` is fixed-budget voting at
N=64, which is what the published study does.

| method | k=4 | k=8 | k=16 |
|---|---|---|---|
| **chen (reconstruction)** | **0.0510** | **0.0317** | **0.0087** |
| naive_within_k | 0.0696 | 0.0529 | 0.0128 |
| always_max | 0.0962 | 0.0962 | 0.0962 |
| always_one | 0.1015 | 0.1015 | 0.1015 |

Exact-match rate on the per-problem optimum:

| method | k=4 | k=8 | k=16 |
|---|---|---|---|
| chen | 0.384 | 0.430 | 0.444 |
| naive_within_k | 0.371 | 0.430 | 0.517 |
| always_max | 0.139 | 0.139 | 0.139 |
| always_one | 0.325 | 0.325 | 0.325 |

Paired per-problem regret difference, chen minus naive, negative favours the
estimator:

| id | k | mean | 95 percent CI | registered threshold | verdict |
|---|---|---|---|---|---|
| **TA1** | **8** | **-0.0213** | **[-0.0335, -0.0091]** | CI upper below 0.0 | **PASS** |
| TA2a | 4 | -0.0186 | [-0.0332, -0.0041] | CI upper below 0.0 | PASS, underpowered |
| TA2b | 16 | -0.0040 | [-0.0085, +0.0004] | CI upper below 0.0 | **FAIL** |

TA1 passes by more than the resolution that produced it: the registered floor
`ta1_resolution_floor` is 0.0161 and the observed effect is 0.0213. TA2a passes
despite being registered as underpowered. TA2b fails by 0.0004.

The advantage peaks and erodes, 1.86 points at k=4, 2.13 at k=8, 0.40 at k=16,
which is the shape the mixture story predicts: modelling per-problem structure
helps most when there is too little data to measure it directly. At k=16 the
naive baseline has the better exact-match rate, 0.517 against 0.444, while
still losing on regret.

---

## Post-hoc: is the advantage regularisation rather than structure?

**Post-hoc. Not registered, not covered by any tag, added after the
confirmatory result was seen.** It asks one question the registered comparison
cannot: does the estimator win because it models per-problem structure, or
merely because it declines to trust a curve measured on `k` samples?

The test is a third baseline, `shrunk_within_k`: identical to `naive_within_k`
in measurement, argmax and boundary rule, with each problem's measured curve
pulled toward the pooled curve by

    curve_i(N) <- (k * curve_i(N) + m * pooled(N)) / (k + m)

and no mixture model anywhere. If it matched the estimator, the advantage would
be regularisation.

Per-problem regret on the confirmatory 151:

| method | k=4 | k=8 | k=16 |
|---|---|---|---|
| chen | **0.0510** | **0.0317** | **0.0087** |
| naive_within_k | 0.0696 | 0.0529 | 0.0128 |
| shrunk, m=1 | 0.0765 | 0.0458 | 0.0142 |
| shrunk, m=k | 0.0773 | 0.0500 | 0.0142 |
| shrunk, m=4k | 0.0794 | 0.0509 | 0.0147 |

Paired difference, chen minus shrunk, at m=k:

| k | mean | 95 percent CI |
|---|---|---|
| 4 | -0.0263 | [-0.0416, -0.0111] |
| 8 | -0.0184 | [-0.0316, -0.0051] |
| 16 | -0.0055 | [-0.0101, -0.0008] |

**Shrinkage does not match the estimator, and mostly makes things worse than
doing nothing.** At k=4 and k=16 every shrinkage strength is worse than plain
`naive_within_k`; at k=8 the weakest shrinkage helps a little (0.0458 against
0.0529) and still loses to the estimator by a margin whose interval excludes
zero at every k.

The exact-match rates say why:

| method | k=4 | k=8 | k=16 |
|---|---|---|---|
| chen | 0.384 | 0.430 | 0.444 |
| shrunk, m=k | 0.185 | 0.325 | 0.325 |

Shrinking toward the pooled curve pulls every problem's argmax toward the same
grid point, which is exactly the per-problem discrimination the task needs.

**So the advantage is not regularisation.** The remaining explanation is the
one thing the estimator has and neither baseline does: a generative model that
predicts per-problem accuracy at grid points **beyond** `k`. Both baselines can
only measure inside `k` and then apply a boundary rule. That is a sharper
description of the mechanism than "mixture structure", and it is post-hoc, so
it is a hypothesis for a future registration rather than a result.

---

## For the next registration, not this one

The post-hoc section above narrows the mechanism to "predicts beyond k" and
cannot test it, because both existing baselines stop at k by construction. A
registration of that hypothesis **needs a non-mixture extrapolating control**:
fit a simple parametric curve to the k measured points and extrapolate to the
grid, with no mixture model and no per-problem distribution.

If that control matches the estimator, extrapolation is the mechanism and the
mixture assumption is inert, which would be a sharper and more deflationary
result than the one recorded here. The control is registered **with** the
hypothesis, not added afterwards, because a control introduced after seeing the
result is not a control.

---

## How it was run

### Phase 1. Every free choice fixed on the exploratory split only

**The split.** 47 exploratory and 151 confirmatory, the study's own
pre-registered split. The exploratory 47 are identifiable in the store without
using labels: they are the problems with no logprobs, and they are exactly the
47 in `outputs/entropy_baseline/`.

The brief said "the exploratory 50". `data/problem_ids.json` does list 50, but
3 of those sit inside the paper's confirmatory 151, so tuning on 50 would put
three confirmatory problems into the tuning set. 47 is used instead, a
deviation in the direction of a cleaner split. Those 3 problems are their own
disclosure item; see `files/01-prd.md` section 4.4.

Every parameter was tuned **in its own method's favour**, so the confirmatory
comparison is not rigged toward either side.

| Choice | Value | How it was fixed |
|---|---|---|
| smoothing `alpha` | **1.0** | lowest exploratory regret for the estimator, at both draw counts |
| prediction draws | **2000** | ties with 500 at alpha=1.0, so the stabler one |
| `boundary_rule` for the naive baseline | **extrapolate_to_max** | its own best: exploratory regret 0.0000 against 0.0453 to 0.0865 for `stay` |
| ground-truth draws | 20,000 | precision, not a tuning knob |
| `M` cap | 64 | first 64 by `sample_idx`, so every problem has the same pool size |
| unanswered policy | exclude | doc 4; extraction failure is 0.1 percent here |
| tie-break over the grid | smallest N | the cheaper call count wins a tie |
| `k` | 4, 8, 16 | specified in the PRD, each a subset of the same stored M |

### Contamination, stated rather than papered over

**The mixture measurement used all 198 problems, including the confirmatory
151.** `notes/mixture_premise.md` established 25.5 times a homogeneous null
across the full benchmark, and that result is the premise of this design. So
the confirmatory set is held out from the parameter fixing and the metric
choice, and not from the decision to run the experiment at all.

It does not affect the estimator or the baselines, which read only their own
`k` samples. It does mean a reader may discount the premise. Recomputed on the
exploratory 47 alone the ratio is **24.1x**, so the premise survives on
uncontaminated data.

### Phase 2. The resolution, computed before any threshold was written

Per-problem paired regret difference at the frozen configuration on the
exploratory 47, against the minimum detectable effect at n=151, alpha 0.05
two-sided, 80 percent power:

| k | exploratory mean | sd | MDE at n=151 | observed / MDE |
|---|---|---|---|---|
| 4 | -0.0399 | 0.1824 | 0.0416 | 0.96 |
| **8** | **-0.0266** | 0.0706 | **0.0161** | **1.65** |
| 16 | -0.0105 | 0.0528 | 0.0120 | 0.87 |

k=8 is the only k whose exploratory effect exceeds its own confirmatory
resolution, which is why it is the registered decision and the other two are
registered as underpowered.

What 151 problems can resolve between grid points at all:

| pair | mean difference on exploratory | MDE at n=151 |
|---|---|---|
| N=1 against N=64 | +0.1143 | 0.0671 |
| N=16 against N=64 | +0.0453 | 0.0396 |
| N=32 against N=64 | +0.0307 | 0.0310 |

The design changed before registration as a result: primary metric from
aggregate regret to per-problem regret, primary k to 8, aggregate regret
demoted to descriptive.

### Phase 3. Registration

`PREREGISTRATION.md` carries the hypotheses, the thresholds and the tag
`argmax-prereg-threadA-v1.0`. One tag, one row, per doc 2 section 8.3.

---

## What this does not establish

1. **A reconstruction, not Chen et al.'s method.** Their code is not available
   to this project. A PASS is evidence about the mechanism as described in the
   Positioning section of arXiv:2608.11403, read as
   `paper/backfire_preprint.pdf`, not about their implementation.
2. **Labels were granted**, per finding 2.
3. **One model.** Llama-3-8B-Instruct-Lite is no longer serverless, so the
   cross-family replication the published study has is unavailable.
4. **The aggregate question is untouched**, per finding 1, because this
   benchmark cannot ask it.
