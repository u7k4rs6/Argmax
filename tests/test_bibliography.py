"""Every bibliography entry is checked against a source, not against memory.

The incident: an entry's author list was written from a search-result title.
It named a person who is not an author and omitted two who are, and it
survived a merge, a build and a full read. See `argmax.bib`.

This suite never touches the network. Entries with an arXiv id are compared
against a cached API response; `scripts/verify_bib.py --refresh` refetches.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from argmax.bib import compare, load_cache, parse_bib

REPO = Path(__file__).resolve().parents[1]
BIB = REPO / "paper" / "tex" / "references.bib"
CACHE = REPO / "paper" / "tex" / "references.verified.json"
PROV = REPO / "paper" / "tex" / "references.provenance.json"


def entries():
    return parse_bib(BIB.read_text(encoding="utf-8"))


def test_the_bibliography_parses_and_is_not_empty():
    e = entries()
    assert len(e) >= 16, f"only {len(e)} entries parsed; the parser may be wrong"


def test_every_arxiv_entry_matches_the_arxiv_record():
    """Title, full author list and year, against the cached API response."""
    cache = load_cache(CACHE)
    problems: list[str] = []
    checked = 0
    for e in entries():
        if not e.arxiv_id:
            continue
        rec = cache.get(e.key)
        if rec is None:
            problems.append(
                f"{e.key} ({e.arxiv_id}) has never been verified; "
                f"run scripts/verify_bib.py --refresh"
            )
            continue
        if rec.get("arxiv_id") != e.arxiv_id:
            problems.append(
                f"{e.key}: cached id {rec.get('arxiv_id')} != bib id {e.arxiv_id}"
            )
            continue
        checked += 1
        problems.extend(str(m) for m in compare(e, rec))
    assert checked >= 6, f"only {checked} arXiv entries verified"
    assert not problems, "\n".join(problems)


def test_every_non_arxiv_entry_records_the_source_that_was_opened():
    prov = json.loads(PROV.read_text(encoding="utf-8"))
    problems = []
    for e in entries():
        if e.arxiv_id:
            continue
        rec = prov.get(e.key)
        if not rec:
            problems.append(f"{e.key}: no recorded source. Open one and record it.")
            continue
        for required in ("source", "method", "verified_utc", "checked"):
            if not rec.get(required):
                problems.append(f"{e.key}: provenance missing '{required}'")
    assert not problems, "\n".join(problems)


def test_every_verification_records_when_it_happened():
    """A cache with no date cannot be audited or refreshed on a schedule."""
    cache = load_cache(CACHE)
    assert cache, "verification cache is empty"
    for key, rec in cache.items():
        stamp = rec.get("verified_utc", "")
        assert stamp, f"{key}: no verified_utc"
        date.fromisoformat(stamp)  # raises if malformed


def test_provenance_has_no_entries_for_keys_that_left_the_bibliography():
    """A stale provenance record would vouch for an entry nobody can read."""
    prov = json.loads(PROV.read_text(encoding="utf-8"))
    keys = {e.key for e in entries()}
    stale = [k for k in prov if not k.startswith("_") and k not in keys]
    assert not stale, f"provenance for entries no longer in the bib: {stale}"


# --- the comparator itself, so a green suite is not a broken checker --------


def test_a_fabricated_author_is_caught():
    from argmax.bib import BibEntry

    e = BibEntry("x", "article", {"title": "T", "author": "Real, A and Fake, B", "year": "2025"})
    out = compare(e, {"title": "T", "authors": ["A Real"], "year": "2025"})
    assert any(m.field_name == "authors" for m in out)


def test_a_missing_author_is_caught():
    from argmax.bib import BibEntry

    e = BibEntry("x", "article", {"title": "T", "author": "Real, A", "year": "2025"})
    out = compare(e, {"title": "T", "authors": ["A Real", "B Other"], "year": "2025"})
    assert any(m.field_name == "authors" for m in out)


def test_reordered_authors_are_caught():
    from argmax.bib import BibEntry

    e = BibEntry("x", "article", {"title": "T", "author": "Bee, B and Ay, A", "year": "2025"})
    out = compare(e, {"title": "T", "authors": ["A Ay", "B Bee"], "year": "2025"})
    assert any(m.field_name == "authors" for m in out)


@pytest.mark.parametrize(
    "bib_title,src_title",
    [("{GPQA}: A {Google}-Proof Benchmark", "GPQA: A Google-Proof Benchmark"),
     ("Reported Confidence in {LLM}s", "Reported Confidence in LLMs")],
)
def test_bibtex_capitalisation_braces_are_not_a_mismatch(bib_title, src_title):
    from argmax.bib import BibEntry

    e = BibEntry("x", "article", {"title": bib_title, "author": "A, B", "year": "2025"})
    out = compare(e, {"title": src_title, "authors": ["B A"], "year": "2025"})
    assert not [m for m in out if m.field_name == "title"]


def test_and_others_is_treated_as_et_al():
    from argmax.bib import BibEntry

    e = BibEntry("x", "article", {"title": "T", "author": "First, A and others", "year": "2025"})
    out = compare(e, {"title": "T", "authors": ["A First", "B Second", "C Third"], "year": "2025"})
    assert not [m for m in out if m.field_name == "authors"]


def test_a_surname_particle_is_not_a_mismatch():
    from argmax.bib import BibEntry

    e = BibEntry("x", "article", {"title": "T", "author": "Guedes de Souza, R", "year": "2026"})
    out = compare(e, {"title": "T", "authors": ["Rodrigo Guedes de Souza"], "year": "2026"})
    assert not [m for m in out if m.field_name == "authors"]


# --- the generated submission package ---------------------------------------


def test_the_arxiv_package_is_byte_identical_to_its_source():
    """The document scan skips `paper/arxiv_v2/` as a copy. Prove it is one.

    An exemption granted to a copy is only as good as the copy being a copy.
    If the package drifts from `paper/tex/`, the scans stop covering what is
    actually submitted, which is the one file that reaches a reader.
    """
    src = REPO / "paper" / "tex"
    pkg = REPO / "paper" / "arxiv_v2"
    if not pkg.exists():
        pytest.skip("no submission package built")
    pairs = {
        "backfire_v2.tex": "backfire_preprint.tex",
        "backfire_v2.bbl": "backfire_preprint.bbl",
        "colm2026_conference.sty": "colm2026_conference.sty",
        "colm2026_conference.bst": "colm2026_conference.bst",
        "two_units.png": "two_units.png",
        "backfire_both.png": "backfire_both.png",
        "calibration_both.png": "calibration_both.png",
        "gate_sweep_both.png": "gate_sweep_both.png",
        "pareto_both.png": "pareto_both.png",
    }
    missing = [p for p in pairs if not (pkg / p).exists()]
    assert not missing, f"package is missing files: {missing}"
    drifted = [
        p for p, s in pairs.items() if (pkg / p).read_bytes() != (src / s).read_bytes()
    ]
    assert not drifted, (
        "submission package has drifted from paper/tex/ and is no longer a copy: "
        f"{drifted}. Rebuild it or remove the scan exemption in argmax.repo."
    )
    assert len(list(pkg.iterdir())) == len(pairs), (
        "package contains files not covered by this check: "
        f"{sorted(p.name for p in pkg.iterdir() if p.name not in pairs)}"
    )
