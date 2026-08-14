# margin-v2 does not meet its registered comparability condition

**MD3 and MD4 remain registered under `argmax-prereg-margin-desc-v2.0` and are
NOT evaluated.** They are not withdrawn, not falsified, and not tested. The
store that exists cannot decide them, and this note records why so that the
tag reads as unevaluated rather than as forgotten.

## What was registered

Cap 6144 was chosen under doc 2 section 7.1, which keys comparability on
answer rate rather than on matched caps. The registered reference is
`md_v2_answer_rate_reference = 0.9950`, the v1 answer rate over 12,672
samples. A 32-sample probe at cap 6144 measured answer rate **1.0000** with
truncation **0.0000**, and that measurement is what licensed the cap.

## What the run actually produced

1,253 of 3,168 samples, 79 of 198 problems, before the sampler was terminated:

| | probe, n=32 | run, n=1253 |
|---|---|---|
| answer rate | 1.0000 | **0.8931** [0.8747, 0.9090] |
| truncation | 0.0000 | **0.2905** |
| mean completion | 2055.1 | **3396.9**, +65.3 percent |

**0.8931 against a registered 0.9950 is not a near miss.** Roughly one sample
in nine returns no extractable answer, and 29 percent hit the ceiling.

## Config drift ruled out before the selection story was accepted

The obvious alternative was that the thinking control lapsed. It did not:

| check | result |
|---|---|
| distinct `param_hash` across all 1,253 samples | **1**, and it is `89bdcf2e54986835b4448654...`, the thinking-off config computed before launch |
| `usage.reasoning_tokens` nonzero | **0 samples**, across both run ids |
| `max_tokens` | 6144 on every sample |
| reasoning or reasoning_content field returned | 0 samples |

(`split_ok` reads true on all 1,253, which looks alarming and is not: the
sampler sets it alongside `split_method: none`, meaning no split was
attempted rather than that one succeeded.)

The request was byte-identical throughout. **The instrument was not
misconfigured. The probe measured what it measured, correctly, on the wrong
problems.**

## The cause, measured directly

The sampler iterates problem-major, so the run re-sampled the probe's own 8
problems first, at M=16, under the confirmatory config. That gives a direct
comparison the probe could not give itself:

| problems, in iteration order | n | mean completion | truncation |
|---|---|---|---|
| **0 to 7, the probe set** | 128 | **2082.9** | **0.0312** |
| 8 to 15 | 128 | 2938.5 | 0.2422 |
| 16 to 39 | 384 | 3922.1 | 0.3750 |
| 40 to 78 | 613 | 3438.0 | 0.3018 |
| **probe set** | 128 | **2082.9** | 0.0312 |
| **everything else** | 1125 | **3546.4** | 0.3200 |

The probe set reproduces the probe almost exactly, 2082.9 against 2055.1 and
truncation near zero. **Every other band is longer, and the rest of the
benchmark runs 1.703 times the probe set's mean completion.**

So the probe was not noisy and was not unlucky. It was **precise about an
unrepresentative slice.** The 8 lowest-id GPQA Diamond problems are
substantially shorter than the benchmark, and nothing in a within-probe
statistic could have revealed that.

### Why the calibration did not catch it

Doc 2 section 5.3.1 puts the 95 percent uplift at k=8 at 22.7 percent, from
resampling the 198 v1 per-problem means, with a fifth percentile of -18.53
percent. The observed error is **-65.3 percent on mean completion**, far
outside that interval.

That is not a failure of the calibration. It is the calibration being applied
to the wrong thing. **The uplift table describes a random draw of k problems.
A fixed lowest-id slice is not a random draw, and its error is not
resampleable even in principle**, because there is only one such slice and it
is the same one every time. The same section already records the fix, that
probe problems are drawn at random with a recorded seed. This run is the
evidence for it, arriving one run too late.

## Why MD3 and MD4 are not evaluated on this store

Not because 1,253 of 3,168 samples is too few. Because of **what** is missing.

At 29 percent truncation the pool that would be scored is **selected for
finishing fastest**. Samples that would have taken longer are absent, and
they are absent non-randomly: they are the ones on the harder or more
discursive problems, which are precisely the ones a claim about margins among
incorrect samples is about. Scoring the survivors would produce a number about
the subset of samples that fit inside 6144 tokens and would report it as a
number about the model.

That is the exact confound doc 2 section 7.1 and doc 4 section 4.1 exist to
prevent. Section 7.1 says comparability is keyed on answer rate because
matching caps across models with different length distributions compares two
different output populations wearing one name. Section 4.1 requires the answer
rate beside every accuracy for the same reason. **Evaluating MD3 and MD4 here
would violate both rules in the same paper that argues for them.**

There is no rescue available at this store either. Scoring unanswered samples
as incorrect does not help, because the claims are defined over incorrect
samples and an unanswered sample has no margin to contribute. Restricting to
problems with low truncation reintroduces the selection at the problem level.

## The money, which removes the choice anyway

| | |
|---|---|
| realized to date, all phases | **$4.6676** |
| v2 cost per sample, measured | $0.000894 |
| remaining 1,915 samples at that rate | **$1.71** |
| implied balance, from the $2.55 stated remaining at v1 completion | **$1.29** |
| implied balance, on the most generous reconstruction | $1.43 |

**Short by $0.28 to $0.42.** And that understates it: the 119 unsampled
problems are the ones the run had not reached, the sampled bands trend longer
with position, and the $0.000894 average is held down by the cheap probe-set
problems at the front. The true remaining cost is above $1.71.

These balances are reconstructed from the ledger and the last stated credit
figure, not queried from the provider. The conclusion does not turn on the
reconstruction: both are short, and finishing at a cap that fails
comparability would buy a number this project could not report.

## What this costs, stated plainly

**The rule cost its authors a registered replication.**

The second-model replication of the margin claims is not happening on this
budget. MD3 and MD4 were registered before sampling, thresholds were held
after a stratification check, the tag was cut with no confirmatory sample in
existence, and the discipline was followed exactly. It was followed right up
to the point where it said the data could not be used, and then it was
followed there too.

The alternative was available and it was cheap: score the 79 problems, report
MD3 and MD4 with a footnote about truncation, and let a reader who does not
check the answer rate take the numbers at face value. Doc 4 section 9.1 exists
because that footnote is exactly what gets dropped.

## What survives

| | |
|---|---|
| MD1 and MD2, v1 | **unaffected**. Registered, held-out, passed, one model |
| the commitment result | stands on v1 alone, one model, and the draft says so |
| MD3 and MD4 | **registered and unevaluated**, cause recorded here |
| the 1,253 samples | kept. Raw is append-only, and they are the evidence for everything above |
| the reasoning wall | strengthened. This is a fourth measured wall, and the most expensive |
| the 69-problem holdout | untouched on both models |

The v2 store is not waste. It is the measurement that shows a cap chosen from
8 non-random problems fails on 198, which is a result about probe design that
no successful run would have produced. It belongs in the reasoning-wall
section, not in a replication section.

## Do not

- Do not evaluate MD3 or MD4 on this store.
- Do not re-register the same claims at a larger cap as if v2.0 had not
  happened. If a future budget allows it, that is v3.0 and it cites this note
  for why v2.0 was not evaluated.
- Do not move or delete `argmax-prereg-margin-desc-v2.0`. It is a correct
  record of a claim that was properly registered and could not be tested.
