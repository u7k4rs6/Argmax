# Artifact release, doc 3 section 7: blocked, with the blockers measured

Attempted, not completed. Three blockers, one of them substantive and
discovered by running the check rather than by planning around it.

## Blocker 1, substantive: the raw store fails the leakage check

**This is the finding.** Doc 3 section 7 says the raw store is archived "after
the leakage check". The check was run over the margin-v1 store and it fails:

```
leakage check: 198 files, 12672 lines, 129247 10-gram fingerprints
  HITS: 5669
LeakageDetected: release blocked.        (exit 1)
```

The mechanism is not a stored prompt. The `sample` record deliberately holds
`prompt_hash` and never the prompt. It is `raw_text`: **the model restates the
question inside its own chain of thought**, so the completions carry GPQA
question and option text even though the request never stored it.

That has consequences beyond this release, and they were not anticipated
anywhere in doc 3:

- **No chain-of-thought store on a gated benchmark is publishable verbatim.**
  The redaction rule in doc 3 section 5 covers what this project writes; it does
  not cover what the model writes back.
- A release therefore needs either per-record redaction of the matched
  n-grams, which mutates raw and collides with the append-only rule, or a
  derived-only release (ids, hashes, margins, token counts, verdicts) with raw
  withheld, or a gated repository with the same access conditions GPQA itself
  carries.
- **Recommendation: derived-only public release plus a gated raw release.**
  The derived table is what reproduces every number in the paper; the raw store
  is what reproduces the derived table. Splitting them keeps guarantee 1
  without publishing questions.

Not decided here. It changes what doc 3 section 7 promises, so a human decides
it.

## Blocker 2: the predecessor's store is not on this machine

`self-consistency-backfire` is not present. Only
`backfire-arxiv-submission.tar.gz` is, which is the paper submission and not
the sample store. The predecessor archive cannot be built from here.

## Blocker 3: no Zenodo credentials

No `ZENODO_TOKEN` or equivalent in the environment. Publishing is a human step.

## Also missing, and required by doc 3 section 7

`DATASETS.md` exists at `data/DATASETS.md`, which is **gitignored**, so the
licence notes the release must carry are not in the repository. Either it
moves out of `data/` or the release build reads it from an untracked path,
which makes the release unreproducible from a clone.

**Related defect, mine, one turn old.** The inverted document scan in
`argmax.repo` excludes `data/` wholesale with the stated reason "never
contains authored prose". That reason is false: `data/DATASETS.md` is authored
prose, and the previous glob list included `data/*.md` and scanned it. So the
inversion, which was justified as strictly wider coverage, silently dropped one
document. Reported rather than fixed in the same pass; the fix is an exception
for `DATASETS.md` or moving the file.

## Why this is urgent, which the run confirmed

`Meta-Llama-3-8B-Instruct-Lite`, one of v1's two models, returns
`model_not_available`: "Unable to access non-serverless model", recorded in
`configs/models/llama-3-8b-instruct-lite.capabilities.json`. **v1's Llama half
cannot be re-run today at any price without a dedicated endpoint.** Its stored
samples are the only remaining evidence for the 65.7 percent backfire figure.

The paper now argues that endpoint churn breaks replication. It is arguing that
from inside the failure.

## What exists and would go in a release, once blocker 1 is decided

| item | state |
|---|---|
| margin-v1 raw store, 12,672 samples | present, **fails leakage** |
| margin-v2 partial store, 1,253 samples | present, fails leakage by the same mechanism |
| derived table, 14,073 rows | present, rebuilds byte-identically, **not yet leak-checked** |
| ledger, 14,073 rows | present, reconciles to $4.667639 |
| manifests | present, three marked `reconstructed` |
| canary string | in doc 3 section 3; must be carried in the release README |
| licence notes | in `data/DATASETS.md`, gitignored |

**Next action for a human:** decide the derived-only versus gated split, then
the Zenodo upload. Nothing here should be published until that decision is
made, because the check that would have caught the problem has already fired.
