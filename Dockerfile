# ==============================================================================
# DyslexAid V2 — Production Backend Dockerfile
# ==============================================================================
# Multi-stage build for a minimal, secure, non-root Python 3.11 ASGI service.
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final minimal runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

# Create unprivileged user for production security
RUN groupadd -r dyslexaid && useradd -r -g dyslexaid dyslexaid

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/dyslexaid/.local
ENV PATH=/home/dyslexaid/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source
COPY backend /app/backend

# Set correct permissions
RUN chown -R dyslexaid:dyslexaid /app

USER dyslexaid

WORKDIR /app/backend

EXPOSE 8000

# Native container healthcheck against liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Production ASGI server execution with graceful termination timeout
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "30"]
