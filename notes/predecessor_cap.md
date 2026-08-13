# The predecessor's cap and answer rates

Why this is a note and not a footnote: under `02-technical-architecture.md`
section 7.1 as amended, comparability is keyed on the answer rate. Whether
Argmax may compare its curves to the published confirmatory numbers at all is
therefore decided by the numbers below, before any Argmax sample is drawn. That
is a PRD-level constraint, not an implementation detail.

Read-only against the predecessor. Nothing in that repository was modified.

## Provenance

| What | Value |
|---|---|
| Source repo | `github.com/u7k4rs6/self-consistency-backfire` |
| Pre-registration tag | `backfire-prereg-v1.0` (`32ed32f6fc00c1b98124aeb3d3068fcec6e081d4`) |
| Read at commit | `a7f168e685b2eecf4793e2b635a6c801b6192d91` |
| Stores read | `outputs/samples/`, `outputs/samples_model2/`, `outputs/samples_qwq/` |
| Date | 2026-08-13 |

## 1. What `max_tokens` was

**2048 for every published confirmatory run.** It appears as a literal in the
request payload rather than as a configured or registered value:

| Location at the tag | Value |
|---|---|
| `pilot/sampling.py:147`, the payload for the main sampler | `"max_tokens": 2048` |
| `scripts/run_model2_sampling.py:52`, `MAX_OUTPUT_TOKENS` | `2048` |
| `scripts/sample_for_entropy.py:46`, `_MAX_TOKENS` | `2048` |
| `scripts/sample_for_entropy_N4.py:42`, `_MAX_TOKENS` | `2048` |

The stored records do not carry `max_tokens`, so this is read from the code and
not from the data. The data corroborate it: the maximum `output_tokens` in both
confirmatory stores is exactly 2048, with 21 and 38 records sitting on it.

That the cap is a bare literal in a request body, rather than a registered
parameter, is the concrete form of what doc 2 section 7.1 now forbids. It was
the single most consequential experimental setting in the study and it was
typed inline in four places.

## 2. Answer rate per model

Answered means an answer was extracted. Truncated means `output_tokens` reached
the cap. Wilson intervals at 95 percent.

| Store | Model | Cap | Records | Problems | **Answer rate** | Truncated | Empty text |
|---|---|---|---|---|---|---|---|
| `samples/` | `Qwen/Qwen2.5-7B-Instruct-Turbo` | 2048 | 13,058 | 198 | **0.9946** [0.9932, 0.9958] | 0.0016 | 0.0000 |
| `samples_model2/` | `meta-llama/Meta-Llama-3-8B-Instruct-Lite` | 2048 | 12,672 | 198 | **0.9860** [0.9838, 0.9879] | 0.0030 | 0.0000 |
| `samples_qwq/` | `MiniMaxAI/MiniMax-M2.7` | 16,384 | 404 | 47 | **0.6460** [0.5982, 0.6911] | 0.3515 | 0.3490 |

Output length, for context:

| Store | p50 | p95 | max | mean |
|---|---|---|---|---|
| `samples/` | 555 | 1,084 | 2,048 | 598.9 |
| `samples_model2/` | 414 | 718 | 2,048 | 438.7 |
| `samples_qwq/` | 4,655 | 16,384 | 16,384 | 8,005.1 |

Per-problem answer rate, which is what decides whether a problem contributes at
all:

| Store | min | median | max | problems at 0.0 | problems at 1.0 |
|---|---|---|---|---|---|
| `samples/` | 0.492 | 1.000 | 1.000 | 0 of 198 | 181 |
| `samples_model2/` | 0.766 | 1.000 | 1.000 | 0 of 198 | 121 |
| `samples_qwq/` | 0.000 | 0.875 | 1.000 | **8 of 47** | 18 |

The two confirmatory models answer essentially always. The reasoning model
loses a third of its samples and loses eight problems outright.

## 3. What is not a barrier

Worth establishing first, because it narrows the constraint to one thing:

- **Same benchmark and same problems.** The 47 probe problems are a strict
  subset of the 198 confirmatory problems.
- **Same prompt.** `prompt_template_hash` is
  `e3544f731c3b30d4...` in all three stores. One store writes it with a
  `sha256:` prefix on some records, which is a formatting difference in the
  field, not a different template.
- **Same provider.** Together AI throughout.
- **Same temperature.** 0.7, apart from 320 records in the main store at 0.3
  and 1.0 that are a deliberate sensitivity sweep.

So the only material differences between the probe and the published runs are
the model and the cap, and the only consequence that matters is the answer
rate.

## 4. Applying the amended rule

### The two published models against each other

Their answer rates are 0.9946 and 0.9860. The Wilson intervals do **not**
overlap, so on a strict reading the rates do not match, despite the difference
being 0.86 percentage points on 13,058 and 12,672 records.

The rule's second clause applies, and it is demonstrated rather than asserted.
Recomputing the between-model comparison on answered samples only:

| | all samples | answered only | change |
|---|---|---|---|
| `Qwen2.5-7B` accuracy | 0.3406 | 0.3425 | +0.0019 |
| `Llama-3-8B-Lite` accuracy | 0.2684 | 0.2722 | +0.0038 |
| **difference between models** | **0.0722** | **0.0703** | **-0.0019** |

The comparison is insensitive to the answer-rate difference: the gap moves by
0.2 percentage points and the ranking does not move. **These two are
comparable**, and the reason is on the record.

### Argmax against the published numbers

This is the constraint. It depends entirely on what Argmax's own answer rate
turns out to be:

- **A non-reasoning model at 2048 tokens.** The published models answer at
  0.986 to 0.995 at that cap. A comparable model would land in the same place,
  and the comparison is available. This is the case where citing the published
  numbers is legitimate.
- **A reasoning model at any cap this project can afford.** The only measured
  point is 0.6460 at 16,384. Against 0.9946 that is a gap of **35 percentage
  points**, and no sensitivity argument survives it: 8 of 47 problems produce
  no answer at all, so the answered subpopulation is not a subset of the
  published population that anyone chose, it is the subset that finished
  thinking. `notes/max_tokens_estimate.md` section 7 shows that which problems
  those are is a property of the problem, not sampling noise, so restricting to
  the matching subpopulation does not rescue the comparison either. It changes
  which problems are being compared.

Binding 3 of doc 2 section 7.1 already refuses the second case outright,
because it spans a cap change. The answer rate is why that refusal is correct
rather than merely cautious.

### The consequence for the PRD

**Argmax cannot compare a reasoning-model curve to the predecessor's published
numbers.** Three options, and the cost of each:

1. **Run non-reasoning models at 2048** and cite the published numbers. Cheap,
   comparable, and it forfeits the reasoning-model question that motivated the
   project.
2. **Run reasoning models and treat the published numbers as unavailable.**
   The comparison becomes internal to Argmax: reasoning against non-reasoning,
   both measured here, both at rates this project records. This is the honest
   default and it is what section 7.1 pushes towards.
3. **Run both, at both caps.** Four cells, and the cost multiplies by the cap:
   the reasoning cells at a large budget dominate spend. It buys the bridge
   between the two literatures, and whether that bridge is worth its price is a
   PRD decision, not one to make in a config file.

None of the three is chosen here. What is settled is that the choice exists,
that it has to be made before sampling rather than at analysis time, and that
option 1's comparability is the only one that comes for free.

## 5. One thing this data cannot tell us

The published runs stored no `finish_reason` and no `max_tokens`, so the cap in
force is known from the code at a tag rather than from the artifacts. If that
repository's history were lost, the 2048 would be unrecoverable from the sample
store, and the 21 and 38 records sitting exactly on the cap would be the only
hint. That is the argument for doc 4 section 3.2 requiring `max_tokens` per
record and section 8 requiring it in the manifest: a cap that lives only in
code is a treatment that cannot be audited.
