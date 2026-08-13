# Provenance of copied code

One section per file copied into this repo from elsewhere. Written at copy
time, not reconstructed afterwards. A copied file whose origin is not recorded
here is a file nobody can check the published numbers against.

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
