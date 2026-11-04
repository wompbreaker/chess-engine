.PHONY: sync hooks check

sync:
	uv sync

hooks:
	uv run pre-commit install --install-hooks

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest
