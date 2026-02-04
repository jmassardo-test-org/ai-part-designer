# AI Part Designer - Backend
# Multi-stage Dockerfile for development and production
# Uses Python with Build123d for CAD generation

# =============================================================================
# Base stage: Python with Build123d
# =============================================================================
FROM python:3.11-slim-bookworm AS base

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

WORKDIR /app

# Install Build123d and CAD dependencies via pip
# Using latest available versions
RUN pip install --no-cache-dir \
    build123d scipy ipython \
    ezdxf svgpathtools trianglesolver webcolors anytree

# =============================================================================
# Development stage
# =============================================================================
FROM base AS development

# Copy requirements and install Python dependencies
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "python-multipart>=0.0.6" \
    "email-validator>=2.0.0" \
    "sqlalchemy[asyncio]>=2.0.25" \
    "asyncpg>=0.29.0" \
    "alembic>=1.13.0" \
    "redis>=5.0.0" \
    "celery[redis]>=5.3.0" \
    "anthropic>=0.40.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "cryptography>=42.0.0" \
    "pyotp>=2.9.0" \
    "qrcode[pil]>=7.4.0" \
    "boto3>=1.34.0" \
    "aioboto3>=13.0.0" \
    "httpx>=0.26.0" \
    "python-dotenv>=1.0.0" \
    "structlog>=24.1.0" \
    "bcrypt==4.0.1" \
    "Pillow>=10.0.0" \
    "numpy>=1.26.0" \
    "pdf2image>=1.16.0" \
    "aiofiles>=23.0.0" \
    "stripe>=8.0.0" \
    "authlib>=1.3.0" \
    "itsdangerous>=2.1.0" \
    "PyMuPDF>=1.24.0" \
    "pytest>=8.0.0" \
    "pytest-asyncio>=0.23.0" \
    "pytest-cov>=4.1.0" \
    "factory-boy>=3.3.0" \
    "    "aiosqlite>=0.19.0" \
    "typing_extensions>=4.0.0""

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production stage
# =============================================================================
FROM base AS production

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy and install dependencies (build123d is from conda)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir \
    "fastapi>=0.109.0" \
    "uvicorn[standard]>=0.27.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "python-multipart>=0.0.6" \
    "email-validator>=2.0.0" \
    "sqlalchemy[asyncio]>=2.0.25" \
    "asyncpg>=0.29.0" \
    "alembic>=1.13.0" \
    "redis>=5.0.0" \
    "celery[redis]>=5.3.0" \
    "anthropic>=0.40.0" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[bcrypt]>=1.7.4" \
    "cryptography>=42.0.0" \
    "pyotp>=2.9.0" \
    "qrcode[pil]>=7.4.0" \
    "boto3>=1.34.0" \
    "aioboto3>=13.0.0" \
    "httpx>=0.26.0" \
    "python-dotenv>=1.0.0" \
    "structlog>=24.1.0" \
    "bcrypt==4.0.1" \
    "Pillow>=10.0.0" \
    "numpy>=1.26.0" \
    "pdf2image>=1.16.0" \
    "aiofiles>=23.0.0" \
    "stripe>=8.0.0" \
    "authlib>=1.3.0" \
    "itsdangerous>=2.1.0" \
    "PyMuPDF>=1.24.0"

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
