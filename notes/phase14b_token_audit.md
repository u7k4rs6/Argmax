# Step 0: phase 14b token audit

Status: **not started.** Nothing in this repo may spend credits until this
returns real numbers, and nothing may be written into a `[BLOCKED: Step 0]`
field until then either.

The audit reads the abandoned phase 14b probe from the predecessor
(`self-consistency-backfire`) for measured token counts. That repo is not in
this checkout; locate it before starting.

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

_(empty — fill in with measured numbers, the date, and the source of each)_
