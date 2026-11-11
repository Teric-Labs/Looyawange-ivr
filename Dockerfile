# Looyawange IVR — Africa's Talking Voice adapter for Wakilibot
# Build:  docker build -t bateesa/looyawange-ivr:latest .
# Run:    docker run --rm -p 8088:8088 --env-file .env bateesa/looyawange-ivr:latest
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt \
    && pip uninstall -y pytest || true

COPY app/ ./app/
COPY static/ ./static/
COPY scripts/ ./scripts/

RUN mkdir -p /app/static/audio \
    && useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app/static

ENV PORT=8088
ENV HOME=/app
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD sh -c 'curl -f "http://127.0.0.1:${PORT:-8088}/health" || exit 1'

USER app

# Render injects $PORT; local default is 8088.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8088}"]
