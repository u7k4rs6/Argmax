# Did the entropy gate fail because confidence is uninformative, or because the instrument was?

The published study gated on mean token entropy and moved accuracy by less than
0.002. Two explanations fit: confidence genuinely does not track correctness,
or the signal had no variance to threshold on. The paper assumed the first.
This tests the second.

Read-only against the predecessor's confirmatory stores. No API calls, nothing
written outside this file.

## Provenance

| What | Value |
|---|---|
| Source repo | `github.com/u7k4rs6/self-consistency-backfire` |
| Read at commit | `a7f168e685b2eecf4793e2b635a6c801b6192d91` |
| Stores | `outputs/samples/`, `outputs/samples_model2/`, `outputs/entropy_baseline/` |
| Date | 2026-08-13 |

**Coverage first, because it bounds everything below.** `mean_token_entropy` is
present on 9,589 of 13,058 Qwen samples (73.4 percent) and 9,664 of 12,672
Llama samples (76.3 percent), covering **151 of 198 problems** for each model.

Those 151 are not an arbitrary subset. **They are the paper's pre-registered
confirmatory split**, and the problems without entropy are the 47 exploratory
ones, plus 3 that Qwen sampled and the study set aside. Section 0 characterises
the gap; the published paper discloses it in two places and evaluates its
entropy gate on the same 151 this note uses. So the population here is the
right one, and it is not the population the headline backfire rate is quoted
on.

**What the stored field actually is.** The mean negative logprob of the tokens
that were sampled, averaged over the whole completion. It is a surprisal of the
realised path, not an entropy of a distribution, and the naming has misled at
least one reader of this data. Section 3 turns on the difference.

---

## 0. What exists, exactly, and what does not

An earlier version of this note said per-token arrays were never stored and
then quoted a median token surprisal, which cannot both be true. Resolving it:
**the arrays are not there, and the median is a stored summary of them.**

`outputs/entropy_baseline/`, verbatim structure of one file, all 47 identical
in shape:

| Field | Type | Example |
|---|---|---|
| `problem_id`, `subject`, `model`, `schema_version`, `timestamp` | str | |
| `temperature` | float | 0.7 |
| `n_tokens`, `input_tokens`, `output_tokens` | int | 336 |
| `full_response` | str | the completion |
| `mean_per_token_nll` | float | 0.3631963021081371 |
| `median_per_token_nll` | float | 0.0035171509 |
| `max_per_token_nll` | float | 5.5 |
| `mean_per_token_entropy` | float | 0.30941057361870883 |
| `median_per_token_entropy` | float | 0.024767642715901567 |
| `max_per_token_entropy` | float | 1.4391867481671252 |
| `top_logprobs_available` | bool | true |

- **47 problems, one sample each.** Not 64, not a matrix.
- **Every field is a scalar.** A scan across all 47 files finds no list-valued
  or dict-valued field anywhere. The six statistics were computed at sampling
  time from per-token data that was then discarded.
- **`top_logprobs_available` is a boolean, not a payload.** It records that the
  API returned alternatives during that run, which is corroborating evidence
  for the capability probe's depth-5 finding on the same model family. It does
  not contain them.
- **The depth k is not recorded anywhere**, in any of the 47 files or in the
  summary. That a true per-token entropy was computable means k was at least 2
  at sampling time, and how much more than 2 is unknown.

**Therefore the two follow-on questions cannot be answered from this data.**
Localised entropy at the answer span is not computable, which is what phase 14a
said and what the published paper repeats as a stated limitation. The
answer-token margin is not computable for the same reason. No pilot of the v2's
gate is available at zero dollars, from this store or any other in the
repository.

**Effect on the case for the v2: untouched.** No new evidence in either
direction. The gate remains untested by anyone, and the only way to test it is
to collect the arrays.

### Characterising the missing quarter

The gap is not random, not length-related and not failure-related. It is a run
boundary that coincides exactly with the study's own experimental split:

| | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| samples without entropy | 3,469 of 13,058 | 3,008 of 12,672 |
| schema of the missing | `v6.0-pilot` | `v6.0-pilot-model2` |
| schema of the present | `v6.0-pilot-phase13` | `v6.0-pilot-model2-phase13` |
| when the missing were sampled | 2026-05-19 to 05-24 | 2026-06-05, 11:30 to 11:47 |
| when the present were sampled | 2026-06-05, 17:24 to 17:56 | 2026-06-05, 17:59 to 18:24 |
| problems entirely missing | **50** | **47** |
| problems entirely present | 148 | 151 |
| problems mixed | 3 | 0 |

The missing set is the **exploratory split**: the 47 problems the hypotheses
were generated from, plus the 3 Qwen sampled and the study set aside, matching
the 50 ids in `data/problem_ids.json`. The `entropy_baseline` 47 are a strict
subset of them, and the 151 with entropy have **zero overlap** with the
`entropy_baseline` set.

Two correlates worth stating, both consequences of which problems are in which
split rather than causes of the missingness:

