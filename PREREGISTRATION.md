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
| `ta1_alpha` | 0.05 | `notes/thread_a.md` phase 2 | `argmax-prereg-threadA-v1.0` | Two-sided, conventional, fixed before the confirmatory run. |
