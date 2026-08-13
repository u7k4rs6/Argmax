# Registration: argmax-prereg-margin-desc-v2.0

**Status: REGISTERED and TAGGED.** Rows are in `PREREGISTRATION.md`; the tag
was cut before any confirmatory sample was drawn. This file was drafted
untagged first, and the section "Why this was held, and what released it"
records that history rather than deleting it.

Second-model replication of the descriptive margin claims registered as
`argmax-prereg-margin-desc-v1.0` and reported in `notes/margin_v1_run.md`.

## Model, cap, and why

**Model:** `Qwen/Qwen3.5-9B`, **with the thinking phase disabled** via
`chat_template_kwargs {"enable_thinking": false}`.

The control is part of the request identity and enters `param_hash`. The model
card's spelling is used rather than Together's `reasoning {"enabled": false}`
because it names what actually changes, the chat template, which is what a
replicator needs; the two were probed side by side and are indistinguishable
(`notes/reasoning_wall.md`).

**Cap: 6144.** Chosen by the rule in doc 2 section 7.1 as amended, which keys
comparability on answer rates rather than on caps. Probed answer rates on 8
already-burned problems:

| configuration | n | answer rate | truncation |
|---|---|---|---|
| cap 2048, thinking on | 20 | 0.0000 | 1.0000 |
| cap 4096, thinking on | 32 | 0.0000 | 1.0000 |
| cap 8192, thinking on | 32 | 0.5938 | 0.4375 |
| cap 2048, thinking off | 16 | 0.8125 | 0.3125 |
| **cap 6144, thinking off** | 32 | **1.0000** | **0.0000** |

Reference: **Qwen2.5-7B-Instruct-Turbo at cap 2048 answers 0.9950** over
12,672 samples. 6144 is the smallest probed cap reaching it. 4096 was not
probed with thinking off because the censored lognormal fit over the 2048 arm
(median 1592 tokens, sigma 0.4128) puts its completion rate at 0.9890, below
the target.

**M = 16**, at $0.000557 per sample, so 198 x 16 = **$1.77** against $2.55
remaining.

## The claims

Both are keyed on **incorrect** samples rather than on samples dissenting from
the problem's plurality. At M=16 the plurality is estimated from 16 draws over
four options, so "dissenting" carries estimation noise that the answer key
does not. The correctness key measures the same mechanism, a sample committing
hard to an answer that is wrong, without inheriting that noise.

Per-problem unit throughout, matching MD1 and MD2. A problem enters the
analysis when it carries **at least three incorrect samples with a measured
(non-censored) margin**; otherwise it is excluded and the exclusion is
counted, never imputed.

| id | claim | statistic | threshold | deciding fields |
|---|---|---|---|---|
| **MD3** | The mean over problems of the per-problem median margin among incorrect samples exceeds 15 nats | one-sided 95 percent lower bound, cluster bootstrap over problems | **15.0** | `answer_margin`, `answer_margin_censored`, `is_correct`, `problem_id` |
| **MD4** | The mean over problems of the per-problem fraction of incorrect samples above 10 nats exceeds 0.60 | one-sided 95 percent lower bound, cluster bootstrap over problems | **0.60** | `answer_margin`, `answer_margin_censored`, `is_correct`, `problem_id` |

### Calibration, so each threshold is a prediction and not a description

From the v1 **exposed** set only (129 problems, 124 usable), never from the
69-problem holdout:

| quantity | Qwen2.5-7B exposed estimate | threshold | headroom |
|---|---|---|---|
| median margin, incorrect | **21.5365** | 15.0 | 6.54 nats |
| fraction above 10 nats, incorrect | **0.7617** | 0.60 | 0.16 |

Thresholds sit below the exposed estimates, so each claim is falsifiable by a
second model that commits less hard than the first. They are the same numbers
MD1 and MD2 used, which keeps the two registrations on one scale.

