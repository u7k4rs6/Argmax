"""Which files in this repository a repository-wide check must read.

## Why this exists

Two checks scan documents: the citation-provenance check in
`tests/falsification.py` and the answer-rate pairing check in
`argmax.persist.pairing`. Both were written as an **allow-list of known
locations**, a glob per directory somebody remembered at the time. Both then
missed a directory, three times between them:

1. `notes/` was outside the pairing check, and a table of per-problem
   accuracies by completion-length quintile was published there with no answer
   rates. Doc 4 section 9.1.1 records it.
2. `paper/` was outside the citation-provenance check, so the draft, the one
   document where citing a superseded source does real damage, was unscanned.
3. `paper/` was outside the pairing check too, for the same reason.

Three misses, one cause. **An allow-list of remembered places fails whenever
somebody creates a place.** The default is wrong, so it is inverted here: walk
everything, and exclude only what an explicit, justified entry excludes.

Adding a directory to `EXCLUSIONS` requires a reason in the table. Adding a
new directory of documents requires nothing, which is the point.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

#: Each entry is (path fragment, why). The reason is not decoration: it is the
#: thing a reviewer checks when a document turns out to be unscanned.
EXCLUSIONS: tuple[tuple[str, str], ...] = (
    (".git", "version control internals, not project documents"),
    (".venv", "installed third-party packages; their docs are not our claims"),
    ("node_modules", "same, for any JS tooling"),
    ("__pycache__", "compiled bytecode, generated from files already scanned"),
    (".pytest_cache", "test-runner scratch state, regenerated on every run"),
    (".ruff_cache", "linter scratch state, regenerated on every run"),
    (".mypy_cache", "type-checker scratch state, regenerated on every run"),
    (".playwright-mcp", "tool scratch output, not authored by this project"),
    # NOT a blanket exclusion. The earlier reason given here, "never contains
    # authored prose", was false: DATASETS.md is the licence-notes
    # document doc 3 s7 depends on, and the glob list this walk replaced
    # included data/*.md and scanned it. Inverting the default dropped a
    # document, which is the same failure the inversion was meant to end. The
    # file has since moved to docs/DATASETS.md so it is tracked at all.
    (
        "data/raw",
        "gitignored sample store; machine-written records only, and CLAUDE.md "
        "forbids committing anything under it",
    ),
    (
        "data/derived",
        "gitignored derived tables; a pure function of raw, machine-written",
    ),
    (
        "runs",
        "gitignored run artefacts and ledger; machine-written, not authored prose",
    ),
    (
        "site-packages",
        "installed dependencies wherever they land",
    ),
)


def is_excluded(path: Path, root: Path) -> str | None:
    """Return the reason `path` is excluded, or None if it must be scanned."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return "outside the repository root"
    rel = "/".join(parts)
    for fragment, reason in EXCLUSIONS:
        if "/" in fragment:
            if rel == fragment or rel.startswith(fragment + "/"):
                return reason
        elif fragment in parts:
            return reason
    return None


#: Authored-document suffixes. `.tex` is here because the manuscript is the
#: document where a bad citation or an unpaired accuracy actually reaches a
#: reader, and for a while it lived only as markdown that the scans covered
#: while the LaTeX they were ported into was covered by nothing.
DOCUMENT_SUFFIXES: tuple[str, ...] = (".md", ".tex")


def iter_documents(root: Path, suffix: str | tuple[str, ...] = DOCUMENT_SUFFIXES) -> Iterator[Path]:
    """Every authored document in the repository, excluding only the above.

    Deliberately a walk rather than a set of globs. A check built on this
    picks up a new directory the day it is created, which is the failure mode
    the module docstring records three instances of.
    """
    suffixes = (suffix,) if isinstance(suffix, str) else suffix
    seen: set[Path] = set()
    for suf in suffixes:
        for path in sorted(root.rglob(f"*{suf}")):
            if path.is_file() and path not in seen and is_excluded(path, root) is None:
                seen.add(path)
                yield path
