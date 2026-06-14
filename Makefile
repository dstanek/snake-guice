CODE_DIRS=snakeguice tests examples

.PHONY: all
all: fmt lint tests

.PHONY: tests
tests:
	uv run pytest -vv tests

.PHONY: example-tests
example-tests:
	uv run pytest -vv examples

.PHONY: lint
lint:
	uv run flake8 $(CODE_DIRS)
	uv run black --check --diff $(CODE_DIRS)
	uv run isort --check $(CODE_DIRS)
	uv run mypy $(CODE_DIRS) --show-error-context

.PHONY: fmt
fmt:
	uv run black $(CODE_DIRS)
	uv run isort $(CODE_DIRS)

.PHONY: docs
docs:
	(cd docs; uv run --extra docs make html)