Note these are **per-problem** statistics. The sample-level figures over the
same set are median 23.25 and fraction 0.7546; MD1 and MD2 are defined on the
per-problem unit, so the thresholds are set against the per-problem means.

## Resolution check at M=16

Run on the v1 exposed set subsampled to 16 of 64 samples per problem, seed
20260814, which reproduces the within-problem estimation noise M=16 will
actually carry. At M=16, 13 of 129 problems fall below the exclusion floor
against 5 at M=64.

| n usable | MD3 lower bound | vs 15.0 | MD4 lower bound | vs 0.60 |
|---|---|---|---|---|
| 198 | 20.7692 | RESOLVES | 0.7427 | RESOLVES |
| 178 | 20.7155 | RESOLVES | 0.7412 | RESOLVES |
| 120 | 20.4899 | RESOLVES | 0.7347 | RESOLVES |
| 80 | 20.2066 | RESOLVES | 0.7266 | RESOLVES |
| 42 | 19.6197 | RESOLVES | 0.7099 | RESOLVES |
| 20 | 18.6626 | RESOLVES | 0.6825 | RESOLVES |

**Both resolve at every plausible surviving n, down to 20 problems.** The
resolution check passes.

The row range is not decoration. Qwen3.5-9B's probe accuracy was 29 of 32,
and at accuracy 0.90 roughly 156 of 198 problems would carry fewer than three
incorrect samples at M=16, leaving about 42. The claims still resolve there,
but see the limitations.

## Stratification check: does the margin depend on how hard the problem is?

Run before tagging, on the v1 exposed 129 at M=64, because the survivor set
under M=16 is selected on accuracy and a threshold calibrated on the whole
range is only valid for a selected subset if the statistic does not vary
across it.

| accuracy bin | problems | usable | median margin | sd | fraction above 10 | sd | mean incorrect per problem |
|---|---|---|---|---|---|---|---|
| 0.000 to 0.125 | 42 | 42 | 20.2467 | 8.40 | 0.7318 | 0.219 | 60.8 |
| 0.125 to 0.250 | 19 | 19 | 23.5325 | 7.31 | 0.7928 | 0.179 | 53.3 |
| 0.250 to 0.500 | 30 | 30 | 23.3041 | 6.75 | 0.7899 | 0.177 | 41.3 |
| 0.500 to 0.750 | 15 | 15 | 18.9663 | 9.88 | 0.6610 | 0.293 | 22.8 |
| 0.750 to 1.000 | 23 | 18 | 21.6352 | 7.93 | 0.8359 | 0.228 | 11.4 |
| **all** | **129** | **124** | **21.5365** | 8.04 | **0.7617** | 0.218 | |

**Flat.** No monotone trend, and both correlations against per-problem
accuracy cross zero on a 4,000-resample bootstrap over problems:

| | correlation | 95 percent interval |
|---|---|---|
| accuracy against median margin | **-0.0094** | [-0.1927, +0.1817] |
| accuracy against fraction above 10 | **+0.0544** | [-0.1402, +0.2527] |

Every bin sits above both thresholds. The lowest bin mean is 18.97 nats
against a 15.0 threshold and 0.661 against 0.60, and it is the bin with the
widest sd and fewest problems.

Recalibrating on the band the survivors will occupy changes nothing worth
changing. The M=16 floor of three incorrect samples admits problems at
accuracy at or below 13 of 16, so:

| calibration set | n | median margin | fraction above 10 |
|---|---|---|---|
| all 124 usable | 124 | 21.537 | 0.7617 |
| **accuracy at or below 0.8125** | 116 | **21.582** | **0.7577** |
| accuracy at or below 0.50 | 91 | 21.941 | 0.7637 |

The survivor band reproduces the full set to within 0.05 nats and 0.004.
**The thresholds are therefore unchanged at 15.0 and 0.60**, and they are
unchanged because the check said so, not because they were convenient.

