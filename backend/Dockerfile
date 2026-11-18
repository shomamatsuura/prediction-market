# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Development: test and lint tools, code mounted from the host by docker compose.
FROM base AS dev
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production (default target): code baked in, runs as an unprivileged user.
FROM base AS prod
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
COPY --chown=root:root . .
USER 10001
ENV APP_ENV=production \
    DOCS_ENABLED=false
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/health', timeout=4)"
# One worker: the ingestion scheduler runs inside the API process.
# Proxy headers are handled by the app (TRUSTED_PROXY_HOPS), which only trusts the entry the
# proxy appended; uvicorn's FORWARDED_ALLOW_IPS=* would trust the client-controlled one.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --no-proxy-headers --no-server-header"]
