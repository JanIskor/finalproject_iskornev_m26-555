.PHONY: lint format build package-install run

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

build:
	uv build

package-install:
	uv pip install --python .venv/bin/python --reinstall dist/*.whl

run:
	uv run project