**Registered sensitivity.** One bin would not carry MD4 on its own: restricted
to problems at accuracy 0.500 to 0.750, the fraction is 0.6610 with sd 0.293,
and at a projected n=42 the bound is 0.5867, below 0.60. MD3 survives that bin
at 16.46. This is registered rather than reported afterwards, because it is
the one way MD4 could fail without the underlying claim being wrong: if the
survivors concentrate in that band, a FAIL is evidence about which problems
survived, not about how hard samples commit. The reported verdict carries the
survivors' accuracy distribution beside it either way.

## Registered limitations

Stated here so they are registered rather than discovered in the writeup.

1. **This is not a reasoning-native replication.** The model is
   reasoning-native and the thinking phase is switched off to make it
   measurable at all. What is tested is a second non-reasoning model.
   `notes/reasoning_wall.md` records why no reasoning-native replication is
   purchasable on this account.
2. **Same family, one generation and one size apart.** Qwen2.5-7B to
   Qwen3.5-9B is not a cross-family replication. Every non-Qwen candidate in
   the 7 to 9B range refused serverless requests. A shared result may be a
   property of the family, or of a shared tokenizer or answer format, rather
   than of models in general.
3. **Caps differ: 2048 against 6144.** Deliberate, and required by doc 2
   section 7.1, which keys comparability on answer rate (0.9950 against
   1.0000) rather than on cap. Recorded because a reader comparing the two
   runs will see the difference first.
4. **MD1 and MD2 are not replicated and are not testable here.** They are
   keyed on dissent from the plurality, and M=16 is a quarter of the M=64 the
   plurality-keyed claims were calibrated at. MD3 and MD4 measure the same
   mechanism through the answer key instead. No plurality-keyed verdict may
   be reported from this run.
5. **The surviving problem set is selected on accuracy.** The three-incorrect
   floor admits only problems at accuracy at or below 13 of 16, and if this
   model's accuracy is near the probe signal most problems are excluded. The
   stratification check above says the statistic does not vary across that
   selection, which is why the thresholds stand; that result is cited whether
   the claims pass or fail, and it is what makes a PASS on a selected subset
   interpretable. Doc 2 section 7.2 requires per-problem heterogeneity be
   published beside any pooled figure, and here it leads: the exclusion count,
   the surviving n, and the survivors' accuracy distribution against v1's are
   reported before either bound.
6. **The margin depends on a fix younger than the claims.** Qwen3.5-9B
   returns the OpenAI-nested logprob shape and `derive_row` read only the
   parallel-array shape, so before the fix every margin on this model was
   null with no error raised. Verified additive against all 12,672 v1 rows.

## Sampling plan

198 GPQA Diamond problems, M=16, cap 6144, thinking disabled, depth-5
logprobs, temperature and top_p from the model config, explicit spend ceiling
set before the run. Projected $1.77. The 69-problem holdout is analysed once
and only once, exactly as under v1; the 8 probe problems are already burned
for both models and are exploratory.

## Why this was held, and what released it

This file existed as an untagged draft first. That is recorded rather than
tidied away, because the gap between drafting and tagging is where a
pre-registration either is one or is not.

It was held because the instruction that authorised the work reserved the
spend decision, and because a tag matching `argmax-prereg-*` can never be
moved or deleted under CLAUDE.md, so a prematurely cut tag is permanent. The
originally stated reason, that credits might not stretch, had already stopped
applying: the thinking control works, the cap is found, and the run costs
$1.77 against $2.55.

It was released by an explicit instruction to tag, after the stratification
check it also required came back flat. The thresholds are the ones the draft
carried, 15.0 and 0.60, unchanged because the check supported them.

Everything above was decided and written down before any confirmatory sample
existed, which is the property that makes it a pre-registration rather than a
description. If any threshold, exclusion rule, or M is changed after this
point, the change is recorded here and a new version is cut. This one is not
edited.
