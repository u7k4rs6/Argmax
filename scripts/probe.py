#!/usr/bin/env python
"""Capability probe: one sample per model, before any phase spends.

Thin wrapper. All logic is in src/argmax/sampling/probe.py.

PAID: issues exactly one request.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

from argmax.config import load_model, require
from argmax.errors import ArgmaxError
from argmax.keys import param_hash
from argmax.sampling.client import Client, build_payload
from argmax.sampling.probe import Capabilities, inspect_response, save_capabilities
from argmax.sampling.spend import SpendGuard

PROBE_PROMPT = (
    "Answer with a single letter.\n\n"
    "Which of these is a prime number?\n"
    "A) 4\nB) 6\nC) 7\nD) 9\n"
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="model_slug from configs/models/")
    args = ap.parse_args()

    cfg = load_model(args.model)
    params = cfg["params"]
    source = cfg["_source"]

    # Constructing the guard raises if ARGMAX_SPEND_CEILING_USD is unset.
    SpendGuard()

    payload = build_payload(
        model_string=require(cfg["model_string"], "model_string", source),
        prompt=PROBE_PROMPT,
        max_tokens=require(params["max_tokens"], "max_tokens", source),
        temperature=params.get("temperature"),
        top_p=params.get("top_p"),
        seed=params.get("seed"),
        stop=params.get("stop") or [],
        logprobs_depth=params.get("logprobs_depth"),
        logprobs_style=params.get("logprobs_style", "integer_depth"),
    )

    with Client(rate_per_sec=1.0) as client:
        response = client.complete(payload)

    if not response.ok:
        # A refusal is a capability finding, not an absent one. It is written
        # to the same file a success would write, so a phase that requires this
        # model refuses to start with a reason instead of a missing file.
        caps = Capabilities(
            capabilities_id=param_hash(
                {"slug": args.model, "error": response.error_type}
            )[:16],
            model_slug=args.model,
            model_requested=cfg["model_string"],
            model_returned="",
            probed_utc=datetime.now(UTC).isoformat(),
            available=False,
            unavailable_reason=f"{response.error_type}: {response.error_message}",
            logprobs_depth_requested=params.get("logprobs_depth"),
            logprobs_style_requested=params.get("logprobs_style", "integer_depth"),
        )
        path = save_capabilities(caps)
        print(
            f"probe failed: {response.error_type}: {response.error_message}",
            file=sys.stderr,
        )
        print(f"wrote {path} recording the model as unavailable", file=sys.stderr)
        return 1

    found = inspect_response(response.body)
    caps = Capabilities(
        capabilities_id=param_hash(
            {"slug": args.model, "body_keys": sorted(response.body)}
        )[:16],
        model_slug=args.model,
        model_requested=cfg["model_string"],
        probed_utc=datetime.now(UTC).isoformat(),
        logprobs_depth_requested=params.get("logprobs_depth"),
        logprobs_style_requested=params.get("logprobs_style", "integer_depth"),
        **found,
    )
    path = save_capabilities(caps)

    delimiter = caps.reasoning_delimiter or ""
    print(f"wrote {path}")
    print(f"  model returned      : {caps.model_returned}")
    depth = caps.logprobs_depth
    print(f"  logprobs            : {caps.logprobs_returned} (depth {depth})")
    print(f"  usage fields        : {', '.join(caps.usage_fields) or 'none'}")
    print(f"  reasoning delivery  : {caps.reasoning_delivery} {delimiter}")
    print(f"  reasoning token fld : {caps.reasoning_token_field or 'none'}")
    print(f"  finish_reason       : {caps.finish_reason_present}")
    if caps.model_returned and caps.model_returned != caps.model_requested:
        print(
            f"  WARNING: requested {caps.model_requested!r} but the API "
            f"returned {caps.model_returned!r}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ArgmaxError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
