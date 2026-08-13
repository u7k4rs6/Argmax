# Pre-registration registry

One row per tag. Written when the tag is cut, never edited afterwards.

The predecessor ended with `pre-pilot-v6.0` and `backfire-prereg-v1.0`
covering different hypothesis sets, and nearly cited the wrong one in the
paper. This file exists so that "which pre-registration covers this claim" is
answerable from one table.

## Rules

- Tag format is `argmax-prereg-<phase>-v<major>.<minor>`. No exceptions.
- Tags matching `argmax-prereg-*` are protected against deletion and
  force-push. A tag that can be moved is not a pre-registration.
- A tag is cut **before** the confirmatory samples for its phase are drawn.
- If a pre-registration turns out to be wrong, cut a new tag with a new
  version and add a row. Never move an existing one.
- Confirmatory analysis refuses to run without a `prereg_tag` in the manifest.
  The tag recorded there must appear in this table.

## Registry

| Tag | Date | Commit | Hypotheses covered | Analyses that may cite it |
|---|---|---|---|---|
| `argmax-prereg-margin-desc-v2.0` | 2026-08-14 | `PENDING` | MD3, MD4 | Second-model replication of the descriptive margin claims on `Qwen/Qwen3.5-9B` with the thinking phase disabled, 198 problems at M=16, cap 6144. Design, calibration, stratification check and limitations in `notes/margin_desc_v2.md`. Covers no gate claim, and explicitly does NOT cover MD1 or MD2, which are not testable at M=16. |
| `argmax-prereg-margin-desc-v1.0` | 2026-08-14 | `739c30b15a32` | MD1, MD2 | The two descriptive claims below, on the 69 unexposed problems of the margin-v1 store listed in `notes/exploration_ledger.md`. No gate claim is covered: the gate question is per-problem and was costed as unaffordable. |
| `argmax-prereg-threadA-v1.0` | 2026-08-13 | `edfae74728f6` | TA1, TA2a, TA2b | Thread A on the predecessor's stored samples, `notes/thread_a.md` phase 4. No Argmax sampling is covered by this tag. |

## Hypotheses

One row per hypothesis id. A hypothesis is not pre-registrable until every
field that decides it exists in the schema and every threshold is a literal
value here.

| Id | Statement | Deciding fields | Threshold | Direction | Tag |
|---|---|---|---|---|---|
| TA1 | On the confirmatory 151, the reconstructed few-sample estimator has lower per-problem regret than `naive_within_k` at k=8 | `per_problem_regret_difference.ci95_upper` (chen minus naive, paired over problems) | 0.0 | less | `argmax-prereg-threadA-v1.0` |
| TA2a | The same at k=4 | `per_problem_regret_difference.ci95_upper` | 0.0 | less | `argmax-prereg-threadA-v1.0` |
| TA2b | The same at k=16 | `per_problem_regret_difference.ci95_upper` | 0.0 | less | `argmax-prereg-threadA-v1.0` |
| MD1 | Among samples whose answer differs from their own problem's plurality, the median answer-token margin exceeds 15 nats | per-problem median of `answer_margin` over dissenting samples, one-sided 95% lower bound across problems | 15.0 | greater | `argmax-prereg-margin-desc-v1.0` |
| MD2 | Among those same dissenting samples, the fraction with a margin above 10 nats exceeds 0.60 | per-problem fraction of dissenting samples with `answer_margin > 10`, one-sided 95% lower bound across problems | 0.60 | greater | `argmax-prereg-margin-desc-v1.0` |
| MD3 | On Qwen3.5-9B with thinking disabled, among INCORRECT samples the median answer-token margin exceeds 15 nats | per-problem median of `answer_margin` over samples with `is_correct` false and `answer_margin_censored` false, one-sided 95% lower bound across problems | 15.0 | greater | `argmax-prereg-margin-desc-v2.0` |
| MD4 | Among those same incorrect samples, the fraction with a margin above 10 nats exceeds 0.60 | per-problem fraction of incorrect samples with `answer_margin > 10`, one-sided 95% lower bound across problems | 0.60 | greater | `argmax-prereg-margin-desc-v2.0` |

**MD1 and MD2 are one-sample bounds, deliberately.** The finding they test is
that a sample contradicting its own problem's plurality still emits its answer
with near-certainty, because it is certain given the chain it has just written.
That is a statement about the dissenting group's own distribution, not about a
difference between two groups, and stating it as a difference would make a
small gap between saturated distributions carry a claim about saturation.

**The unit is the problem, not the sample.** Each problem contributes one
median and one fraction; the bound is taken across problems. Problems with
fewer than three dissenting samples are excluded and the exclusion count is
reported. On the exposed 129 that rule excluded 7.

**The two-sample equivalence is NOT registered.** It was checked first and does
not resolve: on the exposed problems the per-problem median-margin difference
has sd 7.3036, so at n=69 a TOST band must exceed **2.89 nats** to be
clearable. A band that wide would pass on noise rather than on equality, and
registering a test built to pass is worse than registering nothing.

