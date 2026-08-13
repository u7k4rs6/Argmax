# Step 0: phase 14b token audit

Status: **audit read, numbers below, nothing written into a config.** Every
`[BLOCKED: Step 0]` marker is still blocked: this file reports what the stored
data says, and turning a measurement into a `max_tokens` or an `M` is a
decision, not a transcription.

The audit reads the abandoned phase 14b probe from the predecessor
(`self-consistency-backfire`) for measured token counts.

## Provenance of everything below

| What | Where |
|---|---|
| Source repo | `github.com/u7k4rs6/self-consistency-backfire` |
| Probe data | `outputs/samples_qwq/*.jsonl`, 47 files, 404 records |
| Probe summary | `outputs/gate_qwq/qwq_probe_results.json` |
| Read at commit | `a7f168e685b2eecf4793e2b635a6c801b6192d91` (HEAD) |
| Probe added at | `3c1a7d0475825c506764712ce61703c03bd06b6f` |
| Probe script | `scripts/run_phase14b_qwq_probe.py` |
| Date read | 2026-08-13 |

The probe postdates the pre-registration tag: `backfire-prereg-v1.0`
(`32ed32f6fc00c1b98124aeb3d3068fcec6e081d4`) contains neither
`outputs/samples_qwq/` nor `outputs/gate_qwq/`. Phase 14b is exploratory
post-hoc work, which is what its own script says, and it is read here as
measurement rather than as evidence for any pre-registered claim.

Everything in the findings comes from the stored records, except the four
figures marked *(script constant)*, which are not stored in any record and are
recoverable only from the code that wrote them. That distinction is the point
of the third question below.

## What must come out of it

These block spend. Each maps to a `[BLOCKED: Step 0]` marker in the configs.

| Number | Unblocks | Where it lands |
|---|---|---|
| p95 output tokens per reasoning model | `max_tokens` | `configs/models/<slug>.yaml` |
| truncation curve (share truncated vs `max_tokens`) | `max_tokens` | same |
| cost per sample | `M`, the N grid | `configs/phases/<phase>.yaml` |
| reasoning cost multiplier | whether reasoning models enter at all | PRD |
| mean output length | reasoning-model logprob retention | doc 4 s7 |

## Three questions worth answering while in there

Zero extra cost, and each decides a field in doc 4.

1. **Were logprobs requested at all in that probe, and did the provider return
   them for that model?** Decides whether the reasoning-model logprob policy
   in doc 4 section 7 is even a live question.
2. **Which provider and pricing were in effect?** So the cost model has a
   comparable baseline rather than a remembered rate.
3. **Is `finish_reason` stored, or is truncation only inferable from length?**
   Decides whether `hit_ceiling` can be reconstructed retrospectively.

## If the audit cannot answer them

A paid fallback probe is required. It should **double as the capability
probe** (doc 4 s2): the sample is being bought either way, so buy it once.

Run it as `make probe MODEL=<slug>`, which writes
`configs/models/<slug>.capabilities.json`.

## Interaction to decide jointly, not separately

`M` and the reasoning-logprob retention policy are coupled and should be
settled in the same sitting:

- A CI at the curve's endpoint requires `M > max(n_grid)` (doc 2 s2), which
  pushes `M` up.
- Per-token logprobs over long hidden chains run to hundreds of kilobytes per
  sample (doc 4 s7), and a larger `M` multiplies that.

Deciding them independently is how one of them quietly becomes infeasible.

## Findings

### What the probe was

47 GPQA Diamond problems, 8 samples each, 404 records stored. The model is
`MiniMaxAI/MiniMax-M2.7`, substituted for `Qwen/QwQ-32B`, which needed a
dedicated non-serverless endpoint. Temperature 0.7. `max_tokens` 16384
*(script constant)*, raised from 8192 after the model maxed out mid-think and
returned empty content.

### Token counts

| Quantity | Value |
|---|---|
| output tokens, min / p50 / p95 / max | 10 / 4,655 / 16,384 / 16,384 |
| output tokens, mean | 8,005 |
| input tokens, mean | 351 |
| total input / output tokens | 141,744 / 3,234,042 |

**p95 is censored and must not be used as a p95.** 35.1 percent of samples
(142 of 404) stopped at exactly 16,384 output tokens, so the upper tail of the
distribution was cut off by the cap rather than measured. The true p95 of an
uncapped run is not recoverable from this data at any confidence. What is
recoverable is a lower bound: `max_tokens` of 16,384 truncates about a third
of samples on this model and this benchmark tier.

