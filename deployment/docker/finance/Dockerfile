# ── Build Stage ───────────────────────────────────────────────
FROM container.tmbiz.info/hub/python:3.14-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime Stage ────────────────────────────────────────────
FROM container.tmbiz.info/hub/python:3.14-slim

# Security: run as non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY sql/ ./sql/

# Ensure runtime user can write where needed (logs, temp artifacts).
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Default: run the API server
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

EXPOSE 8000

CMD ["gunicorn", "-c", "python:app.infrastructure.gunicorn.config", "app.main:app"]
