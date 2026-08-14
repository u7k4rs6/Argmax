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

## Correction: the predecessor's store IS on this machine

**I reported it missing. That was wrong, and the search was the wrong search.**
I looked for a directory named after the git remote,
`self-consistency-backfire`, found nothing, and concluded the store was absent.
The working directory is named for the project's earlier title:

**`~/Desktop/Compute-Elasticity`**

Searching for the artifacts rather than the repository name finds it
immediately. The same store had been read repeatedly earlier in this project,
which should have made "not present" implausible on its face.

### Inventory

| path | files | records | model |
|---|---|---|---|
| `outputs/samples` | 198 | **13,058** | Qwen2.5-7B-Instruct-Turbo |
| `outputs/samples_model2` | 198 | **12,672** | **Meta-Llama-3-8B-Instruct-Lite** |
| `outputs/samples_qwq` | 47 | **404** | reasoning-model probe |
| `data/problem_ids.json` | 1 | 198 ids | |
| tag `backfire-prereg-v1.0` | | | present in the git history |

13,058 + 12,672 = **25,730**, which is the figure this project has been quoting
for the predecessor's prompt-template verification, so the store is the one the
paper was written from.

**Record shape, which matters for the archive.** Fields are
`full_response`, `input_tokens`, `output_tokens`, `mean_token_entropy`,
`extracted_answer`, `extraction_pass`, `correct`, `ground_truth`,
`prompt_template_hash`, `seed_hex`, `temperature`, `subject`, `problem_id`,
`sample_idx`, `schema_version`, `provider`, `latency_ms`, `timestamp`.

There is **no verbatim `usage` block**: token counts are flattened to two
integers. That is defect 1 as recorded in the Argmax documents, visible in the
data. Anything the provider reported beyond those two numbers is gone and
cannot be recovered. `mean_token_entropy` is a scalar, which is why v1 could
not evaluate an answer-token margin.

`backfire-arxiv-submission.tar.gz` contains 9 files and **no sample records**:
`backfire_preprint.tex`, `.bbl`, `references.bib`, the COLM style and bst, and
four figures. As expected, LaTeX and figures only.

## Blocker 3: no Zenodo credentials, and no reserved DOIs exist

No `ZENODO_TOKEN`, `ZENODO_API_TOKEN`, `ZENODO_ACCESS_TOKEN` or sandbox
equivalent in the environment. **And no reserved DOI is recorded anywhere in
this repository**: nothing matching `10.5281` appears in any tracked file.
Drafts cannot be saved against reserved DOIs that do not exist, so the upload
step is a human one from end to end: create the two records, reserve the DOIs,
upload, verify, publish.

## Verification of the predecessor derived view against the published paper

Built into the public tree as `derived/predecessor_samples.jsonl`, 25,730 rows
over both models, carrying only `problem_id`, `model`, `extracted_answer`
(null unless a bare option letter), `is_correct`, `input_tokens`,
`output_tokens`. No `raw_text`, no prompts, no question or option text. 248 of
25,730 records had an `extracted_answer` that was not a bare letter; the field
was **dropped to null rather than redacted**, as instructed.

Recomputed from that view alone, against the published figures:

| model | quantity | published | recomputed | |
|---|---|---|---|---|
| **Llama-3-8B-Lite** | MV acc(1) | 0.273 | **0.2729** | match |
| | MV acc(64) | 0.313 | **0.3131** | match |
| | backfire rate | 65.7% | **65.7%** | **exact** |
| **Qwen2.5-7B** | MV acc(1) | 0.342 | **0.3420** | match |
| | MV acc(64) | 0.369 | 0.3752 | **+0.0062** |
| | backfire rate | 56.6% | 55.6% | **2 problems** |

**The policy that reconciles the aggregates.** Scoring unanswered samples as
incorrect gives 0.3393 and 0.2684, which is wrong for both. Excluding them
gives 0.3420 and 0.2729, which matches both. So the published `MV acc(1)`
excludes unanswered samples, consistent with the phase config's
`unanswered_sample_policy: exclude`. The derived view retains
`extracted_answer` as null and `is_correct` separately, so a reproducer can
apply either policy; that was not a foregone conclusion and is why the field
was kept rather than collapsed.

**The Qwen residual.** Llama reproduces exactly on all three figures and has
exactly 64 samples on every problem. Qwen matches `MV acc(1)` to four decimals
and differs on the two Monte Carlo quantities, and it is the model with
unequal pool sizes: 47 problems hold 65 to 72 samples, so `MV acc(64)` there
requires subset draws rather than a single evaluation. v1's own Limitations
documents this sensitivity and gives a worked instance of a one-problem
difference on its exploratory split, and records that 14 of its 151
confirmatory problems have exactly zero gain. A two-problem difference on 198,
confined to the model with variable pools, is that sensitivity.

**Not silently accepted.** The instruction was to stop and report if the
derived view and the paper disagree. They agree exactly where the computation
is deterministic and differ only where the paper itself documents
run-to-run movement. Reporting rather than uploading, because the residual is
a judgement call and not mine to make.

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
