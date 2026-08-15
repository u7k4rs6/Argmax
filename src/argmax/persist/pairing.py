"""Every published accuracy carries the answer rate that qualifies it.

Doc 4 section 9.1, implemented. The rule and the reason are in doc 4 section
4.1: a truncated sample casts no vote, so the pool that votes at a token cap is
smaller than N and is not a random subset of it. An accuracy published without
its rate looks exactly like an accuracy whose pool was complete, and the reader
has no way to tell.

This lives in `src/` rather than in the test because a check that only runs in
CI does not protect a live run. `make analyze` can call `assert_paired` before
it writes anything.

## What counts as an accuracy

A key, column or series named `accuracy` or ending in `_accuracy`. That covers
`single_sample_accuracy`, `vote_accuracy`, `peak_accuracy` and
`accuracy_under_strategy` without naming them.

## What counts as a match

An answer rate at the same granularity and in the same place: the same table
row or column set for a table, the same panel for a figure. A rate in another
file is not a match, because the failure being guarded against is a number
travelling on its own.

For a per-N accuracy, meaning a mapping keyed by grid point, the rate must be a
mapping too and must cover every N the accuracy covers. The voting pool at
N=64 and at N=4 can differ, and that is the whole point.

## Figures

A figure is an image and its plotted quantities are not readable from the
bytes, so a figure is published with a sidecar manifest, `<figure>.manifest.json`,
declaring each panel and what it plots. A figure with no manifest **fails**
rather than passing unexamined, on the same reasoning as the leakage check: no
hits and no evidence are different claims.
"""

from __future__ import annotations

import re
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from argmax.errors import ArgmaxError

FIGURE_SUFFIXES = frozenset({".png", ".svg", ".pdf"})
TABLE_SUFFIXES = frozenset({".parquet", ".json", ".jsonl"})


class AccuracyUnpaired(ArgmaxError):
    """A published accuracy has no answer rate beside it."""


def is_accuracy_key(name: str) -> bool:
    """`accuracy` as an underscore-separated token anywhere in the name.

    Doc 4 s9.1 first said "named `accuracy` or ending in `_accuracy`" and then
    listed `accuracy_under_strategy` as in scope, which that rule excludes. The
    token rule covers every example the doc names, and the doc was corrected to
    match rather than the example dropped.
    """
    return "accuracy" in str(name).lower().split("_")


def is_rate_key(name: str) -> bool:
    return "answer_rate" in str(name).lower()


def _is_per_n(value: Any) -> bool:
    """A mapping from grid point to value, however JSON mangled the keys."""
    if not isinstance(value, dict) or not value:
        return False
    try:
        [int(k) for k in value]
    except (TypeError, ValueError):
        return False
    return True


def _grid(value: dict) -> set[int]:
    return {int(k) for k in value}


@dataclass
class PairingReport:
    n_artifacts: int = 0
    n_in_scope: int = 0
    problems: list[str] = field(default_factory=list)
    unscanned: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.problems and not self.unscanned

    def summary(self) -> str:
        lines = [
            f"answer-rate pairing: {self.n_artifacts} artifacts, "
            f"{self.n_in_scope} carrying an accuracy"
        ]
        lines.extend(f"  UNPAIRED: {p}" for p in self.problems)
        lines.extend(f"  UNSCANNED: {p}: {why}" for p, why in self.unscanned)
        if self.clean and self.n_in_scope:
            lines.append("  every accuracy carries its rate")
        return "\n".join(lines)


def check_mapping(record: dict[str, Any], where: str) -> list[str]:
    """One row, one panel, or one flat record."""
    accuracies = {k: v for k, v in record.items() if is_accuracy_key(k)}
    if not accuracies:
        return []

    rates = {k: v for k, v in record.items() if is_rate_key(k)}
    if not rates:
        return [f"{where}: {sorted(accuracies)} with no answer_rate beside it"]

    problems: list[str] = []
    per_n_rates = {k: v for k, v in rates.items() if _is_per_n(v)}
    for name, value in accuracies.items():
        if not _is_per_n(value):
            continue
        wanted = _grid(value)
        covered: set[int] = set()
        for rate in per_n_rates.values():
            covered |= _grid(rate)
        missing = sorted(wanted - covered)
        if missing:
            problems.append(
                f"{where}: {name} is per N but no answer_rate covers N={missing}"
            )
    return problems


