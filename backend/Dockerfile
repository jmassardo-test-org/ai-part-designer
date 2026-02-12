# AI Part Designer - Backend
# Multi-stage Dockerfile for development and production
# Uses Python with Build123d for CAD generation

# =============================================================================
# Base stage: Python 3.12 with uv for fast package management
# =============================================================================
FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing bytecode and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (including libGL for Build123d/OCP, poppler for pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# =============================================================================
# Development stage
# =============================================================================
FROM base AS development

# Copy project files
COPY pyproject.toml README.md ./

# Install dependencies with uv
RUN uv sync --all-extras --no-dev

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Development command with hot reload
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production stage
# =============================================================================
FROM base AS production

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy project files
COPY pyproject.toml README.md ./

# Install production dependencies with uv
# Also install setuptools<82 for pkg_resources (needed by opentelemetry instrumentation)
RUN uv sync --no-dev && uv pip install "setuptools<82"

# Set ownership of venv to appuser so uv run works correctly
RUN chown -R appuser:appuser .venv

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chown -R appuser:appuser uploads

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production command - use .venv directly, single worker for stability
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Worker stage (Celery)
# =============================================================================
FROM base AS worker

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy project files
COPY pyproject.toml README.md ./

# Install dependencies with uv
RUN uv sync --no-dev

# Set ownership of venv to appuser
RUN chown -R appuser:appuser .venv

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chown -R appuser:appuser uploads

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Worker command - use .venv directly
CMD [".venv/bin/celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"]

# =============================================================================
# Beat stage (Celery scheduler)
# =============================================================================
FROM base AS beat

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy project files
COPY pyproject.toml README.md ./

# Install dependencies with uv
RUN uv sync --no-dev

# Set ownership of venv to appuser
RUN chown -R appuser:appuser .venv

# Create uploads directory with proper permissions
RUN mkdir -p uploads && chown -R appuser:appuser uploads

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Beat command - use .venv directly
CMD [".venv/bin/celery", "-A", "app.worker.celery_app", "beat", "--loglevel=info"]
