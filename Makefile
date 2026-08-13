.PHONY: help probe sample derived analyze verify leakcheck test lint clean-derived

PY := python

help:
	@echo "make probe   MODEL=<slug>                 capability probe, ~1 sample (PAID)"
	@echo "make sample  PHASE=<phase> SPLIT=<split>  draw samples (PAID)"
	@echo "make derived                              rebuild derived tables from raw (offline)"
	@echo "make analyze SPLIT=<split>                curves, gates, matched compute (offline)"
	@echo "make verify                               falsification suite"
	@echo "make leakcheck QUESTIONS=<src> TARGET=<p> question-text check before release"
	@echo "make test                                 full test suite"
	@echo ""
	@echo "PAID targets refuse to start unless ARGMAX_SPEND_CEILING_USD is set."

# --- paid targets -----------------------------------------------------------
# Phases run through make, not from an interactive shell, so that the ceiling
# is enforced and a manifest is written. See doc 3 section 4.6.

probe:
	@test -n "$(MODEL)" || (echo "MODEL=<slug> required" && exit 1)
	@test -n "$$ARGMAX_SPEND_CEILING_USD" || \
		(echo "ARGMAX_SPEND_CEILING_USD is not set. Refusing to run." && exit 1)
	$(PY) scripts/probe.py --model $(MODEL)

sample:
	@test -n "$(PHASE)" || (echo "PHASE=<phase> required" && exit 1)
	@test -n "$(SPLIT)" || (echo "SPLIT=exploratory|confirmatory required" && exit 1)
	@test -n "$$ARGMAX_SPEND_CEILING_USD" || \
		(echo "ARGMAX_SPEND_CEILING_USD is not set. Refusing to run." && exit 1)
	$(PY) scripts/sample.py --phase $(PHASE) --split $(SPLIT)

# --- offline targets --------------------------------------------------------

derived:
	$(PY) scripts/derive.py

analyze:
	@test -n "$(SPLIT)" || (echo "SPLIT=exploratory|confirmatory required" && exit 1)
	$(PY) scripts/analyze.py --split $(SPLIT)

verify:
	$(PY) -m pytest tests/falsification.py

# Run before publishing anything derived from the raw store. QUESTIONS points
# at the gated local source; it is read, fingerprinted, and never written out.
# See files/03-security-and-access.md s5.1.
leakcheck:
	@test -n "$(QUESTIONS)" || (echo "QUESTIONS=<gated source> required" && exit 1)
	@test -n "$(TARGET)" || (echo "TARGET=<path to release> required" && exit 1)
	$(PY) scripts/leakcheck.py --questions $(QUESTIONS) --target $(TARGET) \
		$(if $(README),--readme $(README),)

test:
	$(PY) -m pytest

lint:
	ruff check . && ruff format --check .

# Deleting derived and rebuilding must reproduce byte-identical files.
# tests/test_recompute.py asserts this.
clean-derived:
	rm -rf data/derived
