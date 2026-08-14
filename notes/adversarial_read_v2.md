# Adversarial read of paper/draft_v2.md

One pass, hostile reviewer. Every body claim resolved to an artifact or
flagged. **Nothing fixed in this pass.**

Severity: **A** the claim is wrong or unsupported as stated; **B** the claim is
defensible but its stated provenance is not what it appears to be; **C**
imprecise, would survive review with a wording change.

---

## A1. The +0.0589 correctness separation does not reproduce. It is in the abstract.

**Where:** Abstract; §4.5 "The counterweight"; §8 by implication.

**Claim as written:** "The same margin does separate correct from incorrect
samples across the benchmark, by 0.0589 on the fraction above 10 nats with an
interval excluding zero."

**Recomputed on `data/derived/samples.jsonl`, 186 problems carrying both
correct and incorrect samples with measured margins:**

| unit | estimate | 95% cluster bootstrap |
|---|---|---|
| **per-problem, paired** (the unit MD1/MD2 use) | **-0.0168** | **[-0.0519, +0.0189]** |
| pooled sample-level | +0.0429 | not computed |

**Neither is 0.0589.** Worse, on the per-problem unit the paper uses
everywhere, the difference **crosses zero and its sign is negative**: incorrect
samples are, if anything, slightly *more* likely to sit above 10 nats.

This is the defect class the predecessor was caught by twice: **a sentence
describing a computation that was never run.** I wrote it from a figure quoted
in conversation and did not compute it before putting it in the abstract. No
scan covers this, because the sentence is well-formed and the number is
plausible.

**Consequence if left:** the paper's own counterweight paragraph, the one that
prevents the overclaim "log-probabilities are uninformative", is unsupported.
The reconciliation with Kumaran in §4.5 also leans on it.

**Note the reconciliation may survive anyway**, on the pooled unit or on a
correctly computed across-question statistic. But it must be computed, and the
number must be whichever one is true.

## A2. "Almost all of the average is prose" was never measured

**Where:** §4.4 Signal 2; echoed in §1 and the Abstract.

**Claim:** the entropy average over ~613 tokens is dominated by fluency, so a
gate thresholding it thresholds fluency.

**What exists:** a token *count* (median completion ~613 in the predecessor's
store; 602.21 mean in the margin-v1 store). **What does not exist:** any
decomposition of the entropy average into answer-token and non-answer-token
contributions. `notes/entropy_signal.md` records that per-token entropy arrays
were **never stored** by the predecessor, only a mean scalar. So the
decomposition is unavailable in principle from that store.

The claim is an inference from a count, not a measurement. As written it reads
as measured.

**It is computable now**, on the margin-v1 store, which stores full logprob
arrays. It has not been.

## A3. MiniMax's 0.2649 is a model-based extrapolation presented as a measurement

**Where:** §5.2 table, "answer rate 0.6460 at cap 16,384; **0.2649 at the
published 2048**"; repeated in §5.4.

0.6460 at 16,384 is measured on 404 stored records. **0.2649 at 2048 is a
right-censored fit extrapolated downward**, from `notes/max_tokens_estimate.md`.
The table's column header says "measurement". Two different epistemic objects
in one cell.

§5.4 then uses 0.2649 to argue the comparability rule. The argument holds at
either value, but the number should be labelled.

## A4. The 41,000-token cap and $4.19 rest on a fit flagged as unreliable

**Where:** §6, "puts the cap required for the registered 0.9950 answer rate
near 41,000 output tokens and the run at about $4.19".

`notes/v2_comparability_failure.md` records that this fit's sigma converged to
exactly 1.0000, suggesting the optimiser hit a flat region, and that it
predicts 0.7489 completion at 6144 against 0.7095 observed. The draft carries
the conclusion and **drops both caveats.**

The conclusion survives without the fit, as the note says, because a 16,384 cap
alone costs $3.84 against $1.16. The draft should make the argument that way
rather than on an extrapolation it does not caveat.

## B1. arXiv:2608.12150's numbers come from a fetch summary, not the paper

**Where:** §5.1, "reversals significant at p < 0.01, with a three-tier
truncation analysis", and the claim that it excludes reasoning-native models.

Read via an automated page summary, never from the PDF. **An automated summary
of arXiv:2606.29490 was materially wrong earlier in this same project**, which
is why that one was read directly. The same standard has not been applied here,
and this paper is load-bearing: §5.1 positions the whole reasoning-wall section
against it.

## B2. Murray and Chiang, and Duan et al., cited from search results

**Where:** §4.4 Signal 2.

Duan et al. (SAR) was verified against its abstract page. **Murray and Chiang
(2018) was not opened**; the length-bias characterisation comes from a search
summary. It is almost certainly right, and it is not verified.

## B3. "Roughly 613 tokens" is from the predecessor's store, not this one

