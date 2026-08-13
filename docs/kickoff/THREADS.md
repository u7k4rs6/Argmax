# Threads from the kickoff brief

Recorded here because a thread label used in scoping decisions was defined only
in the kickoff brief, which is not in this repository. An agent scoping row A
of the PRD searched both repositories for "Thread A", found nothing, and
proceeded on a guess that turned out to be wrong in a way that changed the
eligibility verdict. This file exists so that cannot recur.

**The kickoff brief itself is still not committed.** This file transcribes one
definition from it. Committing the brief to `docs/kickoff/` supersedes this
file and closes the gap properly.

---

## Thread A

**The prior work.** Chen et al. 2024 show that majority-vote accuracy can rise
and then fall as the number of LM calls grows. They attribute the
non-monotonicity to a **mixture of easy and hard queries within a task**: easy
queries are helped by more calls, hard ones are hurt, and the aggregate curve
turns over where the second group starts to dominate. They then use that
structure to estimate the optimal call count from a small number of samples.

**What Thread A tests.** Whether that scaling model breaks **when the mixture
is absent**, on a uniformly hard benchmark.

The prediction under Chen et al. is that a task with no easy component should
not show the rise-then-fall shape, because the shape is attributed to
composition. A uniformly hard benchmark is therefore the discriminating case,
and GPQA Diamond is the closest thing available to one.

**Why this is not the backfire paper's question.** arXiv:2608.11403, read as
`paper/backfire_preprint.pdf`, measures
how often majority vote hurts, per problem, on one hard benchmark, and shows a
deploy-time agreement gate cannot avoid it. It does not test a scaling model,
does not manipulate the mixture, and does not evaluate an optimal-call-count
estimator. Thread A tests a mechanism claim from a different paper by
manipulating the thing that claim rests on.

## Thread A, reformulated 2026-08-13

**The original premise was tested and it failed.** Thread A as specified needs
a benchmark that is uniformly hard for the models being run. GPQA Diamond is
not, for either model this project can reach: per-problem accuracy varies at
**25.5 times** the homogeneous null on Qwen and **17.1 times** on Llama, with
12 problems solved on none of 64 samples and 10 solved on more than 95 percent.
Evidence in `notes/mixture_premise.md`.

**The replacement tests the same estimator where the mixture is present and
measured**, rather than where it is absent. The mixture is no longer an
assumption in either direction: its weights and component means are estimated
from stored data, so the condition Chen et al. rely on is a known quantity
rather than a hoped-for one.

This is recorded as a reformulation, not a substitution. The original question
is not answerable on any benchmark this project has, because establishing that
a task is unmixed for a given model requires the same measurement that just
refuted the assumption here. Specification and costing are in `01-prd.md`
section 4.

**What this project already knows that bears on it.** From
`notes/max_tokens_estimate.md` section 7: completion length on GPQA Diamond is
a two-component mixture, and which component a sample lands in is **a property
of the problem**, not sampling noise, at 5.65 times the permutation null. So a
benchmark chosen for being uniformly hard still contains a strong within-task
mixture, just along a different axis than difficulty. That is a live
complication for Thread A rather than a settled input to it: "uniformly hard"
and "unmixed" are not the same condition, and this project has evidence that
the second does not follow from the first.

## Threads B and onward

Not transcribed. They were not needed for a scoping decision and guessing at
them here would repeat the error this file documents.