Setting `max_tokens` from these numbers therefore requires either a fallback
probe at a higher cap, or an explicit decision to accept a known truncation
rate. Both are decisions, and neither is written here.

### The truncation finding, quantified

| Outcome | Count | Share |
|---|---|---|
| at the 16,384 cap | 142 | 35.1% |
| no visible text at all | 141 | 34.9% |
| ladder exhausted, no answer | 143 | 35.4% |
| at the cap AND no answer | 141 | 34.9% |

This is the finding that killed the phase: the model spent the entire output
budget on hidden chain of thought and returned nothing visible. It is a
property of the cost model, not a failure of the run.

All 143 unanswered samples are stored with `correct = false`. That is the
coercion doc 4 s3.6 forbids, visible in the predecessor's own data: an
unparseable sample is indistinguishable from a confidently wrong one, and the
35 percent truncation rate is therefore invisible in every accuracy number
computed from these files.

### Cost

| Quantity | Value |
|---|---|
| total spend | $3.9234 |
| cost per sample | $0.00971 |
| per-problem at N=8 | $0.0777 |

### Retention, doc 4 s7

Mean output length 8,005 tokens, at the 20 to 30 bytes per logprob entry doc 4
assumes, is roughly 156 to 235 KB per sample uncompressed. The section 7
premise holds with real numbers: for a reasoning model this is a disk-scale
question, not a rounding error, and it is coupled to `M`.

---

## The three questions

### 1. Were logprobs requested, and did the provider return them?

**Requested: yes, at depth 1.** The payload carries `"logprobs": 1`
*(script constant)*. Depth 1 returns the chosen token's logprob and no
alternatives.

**Returned: yes.** `mean_token_entropy` is numeric in 404 of 404 records, and
the function that produced it returns null when the logprob array is absent or
empty, so a numeric value in every record means Together AI returned per-token
logprobs for this model on every stored call. Values span 0.0015 to 2.31 nats.

Two consequences, and the second one is the more important:

- The per-token arrays themselves were **not** stored. Only the scalar
  survives. That is defect 1, confirmed directly in the stored data rather
  than inferred from the paper.
- At depth 1 there are no runner-up logprobs, so
  `answer_margin_vs_runner_up` was never computable from this probe **even if
  the arrays had been kept**. The retention policy in doc 4 s7 is a live
  question, but the margin gate additionally needs `top_logprobs >= 2`, which
  this probe never requested. A capability probe that only checks whether
  logprobs come back will not catch that; it has to record the depth.

### 2. Which provider, and which per-token pricing?

**Provider: Together AI.** `"provider": "together_ai"` is stored in all 404
records, and the base URL `https://api.together.xyz/v1` is a script constant.

**Pricing: $0.30 per 1M input tokens, $1.20 per 1M output tokens** *(script
constant)*, as `QWQ_PRICE_INPUT` and `QWQ_PRICE_OUTPUT`.

Not stored anywhere: the price, the date it was in effect, and the per-sample
cost. No record carries a cost field; the $3.9234 total in
`qwq_probe_results.json` is a sum computed at run time from constants that
carry no date. The rate is therefore a remembered number in exactly the sense
doc 3 s4.4 warns about, and it cannot be verified against what Together AI
actually charged. This is the argument for `pricing_snapshot_id` and
`cost_usd_est` being required per record.

### 3. Is `finish_reason` stored?

**No.** The key is absent from all 404 records. The stored fields are
`input_tokens`, `output_tokens`, `latency_ms`, `mean_token_entropy`, and the
extraction results; the provider's own stop reason was read from the response
and discarded.

Truncation is **not** inferable from text length. It is inferable from
`output_tokens` compared against the `max_tokens` the script used, which is
recoverable from the code and not from the data:

- `hit_ceiling` can be reconstructed retrospectively: `output_tokens >= 16384`
  is stored per record, giving the 142 above.
- `truncated`, meaning the provider said `finish_reason == "length"`, cannot be
  reconstructed at all. Whether the provider agreed with the token arithmetic
  is unknowable for this probe.

That gap is precisely why doc 4 s3.5 keeps the two fields separate rather than
deriving one from the other.

### What this does not answer

`max_tokens` stays blocked: the tail needed to set it was censored by the cap.
A fallback probe at a higher cap would measure it, and per doc 4 s2 that probe
should double as the capability probe, requesting `top_logprobs >= 2` so
question 1's second consequence is closed at the same time.
