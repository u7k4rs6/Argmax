# Pre-registration registry

One row per tag. Written when the tag is cut, never edited afterwards.

The predecessor ended with `pre-pilot-v6.0` and `backfire-prereg-v1.0`
covering different hypothesis sets, and nearly cited the wrong one in the
paper. This file exists so that "which pre-registration covers this claim" is
answerable from one table.

## Rules

- Tag format is `argmax-prereg-<phase>-v<major>.<minor>`. No exceptions.
- Tags matching `argmax-prereg-*` are protected against deletion and
  force-push. A tag that can be moved is not a pre-registration.
- A tag is cut **before** the confirmatory samples for its phase are drawn.
- If a pre-registration turns out to be wrong, cut a new tag with a new
  version and add a row. Never move an existing one.
- Confirmatory analysis refuses to run without a `prereg_tag` in the manifest.
  The tag recorded there must appear in this table.

## Registry

| Tag | Date | Commit | Hypotheses covered | Analyses that may cite it |
|---|---|---|---|---|
| _(none yet, pre-Step 0)_ | | | | |

## Hypotheses

One row per hypothesis id. A hypothesis is not pre-registrable until every
field that decides it exists in the schema and every threshold is a literal
value here.

| Id | Statement | Deciding fields | Threshold | Direction | Tag |
|---|---|---|---|---|---|
| _(none yet)_ | | | | | |

## Claims

One row per `claim_id`. A claim is a sentence that may appear in the paper.
`tests/falsification.py` fails when a registered claim has zero backing rows
in its artifact table.

| Claim id | Sentence it licenses | Backing artifact table | Rows required |
|---|---|---|---|
| _(none yet)_ | | | |

## Thresholds

Threshold values are asserted by the falsification suite against the tagged
commit, not merely used to compute a verdict. A regenerated result whose
threshold was quietly edited must fail loudly rather than pass against a moved
line.

| Threshold name | Value | Set in | Tag | Rationale |
|---|---|---|---|---|
| _(none yet)_ | | | | |
