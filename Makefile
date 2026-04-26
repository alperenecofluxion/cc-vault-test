.PHONY: check run

check:
	uv run ruff check
	uv run ruff format --check
	uv run pytest

run:
	uv run uvicorn app.main:app --reload
