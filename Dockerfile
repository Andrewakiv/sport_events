FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --create-home app
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations
USER app

EXPOSE 8000
CMD ["uvicorn", "sport_events.main:app", "--host", "0.0.0.0", "--port", "8000"]
