
# syntax=docker/dockerfile:1

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install only the system utilities needed for reliable HTTPS connections.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install project metadata and application dependencies.
COPY pyproject.toml README.md ./

# Install the API plus optional database, Redis and observability support.
# Remove optional groups only if they are not defined in pyproject.toml.
RUN pip install --no-cache-dir \
    ".[database,redis,observability]"

# Copy the application after dependencies to improve build caching.
COPY app/ ./app/

# Create a non-root runtime user.
RUN groupadd --system app \
    && useradd --system --gid app --home-dir /nonexistent app \
    && chown -R app:app /app

USER app

EXPOSE 8000

# Liveness is intentionally independent of upstream provider availability.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
