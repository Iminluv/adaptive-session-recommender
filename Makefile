.PHONY: check test-unit sample-fixture

check:
	python3 --version
	git diff --check

test-unit:
	PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v

sample-fixture:
	PYTHONPATH=src python3 scripts/validate_sample.py data/sample/events.jsonl

