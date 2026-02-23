# syntax=docker/dockerfile:1

# ─── Base image (Alpine for minimal size) ───────────────────────
FROM python:3.11-alpine AS base

# ─── Build stage: install dependencies ──────────────────────────
FROM base AS builder

WORKDIR /build

# Install build-time dependencies (needed for C extensions)
RUN apk add --no-cache gcc musl-dev libffi-dev

# Install Python dependencies into a virtual env for clean copy
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Strip the venv to minimize image size
RUN pip uninstall -y pip setuptools watchfiles 2>/dev/null; \
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; \
    find /opt/venv -type d -name "tests" -o -name "test" | xargs rm -rf 2>/dev/null; \
    find /opt/venv -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.pyi" \) -delete 2>/dev/null; \
    rm -rf /opt/venv/include /opt/venv/share; \
    true

# ─── Runtime stage: slim final image ───────────────────────────
FROM base AS runtime

LABEL maintainer="Anuj Parashar"
LABEL description="VCE Vocabulary Flashcards - FastAPI Application"

# Create non-root user
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -s /bin/sh -D appuser

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Remove files not needed at runtime & create data directory
RUN rm -rf Dockerfile .dockerignore start_app.sh fastapi_start_app.sh STARTUP_GUIDE.md __pycache__ && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Expose port
EXPOSE 5001

# Environment defaults for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# Health check using the existing /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5001/health')"]

# Switch to non-root user
USER appuser

# Run with gunicorn + uvicorn workers for production concurrency
CMD ["gunicorn", "fastapi_web_flashcards:app", \
     "--bind", "0.0.0.0:5001", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
