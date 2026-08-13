"""Writers, paths, schema validation.

Nothing in this package imports an HTTP client. tests/test_no_network.py
enforces that.
"""

from argmax.persist.paths import raw_path, raw_root
from argmax.persist.reader import read_samples
from argmax.persist.writer import append_sample

__all__ = ["raw_path", "raw_root", "read_samples", "append_sample"]
