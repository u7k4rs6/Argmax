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

#: Second line of defence: a long opaque token in any position, with no
#: `Bearer` and no `key=` to announce it.
#:
#: The literal scrub above only fires when the value is in this process's
#: environment. That covers the sampler, which reads the key from there, and it
#: does not cover a key that arrives any other way: pasted into a config, read
#: from a file, echoed back inside a provider error. This rule has no such
#: dependency.
#:
#: Deliberately NOT matching pure lowercase hex or pure digits. sha256 digests
#: are logged all over this project, in manifests, provenance records and
#: leakage fingerprints, and redacting them would break the audit trail to
#: guard against a shape no provider issues. A real key mixes cases or symbols.
_OPAQUE_TOKEN = re.compile(r"\b(?=[A-Za-z0-9_\-]{32,}\b)[A-Za-z0-9_\-]{32,}\b")
_PURE_HEX = re.compile(r"\A[a-f0-9]+\Z")
_PURE_DIGITS = re.compile(r"\A[0-9]+\Z")


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
    text = _OPAQUE_TOKEN.sub(_redact_unless_digest, text)
    return text


def _redact_unless_digest(match: re.Match[str]) -> str:
    token = match.group(0)
    if _PURE_HEX.match(token) or _PURE_DIGITS.match(token):
        return token  # a digest or a counter, not key material
    return REDACTED


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
