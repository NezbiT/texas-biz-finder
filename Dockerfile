# TX BizFinder FastAPI — optimized for Oracle Cloud Free Tier (Ampere A1 / x86)
# Build:  docker build -t txbizfinder-api .
# Run:    docker run --env-file .env -p 8000:8000 -v ./data:/app/data txbizfinder-api

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

# System deps: curl for healthcheck; build tools only if needed for wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cache)
COPY requirements.txt pyproject.toml ./
COPY backend ./backend
COPY scripts ./scripts
COPY run.py ./

RUN pip install --upgrade pip \
    && pip install -e . \
    && pip install -r requirements.txt

# Optional: Playwright chromium (heavy ~300MB). Only when ENABLE_WEBSITE_RESEARCH=true
ARG INSTALL_PLAYWRIGHT=false
RUN if [ "$INSTALL_PLAYWRIGHT" = "true" ]; then \
      playwright install --with-deps chromium; \
    fi

# Non-root user for free-tier security
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/processed /app/data/raw /app/data/staging \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health: API must answer even if DuckDB not yet mounted (degraded)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

# Single worker by default (Oracle Always Free micro / 1 OCPU)
# Override: UVICORN_WORKERS=2 on Ampere with ≥8GB RAM
CMD ["sh", "-c", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-1} --proxy-headers --forwarded-allow-ips='*'"]
