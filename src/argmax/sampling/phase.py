"""The loop that spends money.

Separate from `runner.py`, which holds the preconditions, so that the refusals
stay importable and testable on a host with no network and no key.

## What it guarantees

  - **`n = 1` per request.** Enforced in the client, restated here because it
    is the reason per-sample token accounting exists at all.
  - **Resume is "run the same command again".** Every request has an
    idempotency key and the writer's existing keys are read first.
  - **Append only.** One file per (split, benchmark, model, param_hash,
    problem). Nothing is rewritten, sorted or deduplicated.
  - **The ledger is written before the sample.** A record that reaches disk
    without its cost row would understate realized spend, and the spend guard
    reads the ledger.
  - **The ceiling is checked in flight**, not only before the run, so a run
    stops at the ceiling rather than discovering it afterwards.

## One deviation, recorded

`outcome_class` is set from truncation and the presence of visible text only.
Doc 4 section 3.5 defines `no_answer_visible` as "completed, no parseable
answer", which needs the extraction ladder, and doc 2 section 5.5 says the
ladder must never run inside the sampler. So at sample time the classes mean:

  - `api_failure`: the request failed after retries
  - `truncated_no_answer`: `finish_reason == "length"` and no visible text
  - `no_answer_visible`: completed with no visible text
  - `answered`: completed with visible text, parseable or not

`extracted_answer`, `extraction_pass` and `is_correct` stay null, and
`extractor_version` records that nothing has run. The derived table refines all
four offline from `raw_text`, which is stored verbatim.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from argmax import keys
from argmax.config import load_model, require
from argmax.datasets.canonicalize import version_hash
from argmax.datasets.gpqa import load_problems, prompt_for
from argmax.persist import paths, reader, writer
from argmax.sampling.client import Client, build_payload
from argmax.sampling.ledger import Ledger, PricingSnapshot
from argmax.sampling.probe import load_capabilities
from argmax.sampling.spend import Projection, SpendGuard
from argmax.schema import OutcomeClass, RunManifest, Sample, Split, SplitMethod

UNEXTRACTED = "unextracted"


def _pricing(cfg: dict[str, Any]) -> PricingSnapshot:
    p = cfg["pricing"]
    return PricingSnapshot(
        snapshot_id=require(
            p.get("snapshot_id"), "pricing.snapshot_id", cfg["_source"]
        ),
        date=p.get("date", ""),
        usd_per_1m_input=float(p["usd_per_1m_input"]),
        usd_per_1m_output=float(p["usd_per_1m_output"]),
        usd_per_1m_reasoning=p.get("usd_per_1m_reasoning"),
    )


def _classify(ok: bool, finish_reason: str, text: str) -> OutcomeClass:
    if not ok:
        return OutcomeClass.api_failure
    if not text.strip():
        return (
            OutcomeClass.truncated_no_answer
            if finish_reason == "length"
            else OutcomeClass.no_answer_visible
        )
    return OutcomeClass.answered


def run_phase(phase_id: str, split: str, cfg: dict[str, Any]) -> dict[str, Any]:
    """Draw `M` samples per problem for every model in the phase."""
    started = datetime.now(UTC).isoformat()
    run_id = f"{phase_id}-{started[:19].replace(':', '').replace('-', '')}"
    problems = load_problems()
    dataset_hash = version_hash(problems)
    M = int(require(cfg.get("M"), "M", cfg["_source"]))
    slugs = cfg["models"]

    counts: dict[str, int] = {}
    lock = threading.Lock()
    ledger = Ledger()
    guard = SpendGuard(ledger)
    manifest_written = {"params": {}, "hashes": {}, "returned": {}}

    for slug in slugs:
        model_cfg = load_model(slug)
        params = model_cfg["params"]
        pricing = _pricing(model_cfg)
        caps = load_capabilities(slug)
        if not caps.available:
            raise RuntimeError(f"{slug} is unavailable: {caps.unavailable_reason}")

        param_set = {
            "model": model_cfg["model_string"],
            "temperature": params.get("temperature"),
            "top_p": params.get("top_p"),
            "max_tokens": params["max_tokens"],
            "seed": params.get("seed"),
            "stop": params.get("stop") or [],
            "logprobs_depth": params.get("logprobs_depth"),
            "logprobs_style": params.get("logprobs_style"),
            "n": 1,
        }
        param_hash = keys.param_hash(param_set)
        manifest_written["params"][slug] = param_set
        manifest_written["hashes"][slug] = param_hash

        # Pre-flight, from the phase's recorded token estimate and its source.
        est = cfg["projected_tokens"]
        pending = 0
        todo: list[tuple[Any, int]] = []
        for problem in problems:
            path = paths.raw_path(
                split, "gpqa_diamond", slug, param_hash, problem.problem_id
            )
            existing = reader.existing_sample_keys(path)
            for index in range(M):
                key = keys.sample_key(
                    model_cfg["model_string"],
                    param_hash,
                    "gpqa_diamond",
                    problem.problem_id,
                    index,
                )
                if key not in existing:
                    todo.append((problem, index))
                    pending += 1

        headroom = guard.check(
            [
                Projection(
                    n_requests=pending,
                    mean_prompt_tokens=float(est["prompt"]),
                    mean_completion_tokens=float(est["completion"]),
                    pricing=pricing,
                )
            ]
        )
        print(
            f"{slug}: {pending} requests to make, "
            f"${headroom:,.4f} headroom after the projection"
        )

        def one(
            job,
            slug=slug,
            model_cfg=model_cfg,
            params=params,
            param_hash=param_hash,
            pricing=pricing,
            client=None,
        ):
            problem, index = job
            payload = build_payload(
                model_string=model_cfg["model_string"],
                prompt=prompt_for(problem),
                max_tokens=params["max_tokens"],
                temperature=params.get("temperature"),
                top_p=params.get("top_p"),
                seed=params.get("seed"),
                stop=params.get("stop") or [],
                logprobs_depth=params.get("logprobs_depth"),
                logprobs_style=params.get("logprobs_style", "integer_depth"),
            )
            response = client.complete(payload)
            body = response.body or {}
            choice = (body.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            text = message.get("content") or ""
            usage = body.get("usage") or {}
            finish_reason = choice.get("finish_reason") or ""
            cost = pricing.cost_usd(usage) if response.ok else 0.0
            sample_key = keys.sample_key(
                model_cfg["model_string"],
                param_hash,
                "gpqa_diamond",
                problem.problem_id,
                index,
            )
            record = Sample(
                sample_key=sample_key,
                run_id=run_id,
                split=Split(split),
                benchmark="gpqa_diamond",
                benchmark_version_hash=dataset_hash,
                problem_id=problem.problem_id,
                problem_hash=problem.problem_hash,
                sample_index=index,
                model_requested=model_cfg["model_string"],
                model_returned=body.get("model", ""),
                param_hash=param_hash,
                temperature=params.get("temperature"),
                top_p=params.get("top_p"),
                max_tokens=params["max_tokens"],
                seed=params.get("seed"),
                stop=params.get("stop") or [],
                prompt_hash=keys.prompt_hash(prompt_for(problem)),
                prompt_template_id=cfg["prompt_template_id"],
                request_timestamp_utc=datetime.now(UTC).isoformat(),
                attempt_count=response.attempt_count,
                latency_ms=response.latency_ms,
                raw_text=text,
                finish_reason=finish_reason,
                usage_raw=usage,
                api_response_id=body.get("id"),
                logprobs_raw=choice.get("logprobs"),
                response_extras={
                    k: v
                    for k, v in body.items()
                    if k not in {"id", "object", "created", "model", "choices", "usage"}
                },
                split_method=SplitMethod.none,
                split_ok=True,
                truncated=finish_reason == "length",
                hit_ceiling=int(usage.get("completion_tokens") or 0)
                >= int(params["max_tokens"]),
                outcome_class=_classify(response.ok, finish_reason, text),
                error_type=response.error_type,
                error_message=response.error_message,
                extractor_version=UNEXTRACTED,
                pricing_snapshot_id=pricing.snapshot_id,
                cost_usd_est=cost,
            )
            path = paths.raw_path(
                split, "gpqa_diamond", slug, param_hash, problem.problem_id
            )
            with lock:
                if response.ok:
                    ledger.record(
                        sample_key=sample_key,
                        run_id=run_id,
                        model_slug=slug,
                        usage_raw=usage,
                        pricing=pricing,
                        cost_usd=cost,
                        timestamp_utc=record.request_timestamp_utc,
                    )
                writer.append_sample(path, record)
                counts[record.outcome_class.value] = (
                    counts.get(record.outcome_class.value, 0) + 1
                )
                done = sum(counts.values())
                if done % 200 == 0:
                    guard.check_live()
                    print(f"  {done} written, {counts}")

        with Client(rate_per_sec=float(cfg.get("rate_per_sec", 4.0))) as client:
            workers = int(model_cfg.get("concurrency", 4))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(lambda j: one(j, client=client), todo))
        manifest_written["returned"][slug] = model_cfg["model_string"]

    manifest = RunManifest(
        run_id=run_id,
        phase_id=phase_id,
        split=Split(split),
        started_utc=started,
        ended_utc=datetime.now(UTC).isoformat(),
        git_sha=cfg["_git_sha"],
        git_dirty=cfg["_git_dirty"],
        lockfile_hash=cfg.get("_lockfile_hash", ""),
        dataset_version_hash=dataset_hash,
        prompt_template_id=cfg["prompt_template_id"],
        extractor_version=UNEXTRACTED,
        params_by_model=manifest_written["params"],
        param_hash_by_model=manifest_written["hashes"],
        capabilities_id_by_model={
            s: load_capabilities(s).capabilities_id for s in slugs
        },
        model_string_requested={s: load_model(s)["model_string"] for s in slugs},
        model_string_returned=manifest_written["returned"],
        pricing_snapshot_id=_pricing(load_model(slugs[0])).snapshot_id,
        prereg_tag=cfg.get("prereg_tag"),
        unanswered_sample_policy=cfg["unanswered_sample_policy"],
        draw_scheme=cfg["draw_scheme"],
        n_grid=cfg["n_grid"],
        M=M,
        realized_cost_usd=ledger.realized_spend_usd(),
        counts_by_outcome_class=counts,
    )
    path = paths.manifest_path(run_id)
    writer.write_manifest(path, manifest.model_dump_json(indent=2))
    print(f"wrote {path}")
    return {"run_id": run_id, "counts": counts, "manifest": str(path)}