TA1 is the decision. TA2a and TA2b are **registered as underpowered and are
reported, not decided**: their exploratory effects are 0.96 and 0.87 of their
own confirmatory resolution, computed before registration in
`notes/thread_a.md` phase 2.

**Aggregate regret is not a hypothesis here.** On the exploratory split every
method names N=64 and every pairwise difference is identically zero, so no
sample size resolves it. That is recorded as a finding rather than registered
as a test.

## Claims

One row per `claim_id`. A claim is a sentence that may appear in the paper.
`tests/falsification.py` fails when a registered claim has zero backing rows
in its artifact table.

| Claim id | Sentence it licenses | Backing artifact table | Rows required |
|---|---|---|---|
| _(none yet)_ | | | |

## Thresholds

Threshold values are asserted by the falsification suite against the tagged
commit, not merely used to compute a verdict. A regenerated result whose
threshold was quietly edited must fail loudly rather than pass against a moved
line.

| Threshold name | Value | Set in | Tag | Rationale |
|---|---|---|---|---|
| `ta1_ci_upper` | 0.0 | `notes/thread_a.md` phase 3 | `argmax-prereg-threadA-v1.0` | The paired 95 percent CI on the per-problem regret difference must lie entirely below zero. A point estimate favouring the estimator is not enough. |
| `ta1_resolution_floor` | 0.0161 | `notes/thread_a.md` phase 2 | `argmax-prereg-threadA-v1.0` | The design's own minimum detectable effect at n=151 and k=8. Registered so that a PASS smaller than the resolution that produced it is visible as such rather than quietly reported as a win. |
| `md1_threshold` | 15.0 | `notes/exploration_ledger.md` | `argmax-prereg-margin-desc-v1.0` | Nats. Set below the exposed-set estimate of 20.6155 so it is a prediction, not a restatement, and above the 10-nat line MD2 uses so the two claims are not the same claim twice. 15 nats is 3.3 million to one. |
| `md2_threshold` | 0.60 | `notes/exploration_ledger.md` | `argmax-prereg-margin-desc-v1.0` | Set below the exposed-set estimate of 0.7489. Clears only if most dissenting samples are saturated. |
| `md_resolution_median` | 1.0018 | `notes/exploration_ledger.md` | `argmax-prereg-margin-desc-v1.0` | Standard error of the per-problem median margin at n=69, from the exposed set's sd of 8.3213. The design's own resolution, registered so a pass inside it is visible. |
| `md_resolution_fraction` | 0.0278 | `notes/exploration_ledger.md` | `argmax-prereg-margin-desc-v1.0` | The same for the fraction above 10 nats, from an sd of 0.2309. |
| `md_alpha` | 0.05 | `notes/exploration_ledger.md` | `argmax-prereg-margin-desc-v1.0` | One-sided, fixed before the holdout was read. |
| `md3_threshold` | 15.0 | `notes/margin_desc_v2.md` | `argmax-prereg-margin-desc-v2.0` | Nats. Below the v1 exposed per-problem estimate of 21.5365, so it is a prediction. Same value as `md1_threshold` deliberately, to keep the two registrations on one scale. Held unchanged after the stratification check found no dependence on per-problem accuracy. |
| `md4_threshold` | 0.60 | `notes/margin_desc_v2.md` | `argmax-prereg-margin-desc-v2.0` | Below the v1 exposed per-problem estimate of 0.7617. Held unchanged for the same reason. |
| `md_v2_incorrect_floor` | 3.0 | `notes/margin_desc_v2.md` | `argmax-prereg-margin-desc-v2.0` | Minimum measured-margin incorrect samples for a problem to enter the analysis. Excluded problems are counted and reported, never imputed. At M=16 this admits only problems at accuracy at or below 13 of 16, which is the selection the stratification check was run to license. |
| `md_v2_stratification_corr_upper` | 0.1817 | `notes/margin_desc_v2.md` | `argmax-prereg-margin-desc-v2.0` | Upper end of the bootstrap interval on the correlation between per-problem accuracy and median margin among incorrect samples, [-0.1927, +0.1817]. Registered because the decision to leave the thresholds unrecalibrated rests on this interval crossing zero. |
| `md_v2_answer_rate_reference` | 0.9950 | `notes/margin_v1_run.md` | `argmax-prereg-margin-desc-v2.0` | The v1 answer rate this run must match to be comparable under doc 2 section 7.1. Cap 6144 was chosen because it reaches it (probe 1.0000); the caps are deliberately unmatched. |
| `md_v2_alpha` | 0.05 | `notes/margin_desc_v2.md` | `argmax-prereg-margin-desc-v2.0` | One-sided, fixed before any confirmatory sample. |
| `ta1_alpha` | 0.05 | `notes/thread_a.md` phase 2 | `argmax-prereg-threadA-v1.0` | Two-sided, conventional, fixed before the confirmatory run. |