**Where:** §4.4 Signal 2, §1.

The margin-v1 store's mean completion is **602.21**. 613 is the predecessor
figure. The draft uses 613 while describing this paper's own measurement
context. Either number supports the argument; mixing stores without saying so
is the problem.

## B4. §5.5's bill table has a row that does not add up

**Where:** §5.5.

The row "the incomplete second-model run (§6) | 1,253 | remainder" gives no
figure. Ledger: Qwen3.5-9B totals $1.2554 across **1,401** samples, of which
148 are probes and 1,253 are the run. The table double-counts the probes into
the first row and then labels the rest "remainder". Two rows should be
$0.1347 and $1.1207; as written the reader cannot verify $4.667639 from the
table.

## C1. "Odds of roughly 800 million to one" is exp(20.52) presented as odds

exp(20.52) = 8.1e8, so the arithmetic is right. But the margin is a difference
of log-probabilities between **two option letters**, so it is a likelihood
ratio between the top option and the runner-up option, not odds against
everything else. The phrase invites the second reading.

## C2. "12,344 measured, 265 censored" sums to 12,609, not 12,672

63 samples have neither. Those are the unanswered ones (answer rate 0.9950
over 12,672 gives ~63). The draft never reconciles the three counts, and a
reviewer checking the arithmetic will stop here.

## C3. §4.3 keeps the title "Two verifier-free gates" inside a paper about three signals

Deliberate and flagged in the draft, but the section title, the §4.4 title and
the Abstract now use "gate" and "signal" in ways a reader must track carefully.
A reviewer will read "three signals fail" and then find a two-gate results
section.

## C4. "We did not find this result in our search" is in the Abstract

Correct and honest. It is also unusual in an abstract and reviewers may read it
as hedging rather than as precision. Keep, but expect the comment.

---

## Claims that resolve cleanly

Checked and traceable, listed so the absence of a flag is not ambiguous:

| claim | resolves to |
|---|---|
| MD1 20.5232 / bound 18.8376 / PASS, MD2 0.7567 / 0.7105 / PASS | `PREREGISTRATION.md` thresholds + `notes/margin_v1_run.md`; tag `argmax-prereg-margin-desc-v1.0` |
| 64 of 69 problems, 5 excluded | same |
| answer rate 0.9950 [0.9936, 0.9961] vs published 0.9946 | `notes/margin_v1_run.md`, produced by `derive.py` |
| Table 1, all four PH verdicts | v1 PDF, carried unchanged |
| Table 2 per-domain backfire | v1 PDF, carried unchanged |
| Table 3 agreement bins | v1 PDF, carried unchanged |
| 56.6 / 65.7 pooled backfire | v1 PDF |
| oracle 0.482 / 0.439, 14 and 17 points | v1 PDF |
| aggregate curve spans 0.52 points | `notes/thread_a.md` |
| TA1 -0.0213 [-0.0335, -0.0091] PASS; TA2a; TA2b FAIL by 0.0004 | `notes/thread_a.md`, tag `argmax-prereg-threadA-v1.0` |
| resolution floor 0.0161 | `PREREGISTRATION.md` |
| Qwen3.5-9B 0.0000 at 2048 and 4096, mean completion = cap | `configs/pricing/together-2026-08-14.yaml` `cap_finding.arms` |
| 0.5938 at 8192 | same |
| thinking control, 1537.3 vs 1532.8 | same, `thinking_control` |
| QwQ / four refusals | `configs/models/*.capabilities.json`, verbatim provider errors |
| 119.66x, and the k-uplift table | `argmax.analysis.projection`, tested |
| 0.8931 [0.8747, 0.9090], truncation 0.2905 | recomputed from the v2 store this pass |
| probe set 2082.9 / 0.0312 vs 3546.4 / 0.3200, 1.703x | recomputed this pass |
| one `param_hash`, zero reasoning tokens | recomputed this pass |
| ledger 14,073 = 14,073, $4.667639 | recomputed this pass |
| balance $1.16 | dashboard, human-read, 2026-08-14 |
| -0.2614 [-0.3912, -0.1156] | `notes/entropy_signal.md` / doc 2 §7.2.1 |
| U-shape quintiles and p = 0.083 | `notes/completion_length_candidate.md` |
| Kumaran AUROC 0.62-0.80, Cal-LP definition | PDF read directly, pages 1-7 |

## Summary

**One A-severity finding is in the abstract** (A1) and one more is in the
mechanism section (A2). Both are the same failure mode: a sentence describing a
computation that was never run. Neither would be caught by the citation scan,
the pairing scan, or the falsification suite, because all three check
provenance of *stored* numbers and neither number is stored.

**The gap this exposes:** the repository has a test that every registered
`claim_id` resolves to backing rows, and no test that every *number in the
prose* does. A1 is precisely a number in prose with no backing row.