| | Qwen: missing / present | Llama: missing / present |
|---|---|---|
| accuracy | 0.4082 / 0.3162 | 0.3331 / 0.2482 |
| extraction failure | 0.0173 / 0.0010 | 0.0189 / 0.0125 |
| at the 2048 cap | 0.0032 / 0.0010 | 0.0017 / 0.0034 |
| input tokens, mean | 358.8 / 273.0 | 343.9 / 250.2 |

**The exploratory problems are about nine points easier** for both models. That
is a property of the split, and it means any statistic computed on the
confirmatory 151, including everything in this note, describes a harder
population than the exploratory 47 do.

### Does the published paper mention the gap?

**Yes, twice, and it draws the right conclusion from it.** Section 2:
"Logprobs are available for all 151 confirmatory problems but not for the 47
older exploratory ones, so the entropy gate is evaluated on the confirmatory
set." Section 4: "logprobs were stored only for the 151 confirmatory problems
... Localized entropy (computed over final-answer tokens only) was not
computable from stored data, which retained only the mean scalar; this is a
limitation of the pipeline rather than a finding."

It also warns that the entropy-gate and agreement-gate capture percentages are
computed on different problem sets and "should not be read as like-for-like".
Nothing here is a gap the paper concealed.

---

## 1. The signal does vary. That is not the problem.

**Per sample:**

| | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| n | 9,589 | 9,664 |
| mean | 0.2543 | 0.2212 |
| sd | 0.1058 | 0.0694 |
| variance | 0.01119 | 0.00481 |
| min | 0.0158 | 0.0163 |
| p5 | 0.0954 | 0.1157 |
| p25 | 0.1685 | 0.1740 |
| median | 0.2496 | 0.2165 |
| p75 | 0.3306 | 0.2631 |
| p95 | 0.4325 | 0.3420 |
| max | 0.7560 | 0.9674 |
| **IQR** | **0.1621** | **0.0890** |
| **p5 to p95 span** | **0.3372** | **0.2264** |

**Per problem**, averaging each problem's samples, which is the level a gate
would threshold at:

| | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| n problems | 151 | 151 |
| mean | 0.2545 | 0.2212 |
| sd | 0.0889 | 0.0435 |
| variance | 0.00790 | 0.00190 |
| min | 0.0739 | 0.1129 |
| p5 | 0.1150 | 0.1469 |
| p25 | 0.1851 | 0.1912 |
| median | 0.2586 | 0.2222 |
| p75 | 0.3247 | 0.2464 |
| p95 | 0.3850 | 0.2893 |
| max | 0.4606 | 0.3521 |
| **IQR** | **0.1396** | **0.0552** |
| **p5 to p95 span** | **0.2700** | **0.1424** |

**Does a threshold placed anywhere in that range separate a meaningful number
of problems? Yes.** The interquartile range spans 0.14 nats on Qwen and 0.055
on Llama, and a cut at any quartile separates 38 problems from 113 by
construction. Nothing about the spread is degenerate. On Llama the range is
about a quarter as wide as on Qwen, which is worth noting but does not change
the answer.

**So the second explanation, taken literally, is false.** The signal had
variance to threshold on. The failure is not that every problem looked alike to
the instrument. Section 2 is where it goes wrong.

For interpretation: the implied mean per-token probability, `exp(-x)`, runs
from 0.909 at p5 to 0.649 at p95 for Qwen. The instrument is reporting that
some completions are made of much likelier tokens than others, and it is right
about that.

---

## 2. The variance does not track the thing a gate needs

Per problem, the stored entropy against the observed diversity of the 64
sampled answers:

| Relationship | Qwen2.5-7B | Llama-3-8B-Lite |
|---|---|---|
| Pearson, entropy vs plurality agreement | **+0.031** | **-0.028** |
| Spearman, entropy vs plurality agreement | +0.051 | -0.012 |
| Pearson, entropy vs answer-distribution entropy | -0.016 | +0.069 |
| Spearman, entropy vs answer-distribution entropy | -0.068 | +0.038 |
| Pearson, entropy vs accuracy | -0.122 | -0.008 |

Every one of these is indistinguishable from zero on 151 problems, and the
signs disagree between the two models.

**The quartile comparison is the cleanest form of it.** Take the 38 problems
where the instrument is most confident and the 38 where it is least:

| | Qwen: mean plurality agreement | Llama: mean plurality agreement |
|---|---|---|
| lowest entropy quartile | 0.6139 | 0.5700 |
| highest entropy quartile | 0.6149 | 0.5458 |

On Qwen the two groups differ by **0.001**. The instrument says one set of
problems is far more certain than the other; the samples say the two sets are
equally diverse. **22 of the 38 lowest-entropy Qwen problems have plurality
agreement below 0.60**, and 24 of 38 on Llama.

The deciles say the same thing without a threshold. Qwen, ordered by entropy:

| decile | mean entropy | mean agreement | plurality correct |
|---|---|---|---|
| 1 | 0.111 | 0.643 | 0.600 |
| 2 | 0.150 | 0.586 | 0.400 |
| 3 | 0.183 | 0.591 | 0.400 |
| 4 | 0.206 | 0.680 | 0.133 |
| 5 | 0.240 | 0.632 | 0.400 |
| 6 | 0.274 | 0.592 | 0.133 |
| 7 | 0.299 | 0.623 | 0.267 |
| 8 | 0.324 | 0.676 | 0.400 |
| 9 | 0.355 | 0.580 | 0.333 |
| 10 | 0.395 | 0.660 | 0.250 |

