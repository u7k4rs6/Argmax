"""Keep the API key out of logs.

Error paths are where keys leak. An unhandled client exception that dumps the
request object prints the Authorization header. Everything emitted through
logging passes this filter, and the client scrubs exception messages before
re-raising.

tests/test_redaction.py logs a planted fake key and asserts the emitted line
does not contain it.
"""

from __future__ import annotations

import logging
import os
import re

REDACTED = "[REDACTED]"

_AUTH_HEADER = re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?\S+")
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}")
_KEYISH = re.compile(r"(?i)\b(?:api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?\S+")


def _secrets() -> list[str]:
    """Live secret values to scrub literally, longest first."""
    vals = [
        os.environ.get("TOGETHER_API_KEY", ""),
    ]
    return sorted((v for v in vals if v and len(v) >= 8), key=len, reverse=True)


def scrub(text: str) -> str:
    """Remove key material from an arbitrary string."""
    for secret in _secrets():
        text = text.replace(secret, REDACTED)
    text = _AUTH_HEADER.sub(rf"\1{REDACTED}", text)
    text = _BEARER.sub(REDACTED, text)
    text = _KEYISH.sub(
        lambda m: m.group(0).split("=")[0].split(":")[0] + "=" + REDACTED, text
    )
    return text


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - a broken format string must not leak
            record.msg = REDACTED
            record.args = ()
            return True
        scrubbed = scrub(message)
        if scrubbed != message:
            record.msg = scrubbed
            record.args = ()
        return True


def install_redaction_filter(logger: logging.Logger | None = None) -> None:
    """Attach to the root logger and to every existing handler.

    Attaching to the logger alone is not enough: a handler added later by a
    library carries no filter, so the handlers are covered too.
    """
    target = logger or logging.getLogger()
    filt = RedactionFilter()
    target.addFilter(filt)
    for handler in target.handlers:
        handler.addFilter(filt)
