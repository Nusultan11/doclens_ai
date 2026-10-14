FROM golang:1.24.8-alpine AS minio-build

ARG MINIO_VERSION=RELEASE.2025-09-07T16-13-09Z

RUN GOBIN=/out go install github.com/minio/minio@${MINIO_VERSION}

FROM alpine:3.22 AS minio

RUN addgroup -S minio \
    && adduser -S -G minio -h /data minio

COPY --from=minio-build /out/minio /usr/local/bin/minio

USER minio

EXPOSE 9000 9001

ENTRYPOINT ["minio"]

FROM python:3.12-slim AS api

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

FROM api AS worker

USER root

RUN pip install --no-cache-dir '.[eda]'

USER doclens

CMD ["python", "-m", "doclens_ai.worker"]