def check_rows(rows: Iterable[dict[str, Any]], where: str) -> list[str]:
    problems: list[str] = []
    for i, row in enumerate(rows):
        problems.extend(check_mapping(row, f"{where}[{i}]"))
    return problems


def _read_table(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".parquet":
        import polars as pl

        return pl.read_parquet(path).to_dicts()
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, list):
        return [row for row in loaded if isinstance(row, dict)]
    return [loaded]


def _panels(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    panels = manifest.get("panels")
    if isinstance(panels, list):
        return [p for p in panels if isinstance(p, dict)]
    return [manifest]


def check_file(path: Path, report: PairingReport) -> None:
    report.n_artifacts += 1

    if path.suffix in FIGURE_SUFFIXES:
        manifest = path.with_suffix(path.suffix + ".manifest.json")
        if not manifest.exists():
            report.unscanned.append(
                (
                    path,
                    "figure has no sidecar manifest; what it plots cannot be "
                    "read from the image, so the pairing cannot be checked",
                )
            )
            return
        document = json.loads(manifest.read_text(encoding="utf-8"))
        panels = _panels(document)
        if any(any(is_accuracy_key(k) for k in panel) for panel in panels):
            report.n_in_scope += 1
        report.problems.extend(check_rows(panels, str(path)))
        return

    if path.suffix not in TABLE_SUFFIXES:
        report.unscanned.append((path, f"unreadable artifact format ({path.suffix})"))
        return

    try:
        rows = _read_table(path)
    except (OSError, ValueError) as exc:
        report.unscanned.append((path, f"unreadable: {exc}"))
        return

    if any(any(is_accuracy_key(k) for k in row) for row in rows):
        report.n_in_scope += 1
    report.problems.extend(check_rows(rows, str(path)))


def iter_artifacts(root: Path) -> Iterator[Path]:
    """Published artifacts under `root`.

    Hidden files are not artifacts. `.gitkeep` holds an empty directory open in
    git and publishes nothing, so treating it as an unreadable artifact would
    fail the check on a repository that has published nothing at all.
    """
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name.endswith(".manifest.json"):
            continue  # checked with the figure it belongs to
        yield path


def scan(roots: Iterable[Path]) -> PairingReport:
    report = PairingReport()
    for root in roots:
        if root.is_dir():
            for path in iter_artifacts(root):
                check_file(path, report)
        elif root.exists():
            check_file(root, report)
    return report


def assert_paired(report: PairingReport) -> None:
    """Refuse to publish. Absence fails; it does not warn."""
    if report.clean:
        return
    raise AccuracyUnpaired(
        "an accuracy is published without the answer rate that qualifies it.\n"
        + report.summary()
        + "\n\nSee doc 4 s4.1: the pool that votes at a token cap is not a "
        "random subset of the pool that was drawn. Publish the rate beside "
        "the accuracy, including when it reads 1.0000."
    )


# --- markdown tables in notes and docs --------------------------------------
#
# The rule above was written for published artifacts, where "what counts as an
# accuracy" is decidable from a key name. It did not cover markdown, and a
# quintile table of per-problem accuracies was published in a note without its
# answer rates for exactly that reason: the discipline existed, the check did
# not reach where the number actually lived.
#
# Doc 4 s9.1 now says the rule covers notes. This is the part that makes that
# enforceable rather than aspirational.

_MD_ACCURACY = re.compile(r"(?<![a-z_])accurac(?:y|ies)(?![a-z_])", re.IGNORECASE)
_MD_RATE = re.compile(r"answer[ _]rate", re.IGNORECASE)


def _md_cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def iter_markdown_tables(text: str):
    """Yield (line_number, header_cells, body_rows) for each pipe table."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        is_header = lines[i].strip().startswith("|")
        has_rule = i + 1 < len(lines) and set(lines[i + 1].strip()) <= set("|-: ")
        if is_header and has_rule and lines[i + 1].strip():
            header = _md_cells(lines[i])
            j = i + 2
            body = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                body.append(_md_cells(lines[j]))
                j += 1
            yield i + 1, header, body
            i = j
        else:
            i += 1


def _column_holds_accuracies(body: list[list[str]], index: int) -> bool:
    """True when the column's cells are numbers that could be accuracies.

    This is what separates a column REPORTING accuracies from one that merely
    labels rows by accuracy, such as an `accuracy bin` column whose cells read
    "0.000 to 0.125". A bin label is a stratifier; it is not a number that can
    travel without its answer rate, so it is out of scope.

    Bold and backtick markup is stripped. A column needs at least one parseable
    value in the unit interval and no cell that parses outside it.
    """
    seen = False
    for row in body:
        if index >= len(row):
            continue
        cell = row[index].strip().strip("*`").strip()
        if not cell:
            continue
        percent = cell.endswith("%")
        try:
            # The WHOLE cell must be one number. "0.000 to 0.125" is a bin
            # label, not an accuracy, and taking its first token would read it
            # as one.
            value = float(cell.removesuffix("%"))
        except ValueError:
            return False
        if percent:
            value /= 100.0
        if not 0.0 <= value <= 1.0:
            return False
        seen = True
    return seen


def check_markdown(path: Path, report: PairingReport) -> None:
    """Fail any markdown table with an accuracy column and no answer rate.

    Matching is per table, not per file: a rate elsewhere in the document is
    not a match, for the same reason a rate in another file is not. The number
    has to be readable without the reader performing a join.
    """
    text = path.read_text(encoding="utf-8")
    for line_no, header, body in iter_markdown_tables(text):
        columns = [
            i
            for i, cell in enumerate(header)
            if _MD_ACCURACY.search(cell) and _column_holds_accuracies(body, i)
        ]
        if not columns:
            continue
        report.n_artifacts += 1
        report.n_in_scope += 1
        blob = " ".join(header) + " " + " ".join(c for row in body for c in row)
        if not _MD_RATE.search(blob):
            named = ", ".join(header[i] or f"column {i}" for i in columns)
            report.problems.append(
                f"{path}:{line_no}: table reports accuracies ({named}) with no "
                f"answer_rate in the same table"
            )


def iter_markdown(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.md")):
        if path.is_file():
            yield path


# --- LaTeX tables ------------------------------------------------------------
#
# The markdown scanner reads pipe tables. A manuscript ported to LaTeX carries
# the same accuracies in `tabular` environments, which that scanner cannot see
# at all: extending the walk to `.tex` without this would have reported clean
# coverage over a file whose tables were never parsed.

_TEX_TABULAR = re.compile(r"\\begin\{tabular\}(.*?)\\end\{tabular\}", re.DOTALL)


def _tex_rows(body: str) -> list[list[str]]:
    rows = []
    for raw in body.split(r"\\"):
        line = re.sub(r"\\(toprule|midrule|bottomrule|hline)\b", "", raw).strip()
        if not line:
            continue
        cells = []
        for cell in line.split("&"):
            cell = re.sub(r"\\(textbf|emph|texttt|mathrm|text)\{([^}]*)\}", r"\2", cell)
            cell = cell.replace("\\%", "%").replace("$", "").replace("{", "").replace("}", "")
            cells.append(cell.strip())
        rows.append(cells)
    return rows


def check_latex(path: Path, report: PairingReport) -> None:
    """Fail any LaTeX tabular with an accuracy column and no answer rate."""
    text = path.read_text(encoding="utf-8")
    for match in _TEX_TABULAR.finditer(text):
        rows = _tex_rows(match.group(1))
        if len(rows) < 2:
            continue
        header, body = rows[0], rows[1:]
        columns = [
            i
            for i, cell in enumerate(header)
            if _MD_ACCURACY.search(cell) and _column_holds_accuracies(body, i)
        ]
        if not columns:
            continue
        report.n_artifacts += 1
        report.n_in_scope += 1
        # a LaTeX table's caption sits outside the tabular; allow the enclosing
        # table environment to carry the rate, which is where a caption lives
        start = text.rfind(r"\begin{table}", 0, match.start())
        end = text.find(r"\end{table}", match.end())
        scope = text[start if start != -1 else match.start(): end if end != -1 else match.end()]
        if not _MD_RATE.search(scope):
            named = ", ".join(header[i] or f"column {i}" for i in columns)
            line_no = text[: match.start()].count("\n") + 1
            report.problems.append(
                f"{path}:{line_no}: LaTeX table reports accuracies ({named}) with "
                f"no answer_rate in the table or its caption"
            )
