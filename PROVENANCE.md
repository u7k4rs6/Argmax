# Provenance of copied code and cited work

One section per file copied into this repo from elsewhere. Written at copy
time, not reconstructed afterwards. A copied file whose origin is not recorded
here is a file nobody can check the published numbers against.

---

## The predecessor's paper, as a source of record

Every figure this repository quotes from the predecessor study comes from the
published paper and from nothing else. This section is the source of record and
`tests/falsification.py` enforces it.

| Field | Value |
|---|---|
| Citation | `arXiv:2608.11403` |
| Title | When Self-Consistency Backfires: Majority Vote Hurts the Majority of Hard Science Problems for Small LLMs |
| Venue line on the artifact | Accepted at the COLM 2026 Workshop on Efficient Reasoning |
| Local artifact | `paper/backfire_preprint.pdf` |
| sha256 | `59d4dea8eba80b2a8bc05554c16b57fc854f5b3c6a7b0fd0e4e76b6c585ad6cc` |
| Size | 448,797 bytes |
| Second artifact | `paper/backfire_colm_submission.pdf`, sha256 `a5ad3c3cb5b29730527c356ed18736b9e2419e3819297e7fbdf8791c4bce7f45` |
| Read | 2026-08-13 |

**The arXiv version number is not stamped on the artifact.** The PDF carries a
venue line and no `v1`/`v2` marker, so the version recorded here is the file
digest, which is verifiable, rather than an arXiv revision number, which would
be a guess. **A maintainer must confirm the arXiv version before any Argmax
draft cites it.** That is the one field here nobody has checked.

**The PDFs are committed, and the doc 3 section 5 check was run before saying
so.** A paper that quoted benchmark items would put question text in this
repository, which is forbidden. This one does not: extracting the text yields
4,232 words, with zero occurrences of `Which of the following`, zero
option-block markers, zero `gpqa_diamond` task ids and zero canary strings. It
reports aggregate metrics only. Repeat the check with
`pdftotext paper/backfire_preprint.pdf -` before committing any future revision.

An earlier version of this section claimed the PDFs were not committed. They
were, added by a `git add -A`, and the claim was written without checking. The
check has now been run and the artifacts stay, because a citation source of
record that a reader cannot open is not a source of record.

### Superseded drafts, which nothing may cite

The predecessor's repository also contains earlier drafts, and they disagree
with the published paper on the headline numbers and on what the paper calls
its central open question:

| Draft | What it says | Status |
|---|---|---|
| `backfire_paper_draft.md`, repo root | 47 problems, backfire 47 and 66 percent, "a deploy-time signal ... is the key open problem" | **superseded** |
| `paper/backfire_paper_draft_v3.md` | earlier still | **superseded** |
| `paper/backfire_paper_draft_v4.md` | 198 problems, matches the published text | superseded by the artifact, which is what may be cited |

An Argmax document cited the first of these and carried its numbers into a
scope decision. The test exists because that happened, not in anticipation of
it happening.

---

## `src/argmax/extract/scoring_verbatim.py`

The five-pass answer extraction ladder, copied byte for byte from the
predecessor study so that extraction behaviour is comparable with the
published results.

| Field | Value |
|---|---|
| Source repo | `https://github.com/u7k4rs6/self-consistency-backfire` |
| Source path | `pilot/scoring.py` |
| Tag | `backfire-prereg-v1.0` |
| Tag commit SHA | `32ed32f6fc00c1b98124aeb3d3068fcec6e081d4` |
| Source HEAD SHA at copy time | `a7f168e685b2eecf4793e2b635a6c801b6192d91` |
| Blob SHA (git, identical at both refs) | `f3754c738154c591c10379475c2b3fa48890b64f` |
| sha256 of the copied file | `f22e15c8cd1d6ed5a4b58fd5a289fcb688e3dd91564a7935d7203bf58c6bafec` |
| Lines | 180 |
| Date copied | 2026-08-13 |

### Did the file change between the tag and HEAD?

**No.** `git diff backfire-prereg-v1.0 HEAD -- pilot/scoring.py` is empty and
both refs point at blob `f3754c73`. The tagged version was copied regardless,
because "identical today" and "taken from the tag" are different claims, and
only the second one stays true if the predecessor repo moves.

The tag is the commit that produced the published confirmatory results, so it
is the version the published numbers were computed with.

### Copied verbatim

Same regexes, same order, same slice widths, same variable names, same
docstrings, no reformatting. The file is excluded from `ruff` and from the
whitespace pre-commit hooks in this repo, because a formatter that touches it
breaks the only property that makes it worth copying.
`tests/test_ladder_provenance.py` asserts the sha256 above on every run.

Behaviour worth knowing about, preserved rather than corrected:

- **`_PASS3` and `_PASS4` are the same regex,** `\b([A-D])\b`. They differ
  only in what they are applied to: pass 3 takes the last non-empty line,
  pass 4 takes the last 500 characters. This is not a typo to fix. Fixing it
  changes which pass index fires and makes the pass distribution
  incomparable with the published one.
- **Every pass takes the LAST match,** via `findall()[-1]`, not the first.
- **Pass 1 reads only the last 200 characters,** pass 4 only the last 500. An
  answer stated early and not restated is invisible to pass 1.
- **The alphabet is hard-coded to `A-D`.** The ladder cannot score a
  benchmark tier with a different option count. The instrumented wrapper
  refuses such a tier loudly rather than silently under-extracting.
- **`pass_number=5` from `extract_answer` means the regex ladder was
  exhausted,** not that an LLM ran. In `score_sample`, 5 means the LLM scorer
  produced the verdict and 6 means all passes failed with no LLM available.
  The predecessor's phase 14b probe called `extract_answer` directly, so its
  143 records at pass 5 are ladder exhaustions.

### Not used by this repo

`pass5_score` and `score_sample` are carried along because the copy is
verbatim, and neither is called here:

- `pass5_score` issues an API call. Argmax extraction runs offline over stored
  raw text (doc 2 s5.5), so an extractor that can call an API is an extractor
  that can spend credits during analysis.
- `score_sample` scores an unresolved sample as `correct=False`. Doc 4 s3.6
  forbids that coercion: `is_correct` is null when no answer was extracted.
  The predecessor's stored phase 14b data has 143 records carrying exactly
  this coercion, which is how a 35 percent truncation rate became invisible in
  its accuracy numbers.

`tests/test_ladder_provenance.py` asserts that neither function is reachable
from Argmax code.

### Instrumentation

Added in the commit immediately after the copy, in
`src/argmax/extract/ladder.py`, never in the copied file. The instrumented
wrapper records `extraction_pass`, `answer_span_chars`, `answer_span_tokens`
and `extractor_version` per doc 4 s3.6, and is asserted to return the same
answer and the same pass index as the verbatim function for every input it is
given.
