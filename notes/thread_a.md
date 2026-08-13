# Thread A on stored data, under split discipline

Thread A reformulated asks whether a few-sample estimator of the optimal call
count lands where a full run measures the optimum, on a benchmark whose
easy/hard mixture is present and quantified. It is computable from the
predecessor's stored samples and costs nothing.

Read-only against `self-consistency-backfire` at `a7f168e6`, model
`Qwen/Qwen2.5-7B-Instruct-Turbo`, the only one still reachable. No API calls.

**Order of operations, and it matters:** everything below phase 1 was fixed
before the confirmatory problems were touched, the resolution was computed
before the thresholds were registered, and the registration happened before
the confirmatory run.

---

## Phase 1. Every free choice, fixed on the exploratory split only

**The split.** 47 exploratory and 151 confirmatory, which is the study's own
pre-registered split. The exploratory 47 are identifiable in the store without
using labels: they are the problems with no logprobs, sampled in the original
pilot run, and they are exactly the 47 in `outputs/entropy_baseline/`.

The brief said "the exploratory 50". `data/problem_ids.json` does list 50, but
3 of those sit inside the paper's confirmatory 151, so tuning on 50 would put
three confirmatory problems into the tuning set. 47 is used instead. That is a
deviation from the instruction, in the direction of a cleaner split.

### The choices, and how each was made

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

Recorded as `frozen.json` and consumed by the confirmatory run, which refuses
to start without the prereg tag.

### Contamination, stated rather than papered over

**The mixture measurement used all 198 problems, including the confirmatory
151.** `notes/mixture_premise.md` established that per-problem accuracy varies
at 25.5 times a homogeneous null across the full benchmark, and that result is
the premise of the reformulated Thread A. So the confirmatory set is not clean
of the reasoning that motivated the design.

What that does and does not affect:

- **It does not affect the estimator or the baselines.** Neither reads the
  mixture measurement. They see only their own `k` samples.
- **It does affect the claim that this is a fair test of the premise.** The
  benchmark was chosen as a mixture case partly on evidence from the same
  problems the hypothesis is tested on. A reader is entitled to discount the
  premise accordingly.
- **The honest description** is that the confirmatory split is held out from
  the parameter fixing and from the metric choice, and not from the decision to
  run this experiment at all.

Re-running the mixture measurement on the exploratory 47 alone gives a ratio of
**24.1x**, against 25.5x on all 198, so the premise survives on uncontaminated
data. That is a repair, not an erasure: the number that motivated the design
was computed on everything.

---

## Phase 2. The resolution, computed before any threshold was written

### The aggregate comparison is unresolvable, at any sample size

On the exploratory 47 the aggregate vote-accuracy curve rises monotonically:

| N | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| aggregate accuracy | 0.4176 | 0.4179 | 0.4454 | 0.4668 | 0.4866 | 0.5012 | **0.5319** |

`N* = 64`, the largest grid point. And at every k, all three methods name it:

| k | Chen | naive_within_k | always_max |
|---|---|---|---|
| 4 | 64 | 64 | 64 |
| 8 | 64 | 64 | 64 |
| 16 | 64 | 64 | 64 |

All three therefore have aggregate regret of exactly **0.0000**, and every
pairwise difference is exactly zero **by construction rather than by
measurement**. No number of problems resolves a difference that is identically
zero. The PASS condition as drafted in the PRD, "aggregate regret smaller than
every baseline", cannot be met or missed.

**This is a finding, not only a design problem.** Chen et al.'s estimator
exploits a rise-then-fall aggregate curve. On this benchmark and this model the
curve does not fall. The mixture is present, at 24x the homogeneous null, and
the aggregate still rises monotonically to the grid boundary, because the easy
component's gains outweigh the hard component's losses at every N on the grid.
**Mixture presence is necessary for non-monotonicity but not sufficient**, and
this benchmark is a case that separates the two.

### The per-problem comparison is resolvable, and it is what the design becomes

Per-problem paired regret difference, Chen minus naive, at the frozen
configuration on the exploratory 47. Negative favours Chen.

| k | mean difference | sd across problems | MDE at n=151 | observed / MDE |
|---|---|---|---|---|
| 4 | **-0.0399** | 0.1824 | 0.0416 | 0.96 |
| **8** | **-0.0266** | 0.0706 | **0.0161** | **1.65** |
| 16 | **-0.0105** | 0.0528 | 0.0120 | 0.87 |

MDE is the minimum detectable paired difference at alpha 0.05 two-sided and 80
percent power, `(z(0.975) + z(0.80)) * sd / sqrt(151)`.

**k=8 is the only k whose exploratory effect exceeds its own confirmatory
resolution.** k=4 and k=16 sit at 0.96 and 0.87 of theirs, so they are
underpowered by design and are reported rather than decided.

For scale, what 151 problems can resolve between grid points at all:

| pair | mean difference on exploratory | MDE at n=151 |
|---|---|---|
| N=1 against N=64 | +0.1143 | 0.0671 |
| N=16 against N=64 | +0.0453 | 0.0396 |
| N=32 against N=64 | +0.0307 | 0.0310 |

The last row is the boundary of what this design can see: a 3-point difference
between adjacent grid points is right at the resolution limit.

### The design was rewritten before registration, not after

| | drafted in the PRD | registered |
|---|---|---|
| primary metric | aggregate regret | **per-problem regret** |
| primary k | all three equally | **k=8**, the only resolvable one |
| aggregate regret | primary | descriptive, with its degeneracy stated |

---

## Phase 3. Registration

`PREREGISTRATION.md` carries the hypothesis, the thresholds and the tag
`argmax-prereg-threadA-v1.0`. One tag, one row, per doc 2 section 8.3. The
confirmatory runner checks the tag exists and refuses to start without it.

---

## Phase 4. The confirmatory result

_(filled in after the tagged run)_
