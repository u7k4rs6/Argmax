"""The only module that reads TOGETHER_API_KEY.

OpenAI-compatible chat completions. Two invariants:

  1. `n = 1` per request, ALWAYS. Requesting n>1 returns one aggregated
     `usage` block for the whole batch, which destroys per-sample token
     accounting. Per-sample tokens are the entire point of Step 0 and the
     entire basis of the cost model. The extra request overhead is worth it.

  2. The full response object is retained. Fields the provider adds later are
     then already captured. Selecting fields at write time is how the
     predecessor permanently lost final-answer margin analysis.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

from argmax.sampling.ratelimit import RetryPolicy, TokenBucket
from argmax.sampling.redact import install_redaction_filter, scrub

log = logging.getLogger(__name__)


@dataclass
class Response:
    """What one request returned, verbatim plus timing."""

    ok: bool
    status: int | None
    body: dict[str, Any]
    latency_ms: int
    attempt_count: int
    error_type: str | None = None
    error_message: str | None = None


class Client:
    def __init__(
        self,
        *,
        rate_per_sec: float = 2.0,
        retry: RetryPolicy | None = None,
        timeout_s: float = 600.0,
    ) -> None:
        load_dotenv()
        install_redaction_filter()

        key = os.environ.get("TOGETHER_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "TOGETHER_API_KEY is not set. Copy .env.example to .env and "
                "fill it in. Use a DEDICATED Argmax key, not the key used "
                "with self-consistency-backfire."
            )
        self._base_url = os.environ.get(
            "TOGETHER_BASE_URL", "https://api.together.xyz/v1"
        ).rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        self._bucket = TokenBucket(rate_per_sec)
        self._retry = retry or RetryPolicy()
        self._client = httpx.Client(timeout=timeout_s)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def complete(self, payload: dict[str, Any]) -> Response:
        """Issue one chat completion. Never batches."""
        if payload.get("n", 1) != 1:
            raise ValueError(
                "n must be 1: n>1 returns one aggregated usage block for the "
                "whole batch, destroying per-sample token accounting"
            )

        url = f"{self._base_url}/chat/completions"
        attempt = 0
        started = time.monotonic()

        while True:
            attempt += 1
            self._bucket.acquire()
            status: int | None = None
            retry_after: float | None = None
            try:
                r = self._client.post(url, headers=self._headers, json=payload)
                status = r.status_code
                if r.is_success:
                    return Response(
                        ok=True,
                        status=status,
                        body=r.json(),
                        latency_ms=int((time.monotonic() - started) * 1000),
                        attempt_count=attempt,
                    )
                err_type, err_msg = f"http_{status}", scrub(r.text[:2000])
                try:
                    retry_after = float(r.headers["Retry-After"])
                except (KeyError, ValueError):
                    retry_after = None
            except Exception as exc:  # noqa: BLE001
                # Re-raise nothing raw: an httpx exception repr can carry the
                # request object, and the request object carries the header.
                err_type, err_msg = type(exc).__name__, scrub(str(exc))

            if not self._retry.should_retry(status, attempt):
                log.warning("request failed permanently: %s", err_type)
                return Response(
                    ok=False,
                    status=status,
                    body={},
                    latency_ms=int((time.monotonic() - started) * 1000),
                    attempt_count=attempt,
                    error_type=err_type,
                    error_message=err_msg,
                )

            delay = self._retry.delay_s(attempt, retry_after)
            log.info("retrying after %.1fs (attempt %d, %s)", delay, attempt, err_type)
            time.sleep(delay)


def build_payload(
    *,
    model_string: str,
    prompt: str,
    max_tokens: int,
    temperature: float | None,
    top_p: float | None,
    seed: int | None,
    stop: list[str],
    logprobs_depth: int | None,
    logprobs_style: str = "integer_depth",
) -> dict[str, Any]:
    """Assemble a request body.

    `max_tokens` is required with no default: truncation must be a controlled
    variable, not a provider default. `stop` defaults to empty because a stop
    sequence silently truncates the answer and looks like a short completion.

    ## Two spellings of the same request, and why the default is not OpenAI's

    Together's chat-completions reference documents `logprobs` as **an integer
    between 0 and 20**, "of the top k tokens to return log probabilities for at
    each generation step, instead of only the sampled token". `top_logprobs`
    appears there only as a RESPONSE field. OpenAI spells the same request as
    `logprobs: true` plus `top_logprobs: k`.

    Sending the OpenAI spelling to Together gets `logprobs: true`, which is not
    an integer depth, and the alternatives the margin gate needs do not come
    back. The failure is silent: a depth-1 response is well formed, so a probe
    written the OpenAI way would report "logprobs unsupported at depth" when
    what actually happened is that the depth was never requested.

    `logprobs_style` therefore travels with the model config rather than being
    assumed, and the capability probe records what came back either way.
    """
    payload: dict[str, Any] = {
        "model": model_string,
        "messages": [{"role": "user", "content": prompt}],
        "n": 1,
        "max_tokens": max_tokens,
        "stop": stop,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if seed is not None:
        payload["seed"] = seed  # sent and recorded, never relied upon
    if logprobs_depth is not None:
        if logprobs_style == "integer_depth":
            payload["logprobs"] = int(logprobs_depth)
        elif logprobs_style == "openai":
            payload["logprobs"] = True
            payload["top_logprobs"] = int(logprobs_depth)
        else:
            raise ValueError(
                f"unknown logprobs_style {logprobs_style!r}; "
                "expected 'integer_depth' (Together) or 'openai'"
            )
    return payload