Agreement is flat across a fourfold change in entropy.

**The best threshold, and why it is not a gate.** Sweeping every candidate cut
and keeping the largest separation in whether the plurality answer is correct:

| | threshold | n below | n above | correct below | correct above | gap |
|---|---|---|---|---|---|---|
| Qwen | 0.1334 | 17 | 134 | 0.647 [0.413, 0.827] | 0.291 [0.221, 0.373] | **+0.356** |
| Llama | 0.1399 | 6 | 145 | 0.000 [0.000, 0.390] | 0.317 [0.247, 0.397] | **-0.317** |

Qwen's gap looks large and its intervals do not overlap. It is also the maximum
over roughly 150 candidate thresholds on 151 problems, selected after seeing
the outcome, resting on 17 problems. **And the sign flips on the second
model**: the same procedure says low entropy predicts being right on Qwen and
being wrong on Llama. A signal whose direction depends on the model is not a
signal. This is consistent with the predecessor's own phase 14a re-analysis,
which measured ROC-AUC 0.63 for entropy predicting backfire and a best ceiling
capture of 0.0054.

---

## 3. What this implies for the v2's margin gate

### The mechanism, which is the part that transfers

`outputs/entropy_baseline/` holds 47 problems sampled with `top_logprobs`
requested, storing **summary statistics** of the sampled-path surprisal and of
a true per-token entropy computed from the alternatives. The arrays are gone,
per section 0, but the summaries are enough to show why a whole-completion
average cannot work:

| Quantity, mean over 47 responses | Value | Stored as |
|---|---|---|
| mean per-token NLL, whole completion | 0.2618 | `mean_per_token_nll` |
| **median per-token NLL, within a response** | **0.0081** | `median_per_token_nll` |
| median of those per-response medians | **0.00038** | derived from the above |
| mean per-token true entropy from `top_logprobs` | 0.2372 | `mean_per_token_entropy` |
| tokens per completion, mean | 612.7 | `n_tokens` |

Every figure here is a scalar the pipeline wrote at sampling time. None of it
required the arrays, and none of it can substitute for them.

The median token in a response carries a surprisal of **0.0004 nats**, which is
a probability of 0.9996. The mean is 0.26. The distribution over tokens is
extreme: several hundred tokens of near-deterministic prose, and a handful that
carry all the uncertainty. Averaging over 613 tokens measures fluency, and the
answer token is one of the 613.

**That is a finding about the instrument, and it is the one that explains the
0.002.** The gate did not fail because confidence is uninformative. It failed
because the quantity being thresholded was a 613-token average in which the
answer contributes about a sixth of one percent of the weight. The paper's
interpretation, that agreement measures concentration rather than correctness,
may also be true; this data cannot separate the two, because the instrument
never localised the measurement enough to test it.

### The margin gate is not the same instrument, and the difference is the point

| | entropy gate, as built | margin gate, as specified |
|---|---|---|
| position | every token in the completion | the answer span only, via `answer_span_tokens` |
| quantity | surprisal of the token that was sampled | gap between the top option and the runner-up |
| depth needed | 1 | at least 2, measured at 5 |
| dilution by prose | total, 613 tokens | none, one span |

The failure documented above is an aggregation failure, and a span-localised
measurement does not inherit it. This is exactly why doc 4 section 3.6 makes
`answer_span_tokens` required and calls it the field that makes final-answer
margin analysis possible at all.

**So: the finding is a warning about aggregation, not about logprobs.** Flagged
as an instrument finding, and specifically not flagged as a reason to abandon
the margin gate.

### One reassurance and one caution, neither conclusive

**Reassurance.** On the 47 baseline problems, the sampled-path NLL (0.2618) and
the top-k entropy (0.2372) agree to within 10 percent. If the returned logprobs
described a different distribution from the one the tokens were drawn from,
those two would not track each other. The remaining 10 percent gap is in the
direction a truncated top-k entropy would produce, since summing only k
alternatives omits tail mass and understates entropy. Read as: the logprobs
appear to describe the distribution the sampling actually used, at the token
level, which is the precondition the margin gate needs.

**Caution.** That is 47 problems at one sample each, and it says nothing about
the answer position specifically. Phase 14a's own note is the honest summary:
per-token arrays were never stored, so localised entropy "is not computable
from stored data". **Whether a localised signal separates confidently-correct
from confidently-wrong is untested, by anyone, on this data.** The v2 is the
experiment that would test it, which is an argument for running it rather than
against.

### What would change the verdict

If the dynamic-range check (blocked on GPQA access) shows answer-token margins
saturated at every problem, the margin gate has no variance to threshold on and
the failure mode this note rules out for the entropy gate would apply to the
margin gate instead. That check is about **variance at the answer position**,
which is precisely the quantity this data does not contain. Nothing here
substitutes for it.
