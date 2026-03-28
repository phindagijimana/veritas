# Veritas API — production-oriented image (gunicorn + uvicorn workers).
# Build: docker build -t veritas-api .
# Run:  set env file from .env.production.example; map port 6000; use /health and /ready for probes.
FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 veritas \
    && chown -R veritas:veritas /app
USER veritas

EXPOSE 6000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD curl -fsS http://127.0.0.1:6000/health || exit 1

# Workers: override WEB_CONCURRENCY (default 4). Timeout for long requests.
ENV WEB_CONCURRENCY=4
CMD gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w ${WEB_CONCURRENCY} \
    -b 0.0.0.0:6000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
