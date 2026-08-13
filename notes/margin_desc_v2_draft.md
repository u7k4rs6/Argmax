# DRAFT registration: argmax-prereg-margin-desc-v2.0

**Status: DRAFTED, NOT TAGGED. Nothing here is registered.** No rows have been
added to `PREREGISTRATION.md`, no tag exists, and no confirmatory sample has
been drawn against it. See "Why this is not tagged" at the end, which is the
part of this document that matters most.

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
5. **The analysed set may be selected.** If accuracy is near the probe
   signal, most problems will be excluded and the survivors will be the
   problems this model gets wrong, which is not the population MD1 and MD2
   were calibrated on. Doc 2 section 7.2 requires the per-problem
   heterogeneity be published beside any pooled figure, and here it must
   lead: the exclusion count, the surviving n, and the accuracy distribution
   are reported before either bound.
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

## Why this is not tagged

The instruction that authorised this work reserved the spend decision and
directed that the registration be left drafted and untagged. It is being
followed literally.

The stated reason for leaving it untagged was that credits might not stretch
to it. **That reason no longer holds.** The wall came down: the thinking
control works, the cap is found, the run costs $1.77 against $2.55, and the
resolution check passes at M=16. The obstacle now is authorisation, not money
and not statistics.

Tagging a pre-registration is the act that makes it binding, and cutting one
that a human has not approved would make the tag a formality. Under CLAUDE.md
a tag matching `argmax-prereg-*` can never be moved or deleted, so a
prematurely cut tag is permanent. Nothing here is registered until a human
says so.

Everything above is decided and written down before any confirmatory sample
exists, which is the property that makes it a pre-registration when it is
eventually cut. If it is tagged unchanged, it is a pre-registration. If any
threshold, exclusion rule, or M changes first, this draft is superseded and
the change is recorded here rather than edited away.
