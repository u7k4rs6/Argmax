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
