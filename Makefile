CODE_DIRS=snakeguice tests

.PHONY: all
all: fmt lint tests

.PHONY: tests
tests:
	pytest -vv tests

.PHONY: lint
lint:
	flake8 $(CODE_DIRS)
	black --check --diff $(CODE_DIRS)
	isort --check $(CODE_DIRS)
	mypy $(CODE_DIRS)

.PHONY: fmt
fmt:
	black $(CODE_DIRS)
	isort $(CODE_DIRS)

.PHONY: docs
docs:
	(cd docs; make html)
