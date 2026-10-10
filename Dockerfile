FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN groupadd --system doclens \
    && useradd --system --gid doclens --home-dir /app doclens

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY alembic ./alembic

RUN pip install --no-cache-dir .

USER doclens

EXPOSE 8000

CMD ["uvicorn", "doclens_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
