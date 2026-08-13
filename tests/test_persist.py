"""Raw storage is append-only and tolerant of an interrupted write.

The long-run failure this defends against: a run is killed mid-write, and the
partial trailing line either crashes the reader or gets "repaired" into
something that is no longer what the API returned.
"""

from __future__ import annotations

import gzip
import json

from argmax.persist.paths import raw_path
from argmax.persist.reader import existing_sample_keys, read_samples
from argmax.persist.writer import append_sample
from argmax.sampling.ledger import Ledger, PricingSnapshot
from argmax.schema import Sample
from tests.conftest import make_sample_dict


def test_roundtrip(tmp_path):
    path = tmp_path / "p.jsonl.gz"
    s = Sample.model_validate(make_sample_dict())
    append_sample(path, s)
    back, report = read_samples(path)
    assert report.clean
    assert back == [s]


def test_append_does_not_rewrite(tmp_path):
    path = tmp_path / "p.jsonl.gz"
    for i in range(3):
        append_sample(path, Sample.model_validate(make_sample_dict(sample_index=i)))
    back, report = read_samples(path)
    assert [s.sample_index for s in back] == [0, 1, 2]
    assert report.n_ok == 3


def test_corrupt_trailing_line_is_reported_not_repaired(tmp_path):
    """Tolerated by the reader and REPORTED, not repaired."""
    path = tmp_path / "p.jsonl.gz"
    append_sample(path, Sample.model_validate(make_sample_dict(sample_index=0)))
    with gzip.open(path, "at", encoding="utf-8") as fh:
        fh.write('{"sample_key": "truncated mid-wr')

    before = path.read_bytes()
    back, report = read_samples(path)

    assert len(back) == 1
    assert report.n_corrupt == 1
    assert report.corrupt_line_numbers == [2]
    assert not report.clean
    assert path.read_bytes() == before, "the reader must not modify the file"


def test_existing_keys_drive_resume(tmp_path):
    path = tmp_path / "p.jsonl.gz"
    keys = set()
    for i in range(2):
        s = Sample.model_validate(make_sample_dict(sample_index=i, sample_key=f"k{i}"))
        append_sample(path, s)
        keys.add(f"k{i}")
    assert existing_sample_keys(path) == keys


def test_param_hash_is_in_the_path():
    """A parameter change cannot contaminate an existing sample set."""
    a = raw_path("exploratory", "b", "m", "hash_a", "p1")
    b = raw_path("exploratory", "b", "m", "hash_b", "p1")
    assert a != b
    assert "hash_a" in a.parts and "hash_b" in b.parts


def test_splits_are_separate_trees():
    """Not a boolean flag: separate directory trees."""
    e = raw_path("exploratory", "b", "m", "h", "p1")
    c = raw_path("confirmatory", "b", "m", "h", "p1")
    assert e.parts[:-1] != c.parts[:-1]


def test_realized_spend_sums_the_ledger(tmp_path):
    ledger = Ledger(path=tmp_path / "ledger.jsonl")
    pricing = PricingSnapshot("snap", "2026-01-01", 1.0, 3.0)
    for i in range(3):
        ledger.record(
            sample_key=f"k{i}",
            run_id="r",
            model_slug="m",
            usage_raw={"prompt_tokens": 1000, "completion_tokens": 1000},
            pricing=pricing,
            cost_usd=0.5,
            timestamp_utc="2026-01-01T00:00:00+00:00",
        )
    assert ledger.realized_spend_usd() == 1.5


def test_ledger_skips_a_corrupt_trailing_line(tmp_path):
    ledger = Ledger(path=tmp_path / "ledger.jsonl")
    ledger.path.write_text(
        json.dumps({"cost_usd": 1.0}) + "\n" + '{"cost_usd": 2.', encoding="utf-8"
    )
    assert ledger.realized_spend_usd() == 1.0


def test_cost_is_derived_from_the_usage_block():
    pricing = PricingSnapshot("snap", "2026-01-01", 1.0, 2.0)
    cost = pricing.cost_usd({"prompt_tokens": 1_000_000, "completion_tokens": 500_000})
    assert cost == 1.0 + 1.0
