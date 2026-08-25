PYTHON ?= python

.PHONY: install demo demo-erie test search

install:
	$(PYTHON) -m pip install -e ".[nasa,dev]"

demo:
	$(PYTHON) -m upstate_hyperspectral demo --region finger-lakes --output-dir outputs/finger-lakes

demo-erie:
	$(PYTHON) -m upstate_hyperspectral demo --region lake-erie --output-dir outputs/lake-erie

test:
	$(PYTHON) -m unittest discover -s tests -v

search:
	$(PYTHON) -m upstate_hyperspectral search --region finger-lakes --start 2023-05-01 --end 2026-10-31
