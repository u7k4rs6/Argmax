"""Bibliography verification: every entry checked against a source, not memory.

## Why this exists

A bibliography entry in this project was written from a search-result title.
Its author list named a person who is not an author and omitted two who are.
It survived a merge, a build, and a full pre-submission read, and was caught
only because a human asked, entry by entry, which ones had actually been
opened. That is the same root cause as the other defects this project has
disclosed: a claim made from recollection rather than from a source.

The instruction that caught it is not a check. This module is.

Two rules, and an entry must satisfy exactly one:

1. **It carries an arXiv id.** Then title, author list and year are compared
   against the arXiv API, and any mismatch fails with both values named.
2. **It does not.** Then a human recorded which source they opened and when,
   in `references.provenance.json`. An entry with no recorded source fails.

The network is not hit on an ordinary test run: API responses are cached to a
tracked file carrying the date each entry was verified. `refresh_cache()`
re-fetches deliberately.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ARXIV_API = "https://export.arxiv.org/api/query"

#: An id like 2407.21787, with or without a version suffix.
ARXIV_ID = re.compile(r"arXiv[:\s]*(\d{4}\.\d{4,5})(v\d+)?", re.IGNORECASE)


@dataclass
class BibEntry:
    key: str
    kind: str
    fields: dict[str, str] = field(default_factory=dict)

    @property
    def arxiv_id(self) -> str | None:
        for value in self.fields.values():
            m = ARXIV_ID.search(value)
            if m:
                return m.group(1)
        return None

    @property
    def title(self) -> str:
        return self.fields.get("title", "")

    @property
    def authors(self) -> list[str]:
        return split_authors(self.fields.get("author", ""))

    @property
    def year(self) -> str:
        return self.fields.get("year", "").strip()


def parse_bib(text: str) -> list[BibEntry]:
    """Parse enough BibTeX for this project's own file.

    Deliberately small: it handles `@type{key, field={...}, ...}` with braced
    values and nothing else. A file it cannot parse raises rather than
    silently returning fewer entries, because a verification pass that skips
    an entry is worse than one that fails.
    """
    entries: list[BibEntry] = []
    for match in re.finditer(r"@(\w+)\s*\{([^,]+),", text):
        kind, key = match.group(1).strip(), match.group(2).strip()
        start = match.end()
        depth, i = 1, match.start()
        # walk from the opening brace of the entry to its match
        i = text.index("{", match.start())
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    body = text[start:j]
                    break
        else:
            raise ValueError(f"unterminated bib entry: {key}")
        fields: dict[str, str] = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{", body):
            name = fm.group(1).lower()
            d, k = 1, fm.end()
            while d and k < len(body):
                if body[k] == "{":
                    d += 1
                elif body[k] == "}":
                    d -= 1
                k += 1
            fields[name] = body[fm.end() : k - 1]
        entries.append(BibEntry(key=key, kind=kind, fields=fields))
    if not entries:
        raise ValueError("no bib entries parsed; the parser or the file is wrong")
    return entries


def normalize_title(value: str) -> str:
    """Compare titles on words, not on LaTeX or punctuation."""
    value = re.sub(r"\\[a-zA-Z]+", " ", value)
    # braces are BibTeX capitalisation protection: {LLM}s is one word.
    value = value.replace("{", "").replace("}", "").replace("$", " ")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


def split_authors(value: str) -> list[str]:
    if not value.strip():
        return []
    return [a.strip() for a in re.split(r"\s+and\s+", value) if a.strip()]


def surname(author: str) -> str:
    """Surname only: initials and given-name spellings differ between sources.

    Author-order and author-set errors are what this check is for, and both
    survive a surname comparison. A wrong first initial does not.
    """
    author = author.replace("{", "").replace("}", "").strip()
    if "," in author:
        last = author.split(",")[0]
    else:
        parts = author.split()
        last = parts[-1] if parts else ""
    # final token only: sources disagree on whether a particle belongs to the
    # surname ("Guedes de Souza" against "Souza"), and that disagreement is not
    # the error this check exists to find.
    last = last.split()[-1] if last.split() else ""
    last = unicodedata.normalize("NFKD", last)
    last = "".join(c for c in last if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", last.lower())


@dataclass
class Mismatch:
    key: str
    field_name: str
    in_bib: str
    at_source: str

    def __str__(self) -> str:
        return (
            f"{self.key}: {self.field_name} disagrees with the source\n"
            f"    bib   : {self.in_bib}\n"
            f"    source: {self.at_source}"
        )


def compare(entry: BibEntry, meta: dict[str, Any]) -> list[Mismatch]:
    """Compare one entry against fetched metadata."""
    out: list[Mismatch] = []
    if normalize_title(entry.title) != normalize_title(meta.get("title", "")):
        out.append(Mismatch(entry.key, "title", entry.title, meta.get("title", "")))

    bib_names = [surname(a) for a in entry.authors]
    src_names = [surname(a) for a in meta.get("authors", [])]
    # `and others` is BibTeX for et al.: check the named prefix, not the count.
    truncated = bool(bib_names) and bib_names[-1] == "others"
    if truncated:
        bib_names = bib_names[:-1]
        src_names = src_names[: len(bib_names)]
    if bib_names != src_names:
        out.append(
            Mismatch(
                entry.key,
                "authors",
                f"{len(bib_names)}: " + ", ".join(bib_names),
                f"{len(src_names)}: " + ", ".join(src_names),
            )
        )

    src_year = str(meta.get("year", ""))
    if entry.year and src_year and entry.year != src_year:
        out.append(Mismatch(entry.key, "year", entry.year, src_year))
    return out


# --- cache ------------------------------------------------------------------


def load_cache(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(path: Path, cache: dict[str, Any]) -> None:
    path.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")


def fetch_arxiv(arxiv_id: str) -> dict[str, Any]:
    """Fetch one record. Only called by an explicit refresh, never by a test."""
    import httpx  # imported here so importing this module needs no HTTP client

    r = httpx.get(ARXIV_API, params={"id_list": arxiv_id}, timeout=60)
    r.raise_for_status()
    xml = r.text
    entry = xml.split("<entry>", 1)[-1]
    title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
    authors = re.findall(r"<name>(.*?)</name>", entry, re.DOTALL)
    published = re.search(r"<published>(\d{4})-", entry)
    if not title or not authors:
        raise ValueError(f"arXiv returned no usable record for {arxiv_id}")
    return {
        "title": " ".join(title.group(1).split()),
        "authors": [" ".join(a.split()) for a in authors],
        "year": published.group(1) if published else "",
    }
