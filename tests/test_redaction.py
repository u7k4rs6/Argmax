"""The key never reaches a log line.

Doc 3 s2.2: "Test it: a unit test that logs a fake key and asserts the emitted
line does not contain it."
"""

from __future__ import annotations

import logging

from argmax.sampling.redact import REDACTED, RedactionFilter, scrub

FAKE_KEY = "sk-fake-0123456789abcdef0123456789abcdef"


def test_scrub_removes_live_key_value(monkeypatch):
    monkeypatch.setenv("TOGETHER_API_KEY", FAKE_KEY)
    assert FAKE_KEY not in scrub(f"requesting with key {FAKE_KEY}")


def test_scrub_removes_authorization_header():
    text = f"headers={{'Authorization': 'Bearer {FAKE_KEY}'}}"
    out = scrub(text)
    assert FAKE_KEY not in out
    assert REDACTED in out


def test_emitted_log_line_does_not_contain_the_key(monkeypatch, caplog):
    monkeypatch.setenv("TOGETHER_API_KEY", FAKE_KEY)
    logger = logging.getLogger("argmax.test.redaction")
    logger.addFilter(RedactionFilter())

    with caplog.at_level(logging.INFO, logger=logger.name):
        logger.info("Authorization: Bearer %s", FAKE_KEY)

    emitted = "\n".join(r.getMessage() for r in caplog.records)
    assert FAKE_KEY not in emitted


def test_error_path_is_scrubbed(monkeypatch, caplog):
    """Error paths are where keys leak: an exception that dumps the request
    object prints the header."""
    monkeypatch.setenv("TOGETHER_API_KEY", FAKE_KEY)
    logger = logging.getLogger("argmax.test.redaction.err")
    logger.addFilter(RedactionFilter())

    exc_text = (
        "ConnectError(request=<Request POST /v1/chat/completions "
        f"headers={{'authorization': 'Bearer {FAKE_KEY}'}}>)"
    )
    with caplog.at_level(logging.ERROR, logger=logger.name):
        logger.error("request failed: %s", exc_text)

    assert FAKE_KEY not in "\n".join(r.getMessage() for r in caplog.records)


# --- second line of defence: the key that is not in this process's env ------


def test_a_long_opaque_token_is_redacted_without_any_marker():
    """The literal scrub only fires when the value is in os.environ. A key
    pasted into a config, or echoed back inside a provider error, has no
    `Bearer` and no `key=` to announce it."""
    from argmax.sampling.redact import scrub

    pasted = "aB3xY7zQ9wE2rT5yU8iO1pA4sD6fG0hJkL"
    assert pasted not in scrub(f"provider said: unknown credential {pasted}")


def test_sha256_digests_survive_redaction():
    """Manifests, provenance records and leakage fingerprints are full of
    digests. Redacting them to guard against a shape no provider issues would
    break the audit trail this project runs on."""
    from argmax.sampling.redact import scrub

    digest = "f22e15c8cd1d6ed5a4b58fd5a289fcb688e3dd91564a7935d7203bf58c6bafec"
    line = f"ladder sha256 {digest} verified"
    assert scrub(line) == line


def test_long_decimal_runs_survive_redaction():
    from argmax.sampling.redact import scrub

    counter = "12345678901234567890123456789012345"
    assert counter in scrub(f"sample_index {counter}")
