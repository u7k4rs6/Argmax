"""The five-pass answer ladder, instrumented.

Runs OFFLINE over stored raw text, so the ladder can be revised and re-run at
zero cost. It must never run inside the sampler.
"""

from argmax.extract.ladder import EXTRACTOR_VERSION, Extraction, extract

__all__ = ["extract", "Extraction", "EXTRACTOR_VERSION"]
