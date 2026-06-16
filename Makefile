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
	uv run ruff check $(CODE_DIRS)
	uv run ruff format --check $(CODE_DIRS)
	uv run mypy $(CODE_DIRS) --show-error-context

.PHONY: fmt
fmt:
	uv run ruff check --fix $(CODE_DIRS)
	uv run ruff format $(CODE_DIRS)

.PHONY: docs
docs:
	(cd docs; uv run --extra docs make html)
