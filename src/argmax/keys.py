"""Content-derived identifiers.

Everything here is a pure function of content, never of row order or wall
clock. Row order changes when a dataset is re-released; an id that depends on
it silently repoints at a different problem.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

_ENC = "utf-8"


def _sha(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode(_ENC))
        h.update(b"\x00")  # unambiguous separator; "ab"+"c" != "a"+"bc"
    return h.hexdigest()


def canonical_json(obj: Any) -> str:
    """Stable serialization for hashing: sorted keys, no incidental whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def param_hash(params: dict[str, Any]) -> str:
    """Hash over the FULL parameter set.

    This lands in the storage path so that a parameter change cannot
    contaminate an existing sample set. Cheap insurance against the single
    most common silent-corruption mode in this kind of pipeline.
    """
    return _sha(canonical_json(params))


def sample_key(
    model_string: str,
    param_hash_: str,
    benchmark: str,
    problem_id: str,
    sample_index: int,
) -> str:
    """The idempotency key.

    Before issuing a call the sampler consults an index of existing keys and
    skips. Resume is "run the same command again".
    """
    return _sha(model_string, param_hash_, benchmark, problem_id, str(sample_index))


def problem_id(benchmark: str, content: str) -> str:
    """Stable across dataset re-releases: a function of content, not row order."""
    return _sha(benchmark, content)[:32]


def problem_hash(canonical_problem: dict[str, Any]) -> str:
    """Includes the FROZEN option order.

    Majority voting is over option letters. If option order shuffles between
    runs the letters mean different things and the stored votes silently
    become incomparable.
    """
    return _sha(canonical_json(canonical_problem))


def dataset_version_hash(problem_hashes: list[str]) -> str:
    """Hash over the canonicalized problem set. A changed hash invalidates
    comparison, so it is stored in every manifest."""
    return _sha(canonical_json(sorted(problem_hashes)))


def prompt_hash(prompt_text: str) -> str:
    """Prompt TEXT is never stored: it contains question and option text.

    See files/03-security-and-access.md section 5.
    """
    return _sha(prompt_text)


def subsample_seed(problem_id_: str, model_slug: str, n: int, replicate: int) -> int:
    """Seed derived from content so results are reproducible and independent of
    iteration order."""
    digest = _sha(problem_id_, model_slug, str(n), str(replicate))
    return int(digest[:16], 16)


#: Human-readable statement of the recipe above, stored in the ProblemRecord so
#: a reader does not have to find this function to know how seeds were made.
SEED_RECIPE = "sha256(problem_id, model_slug, N, replicate)[:16] as int"
