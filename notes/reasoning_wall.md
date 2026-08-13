# Reasoning-native self-consistency is not measurable on serverless inference at these budgets

A result, not a limitation. Three reasoning-native models were approached in
this project and each stopped the measurement at a different point. All three
walls are measured rather than assumed, and the cost of establishing them is
recorded below, because the useful part of a negative result is what it cost
to reach.

The claim is narrow and it is the claim the evidence supports: **on serverless
hosted inference, at the budgets a small study can spend, self-consistency
over a reasoning-native model cannot be measured on the same footing as
self-consistency over a non-reasoning model.** Not that reasoning models
resist self-consistency, which is a different question this project has not
asked.

## Three models, three walls

| model | wall | measured as |
|---|---|---|
| **QwQ-32B** | never reachable | `model_not_available` on a real request; serverless listing gone, dedicated endpoint required |
| **MiniMax-M2.7** | answers, but not at a comparable cap | answer rate **0.6460** at 16,384; **0.2649** at the published 2048 |
| **Qwen3.5-9B** | emits nothing at any affordable cap | answer rate **0.0000** at 2048 and at 4096, **0.5938** at 8192 |

The non-reasoning reference sits beside them: **Qwen2.5-7B-Instruct-Turbo at
cap 2048 answers 0.9950**, over 12,672 samples. That is the number every row
above is failing to reach.

### QwQ-32B: unreachable

Four of five priced candidates in this scale range refused serverless
requests with `model_not_available`, QwQ-32B among the models with no
serverless route at all. A listed price is not an availability record, which
is now doc 3 section 3.4 and is the reason this is a measured row rather than
an assumed one.

### MiniMax-M2.7: answers, but never at the published cap

From the predecessor's 404 stored records. Answer rate 0.6460 at cap 16,384,
and the censored fit puts it near 0.2649 at the 2048 the published
confirmatory runs used. Doc 2 section 7.1 as amended keys comparability on
answer rate rather than on cap, and this is the model that forced the
amendment: matching the cap here would compare a population where two thirds
of samples answer against one where a quarter do, which is a comparison
between two different sets of problems wearing the same name.

### Qwen3.5-9B: the cap is consumed entirely by hidden reasoning

The sharpest of the three, because the failure is total and the mechanism is
visible in one column.

| cap | n | answer rate | truncation | mean completion | visible chars | $/sample |
|---|---|---|---|---|---|---|
| 2048 | 20 | 0.0000 | 1.0000 | **2048.0** | 0 | 0.000542 |
| 4096 | 32 | 0.0000 | 1.0000 | **4096.0** | 37.5 | 0.001067 |
| 8192 | 32 | 0.5938 | 0.4375 | 7108.9 | 1821.7 | 0.001820 |

**Mean completion equals the cap exactly at 2048 and at 4096.** Not
approximately: every one of those 52 samples ran to the ceiling. The model
spends the whole budget inside the thinking phase and the visible channel gets
38 characters at 4096, which is reasoning spilling past the boundary rather
than an answer. At 8192 it starts finishing, and 0.5938 is still 40 points
below the reference.

The model card explains the numbers rather than excusing them: it recommends
32,768 output tokens for general queries and 81,920 for competition-difficulty
problems. The 2048 the published study used is a sixteenth of the model's own
lower recommendation. This is not a model failing at a reasonable cap, it is a
cap that was never reasonable for this class of model, and the predecessor's
design fixed that cap before this class of model was the default.

## The wall has a door, and it changes what the study is

Together honours a thinking control on this model. Established by real request
rather than inferred, in keeping with doc 3 section 3.4:

| control | source | n | answer rate | truncation | mean completion |
|---|---|---|---|---|---|
| `chat_template_kwargs {"enable_thinking": false}` | model card | 16 | 0.8125 | 0.3125 | 1537.3 |
| `reasoning {"enabled": false}` | Together chat-completions reference | 16 | 0.8750 | 0.3125 | 1532.8 |

Both are honoured, neither errors, and they are indistinguishable in effect:
mean completion 1537.3 against 1532.8, identical truncation, no `reasoning`
field on any response either way. Together almost certainly maps its own
parameter onto the model card's chat template kwarg. The model card also
records that Qwen3.5 dropped the `/think` and `/nothink` prompt switches, so
these two are the whole set of levers.

With thinking off, the length distribution becomes ordinary and the censored
fit over the 32 samples at 2048 gives a lognormal with median 1592 tokens and
sigma 0.4128, predicting 0.9890 completion at 4096 and 0.9995 at 6144. Probed
at 6144:

