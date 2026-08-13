"""Derived tables: a pure function of raw, and the only place extraction runs.

Doc 4 principle 3, nothing is derived-only, and its corollary that nobody says
out loud: nothing may be derived TWICE either. The answer rate is what the
whole comparability argument against the published numbers rests on, so it has
to come out of the code path `tests/test_recompute.py` covers, not out of a
second implementation that happens to agree today.

Deterministic and idempotent. Rows are sorted by a total order over
(split, benchmark, model_slug, problem_id, sample_index) before writing, so
deleting `data/derived/` and rebuilding reproduces the same bytes.

What it adds to each raw record:

  - `extracted_answer`, `extraction_pass`, `answer_span_chars`: the copied
    ladder, run offline over stored `raw_text`, never in the sampler
  - `answer_span_tokens`: that span mapped onto the stored logprob array, which
    is the field doc 4 s3.6 calls the one that makes margin analysis possible
  - `answer_margin`, `answer_margin_censored`, `answer_margin_k`: the margin
    against the runner-up option, with the censoring rule, never imputed
  - `is_correct`: null when no answer was extracted, never coerced to false
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from argmax.analysis.gates import answer_margin_vs_runner_up
from argmax.config import DATA
from argmax.extract.ladder import (
    EXTRACTOR_VERSION,
    char_span_to_token_span,
    extract,
    top_alternatives_at,
)

LETTERS = "ABCD"
DERIVED = DATA / "derived"


def _iter_raw(root: Path):
    for path in sorted(root.rglob("*.jsonl.gz")) + sorted(root.rglob("*.jsonl")):
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield path, json.loads(line)


def derive_row(record: dict[str, Any], n_options: int = 4) -> dict[str, Any]:
    """One raw record to one derived row. Pure."""
    e = extract(record["raw_text"], n_options)
    token_span = char_span_to_token_span(
        record.get("logprobs_raw"), e.answer_span_chars
    )

    margin = None
    censored = None
    k = None
    if token_span is not None:
        alternatives = top_alternatives_at(record.get("logprobs_raw"), token_span[0])
        if alternatives:
            m = answer_margin_vs_runner_up(alternatives, LETTERS[:n_options])
            margin, censored, k = m.value, m.censored, m.k

    correct_letter = record.get("correct_option")
    is_correct = (
        None
        if e.extracted_answer is None or correct_letter is None
        else e.extracted_answer == correct_letter
    )

    return {
        "sample_key": record["sample_key"],
        "run_id": record["run_id"],
        "split": record["split"],
        "benchmark": record["benchmark"],
        "problem_id": record["problem_id"],
        "sample_index": record["sample_index"],
        "model_requested": record["model_requested"],
        "param_hash": record["param_hash"],
        "max_tokens": record["max_tokens"],
        "finish_reason": record["finish_reason"],
        "truncated": record["truncated"],
        "hit_ceiling": record["hit_ceiling"],
        "outcome_class": record["outcome_class"],
        "completion_tokens": (record.get("usage_raw") or {}).get("completion_tokens"),
        "prompt_tokens": (record.get("usage_raw") or {}).get("prompt_tokens"),
        "cost_usd_est": record["cost_usd_est"],
        "extractor_version": EXTRACTOR_VERSION,
        "extraction_pass": e.extraction_pass,
        "extracted_answer": e.extracted_answer,
        "answer_span_chars": list(e.answer_span_chars) if e.answer_span_chars else None,
        "answer_span_tokens": list(token_span) if token_span else None,
        "answer_margin": margin,
        "answer_margin_censored": censored,
        "answer_margin_k": k,
        "is_correct": is_correct,
    }


def build(raw_root: Path | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    """Rebuild every derived table from raw. Deterministic and idempotent."""
    raw_root = raw_root or (DATA / "raw")
    out_dir = out_dir or DERIVED
    out_dir.mkdir(parents=True, exist_ok=True)

    # Ground truth lives in the canonicalized problem set, not in the raw
    # record: doc 3 s5 keeps answer keys out of the sample store along with the
    # question text. Joined here when the gated source is present, and left
    # null when it is not, so `is_correct` is absent rather than invented.
    truth: dict[str, str] = {}
    try:
        from argmax.datasets.gpqa import load_problems

        truth = {p.problem_id: p.correct_option for p in load_problems()}
    except (FileNotFoundError, ImportError):
        pass

    rows = [
        derive_row(record | {"correct_option": truth.get(record["problem_id"])})
        for _, record in _iter_raw(raw_root)
    ]
    rows.sort(
        key=lambda r: (
            r["split"],
            r["benchmark"],
            r["model_requested"],
            r["param_hash"],
            r["problem_id"],
            r["sample_index"],
        )
    )

    # JSON Lines, per doc 2 s5.4, which now specifies the format and the
    # reason: Parquet cannot be byte-identical across builds, and
    # byte-identical also catches nondeterministic row ordering.
    path = out_dir / "samples.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")

    answered = sum(1 for r in rows if r["extracted_answer"] is not None)
    summary = {
        "n_rows": len(rows),
        "n_answered": answered,
        "answer_rate": answered / len(rows) if rows else None,
        "n_margin_measured": sum(
            1
            for r in rows
            if r["answer_margin"] is not None and not r["answer_margin_censored"]
        ),
        "n_margin_censored": sum(1 for r in rows if r["answer_margin_censored"]),
        "n_scored": sum(1 for r in rows if r["is_correct"] is not None),
        "accuracy_over_scored": (
            sum(1 for r in rows if r["is_correct"])
            / sum(1 for r in rows if r["is_correct"] is not None)
            if any(r["is_correct"] is not None for r in rows)
            else None
        ),
        "extractor_version": EXTRACTOR_VERSION,
        "path": str(path),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary
