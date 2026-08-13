"""The capability probe.

New component, no predecessor. Runs before any phase, costs approximately one
sample per model, and writes configs/models/<slug>.capabilities.json.

It records what the provider ACTUALLY returns for that model, rather than what
the documentation says it returns. The sampler then refuses to start a phase
whose instrumentation requirements exceed the recorded capabilities.

This is the direct fix for the predecessor's permanent loss of final-answer
margin analysis: that hole was discovered at analysis time, after the samples
were paid for. A probe costs one sample.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from argmax.config import CONFIGS
from argmax.errors import CapabilityMissing

#: Delimiter pairs seen in the wild for inline reasoning. Detection is
#: recorded, never assumed.
REASONING_DELIMITERS = [
    ("<think>", "</think>"),
    ("<reasoning>", "</reasoning>"),
    ("<|begin_of_thought|>", "<|end_of_thought|>"),
]


@dataclass
class Capabilities:
    capabilities_id: str
    model_slug: str
    model_requested: str
    model_returned: str
    probed_utc: str

    #: False when the provider refused to serve the model at all. Recorded
    #: rather than left as a failed exit code: doc 4 principle 5, absence is
    #: data. The predecessor lost a phase to exactly this and the fact survives
    #: only in a script comment. A model that cannot be called is a capability
    #: finding, and the phase that wanted it needs to see it.
    available: bool = True
    unavailable_reason: str | None = None

    logprobs_returned: bool = False
    logprobs_depth: int | None = None  # alternatives per token that came back
    logprobs_container_key: str | None = None  # "content", "tokens", or absent
    logprobs_keys: list[str] = field(default_factory=list)
    logprobs_first_entry_raw: object = None  # verbatim, for checking the reading
    logprobs_first_alternatives_raw: object = None  # the alternatives, verbatim
    logprobs_depth_requested: int | None = None
    logprobs_style_requested: str | None = None
    usage_fields: list[str] = field(default_factory=list)
    reasoning_token_field: str | None = None  # path within usage, if any
    reasoning_delivery: str = "none"  # api_field | delimiter | none
    reasoning_delimiter: list[str] | None = None
    #: None means unknown, and unknown is the honest value: one call cannot
    #: establish that a seed was honoured, and hosted inference is
    #: non-deterministic across batching and hardware even at a fixed seed
    #: (doc 2 s7). It was previously defaulted to False, which reads as a
    #: measurement that nothing performed.
    seed_accepted: bool | None = None
    finish_reason_present: bool = False
    response_extra_fields: list[str] = field(default_factory=list)

    def provides(self, requirement: str) -> bool:
        if not self.available:
            return False  # an unreachable model provides nothing
        return {
            "logprobs": self.logprobs_returned,
            "usage_raw": bool(self.usage_fields),
            "finish_reason": self.finish_reason_present,
            "reasoning_tokens": self.reasoning_token_field is not None,
            "reasoning_split": self.reasoning_delivery != "none",
            # Unknown does not provide. A phase that requires a honoured seed
            # must not start on the strength of a field nobody measured.
            "seed": bool(self.seed_accepted),
        }.get(requirement, False)


def inspect_response(body: dict[str, Any]) -> dict[str, Any]:
    """Read a raw completion body and report what it actually contains."""
    choice = (body.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = body.get("usage") or {}

    logprobs = choice.get("logprobs") or {}
    container = (
        "content"
        if logprobs.get("content")
        else "tokens"
        if logprobs.get("tokens")
        else None
    )
    content = logprobs.get("content") or logprobs.get("tokens") or []

    # Depth 0 and depth unknown are different findings. Zero means the response
    # carried per-token logprobs with no alternatives beside them, which is the
    # answer that kills the margin gate. None means the shape was not one this
    # function knows how to read, which is a reason to look at the verbatim
    # record rather than to conclude anything.
    #
    # Two shapes exist and they nest differently. OpenAI puts one dict per
    # token in `content`, each carrying its own `top_logprobs` list. Together
    # returns PARALLEL ARRAYS: `tokens`, `token_logprobs`, `token_ids` and a
    # sibling `top_logprobs` whose i-th entry holds the alternatives for the
    # i-th token. Reading the OpenAI nesting against a Together response finds
    # a bare string where it expects a dict and concludes depth 0, which is the
    # false negative this probe exists to prevent: it reports "no alternatives"
    # when the alternatives are one key to the left.
    parallel = logprobs.get("top_logprobs")
    depth: int | None = None
    first_alternatives = None
    if content and isinstance(content[0], dict):
        alternatives = content[0].get("top_logprobs") or []
        depth = len(alternatives)
        first_alternatives = alternatives
    elif isinstance(parallel, list) and parallel:
        first_alternatives = parallel[0]
        if isinstance(first_alternatives, dict | list):
            depth = len(first_alternatives)
        else:
            depth = None  # present but unreadable; the verbatim record decides
    elif content:
        depth = 0

    text = message.get("content") or ""
    delivery, delimiter = "none", None
    if message.get("reasoning") or message.get("reasoning_content"):
        delivery = "api_field"
    else:
        for open_d, close_d in REASONING_DELIMITERS:
            if open_d in text:
                delivery, delimiter = "delimiter", [open_d, close_d]
                break

    reasoning_field = None
    if "reasoning_tokens" in usage:
        reasoning_field = "usage.reasoning_tokens"
    elif "reasoning_tokens" in (usage.get("completion_tokens_details") or {}):
        reasoning_field = "usage.completion_tokens_details.reasoning_tokens"

    known_top = {
        "id",
        "object",
        "created",
        "model",
        "choices",
        "usage",
        "system_fingerprint",
    }

    return {
        "model_returned": body.get("model", ""),
        "logprobs_returned": bool(content),
        "logprobs_depth": depth,
        "logprobs_container_key": container,
        "logprobs_keys": sorted(logprobs.keys()),
        # Verbatim, so a depth reading that looks wrong can be checked against
        # what the provider actually sent rather than against this parser.
        "logprobs_first_entry_raw": content[0] if content else None,
        "logprobs_first_alternatives_raw": first_alternatives,
        "usage_fields": sorted(usage.keys()),
        "reasoning_token_field": reasoning_field,
        "reasoning_delivery": delivery,
        "reasoning_delimiter": delimiter,
        "finish_reason_present": choice.get("finish_reason") is not None,
        "response_extra_fields": sorted(set(body.keys()) - known_top),
    }


def capabilities_path(slug: str) -> Path:
    return CONFIGS / "models" / f"{slug}.capabilities.json"


def load_capabilities(slug: str) -> Capabilities:
    path = capabilities_path(slug)
    if not path.exists():
        raise CapabilityMissing(
            f"no capability probe for {slug}. Run `make probe MODEL={slug}` "
            "before any phase that uses it."
        )
    return Capabilities(**json.loads(path.read_text(encoding="utf-8")))


def save_capabilities(caps: Capabilities) -> Path:
    path = capabilities_path(caps.model_slug)
    path.write_text(
        json.dumps(asdict(caps), indent=2, sort_keys=True), encoding="utf-8"
    )
    return path


def assert_phase_supported(slug: str, requirements: list[str]) -> None:
    """Refuse to start a phase whose instrumentation the model cannot deliver.

    Checked before spending, which is the whole point.
    """
    caps = load_capabilities(slug)
    missing = [r for r in requirements if not caps.provides(r)]
    if missing:
        raise CapabilityMissing(
            f"{slug} does not provide {missing}; required by this phase. "
            f"Capability probe: {capabilities_path(slug)}"
        )
