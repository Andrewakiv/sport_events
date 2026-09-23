.PHONY: install lint format typecheck test test-integration check up down

install:
	uv sync --locked

lint:
	uv run --locked ruff check .
	uv run --locked ruff format --check .

format:
	uv run --locked ruff check --fix .
	uv run --locked ruff format .

typecheck:
	uv run --locked mypy

test:
	uv run --locked pytest -m "not integration" --cov --cov-report=term-missing

test-integration:
	uv run --locked pytest -m integration

check: lint typecheck test

up:
	docker compose up --build

down:
	docker compose down