| | n | answer rate | truncation | mean completion | max completion | $/sample |
|---|---|---|---|---|---|---|
| **cap 6144, thinking off** | 32 | **1.0000** | **0.0000** | 2055.1 | 6077 | 0.000557 |

Answer rate 1.0000 against the reference 0.9950, zero truncation, and 198 x 16
projects to **$1.77 against $2.55 remaining**. 4096 was not probed because the
fit puts it at 0.9890, below the target, and the saving would have been a few
cents against a budget that had stopped binding.

**But a reasoning model with reasoning disabled is not a reasoning model.**
The door leads out of the room the question was in. What is purchasable here
is self-consistency over Qwen3.5-9B *in its non-thinking mode*, which is a
second non-reasoning model, and the honest description of that is a
replication of the margin claims on a newer and larger non-reasoning model,
not the reasoning-native replication that was wanted. The finding stands
either way: **to measure this model at all, the thing that makes it
interesting had to be switched off.**

## What establishing this cost

| | samples | spend |
|---|---|---|
| capability gate, five candidates | 5 requests | under $0.01 |
| cap probe at 2048, 4096, 8192 | 84 | $0.1032 |
| thinking-control probe, 2048, two variants | 32 | $0.0137 |
| cap probe at 6144, thinking off | 32 | $0.0178 |
| **total** | **148** | **$0.1347** |

Against a $0.15 ceiling set before any of it ran. Every probe sample is a
proper `Sample` record under its own `param_hash`, written to the exploratory
split on the 8 lowest-id problems already burned for Qwen2.5-7B, so the
69-problem holdout stays unexamined for both models.

Thirteen cents to establish that the thing could not be bought as specified,
against $1.77 for the run itself. That ratio is the argument for probing.

## A silent defect this uncovered, and why it belongs in this note

The margin came back null on all 32 of the first usable Qwen3.5-9B samples.
Not censored, null, with no error anywhere.

Together returns logprobs in two shapes and **which one arrives is a property
of the model, not of the request**. Qwen2.5-7B returns parallel arrays
(`tokens`, `top_logprobs`). Qwen3.5-9B returns the OpenAI-nested shape
(`content`, each entry carrying its own `top_logprobs` list).
`char_span_to_token_span` already read both. `derive_row` read only the first,
and on the second it found no alternatives, produced no margin, and raised
nothing.

This is the response-side twin of the request-side failure `build_payload`
already documents, where sending OpenAI's `logprobs: true` to Together yields
a well formed depth-1 response that looks like unsupported logprobs. Both are
the same shape of bug: a valid response that never contained what was asked
for. Shape knowledge now lives in one function, `top_alternatives_at`, beside
the other shape-tolerant reader, with a test asserting both spellings give the
same margin.

Verified additive: all 12,672 Qwen2.5-7B rows rebuild byte-identical, so the
registered MD1 and MD2 verdicts are unmoved. Post-fix the cap-6144 probe
measures 32 of 32 margins, 1 censored, median 22.95 nats.

**Had the confirmatory run been bought before the probe, it would have
produced 3,168 samples with a null margin on every one**, and the registered
claims would have been untestable on data already paid for. The 13 cents
bought that too.

## The accuracy signal, flagged not concluded

29 of 32 probe samples correct, 7 of the 8 problems at 4 of 4. Wilson
[0.7578, 0.9676] on the naive binomial, and wider once clustering is honoured.

Eight non-random problems is not an accuracy estimate and this note does not
offer one. It is flagged because it bears directly on whether the descriptive
claims can be tested: MD3 and MD4 are keyed on incorrect samples, and at
accuracy 0.90 roughly 156 of 198 problems would carry fewer than three
incorrect samples at M=16 and be excluded by the registered rule. The
resolution check says the claims still resolve on the survivors, down to about
20 problems, but the surviving set would be selected for being the problems
this model gets wrong, which is a different population from the one MD1 and
MD2 were calibrated on. Doc 2 section 7.2 requires that heterogeneity be
published beside the pooled figure, and here it would need to lead.

## What this closes and what it leaves open

Closed: a reasoning-native replication of the margin claims is not purchasable
on this account. Three models, three independent reasons, all measured.

Open, and cheap now that the door is known: the same claims on Qwen3.5-9B with
thinking disabled, at cap 6144 and M=16, for $1.77. That is a replication
across a generation and a size within one family, on a second non-reasoning
model. It is not the study that was wanted and it should not be described as
one.
