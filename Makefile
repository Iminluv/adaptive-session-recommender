PYTHON ?= .venv/bin/python

.PHONY: install check test-unit sample-fixture batch-sample api-sample api-run sample up down seed-cassandra

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e .

check:
	$(PYTHON) --version
	git diff --check

up:
	docker compose up -d

down:
	docker compose down

seed-cassandra:
	PYTHONPATH=src:. $(PYTHON) scripts/seed_cassandra.py

test-unit:
	PYTHONPATH=src:. $(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

sample-fixture:
	PYTHONPATH=src $(PYTHON) scripts/validate_sample.py data/sample/events.jsonl

batch-sample:
	PYTHONPATH=src $(PYTHON) -m adaptive_recommender.batch.run_sample --input data/sample/events.jsonl --output data/generated

api-sample:
	PYTHONPATH=src:. $(PYTHON) scripts/run_api_sample.py

api-run:
	PYTHONPATH=src:. $(PYTHON) -m uvicorn api.main:app --host 0.0.0.0 --port 8000

sample: sample-fixture batch-sample api-sample

