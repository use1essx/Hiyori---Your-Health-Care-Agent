# Healthcare AI V2 - Multi-stage Dockerfile
# Optimized for both development and production builds

# =============================================================================
# Base Stage - Common dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-chi-tra \
    tesseract-ocr-chi-sim \
    poppler-utils \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create app directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY requirements.txt* ./

# =============================================================================
# Development Stage
# =============================================================================
FROM base as development

# Install development dependencies
RUN pip install -e ".[dev]"

# Create necessary directories
RUN mkdir -p /app/logs /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to app user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command for development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Dependencies Stage
# =============================================================================
FROM base as production-deps

    # Install only production dependencies
    RUN pip install .

# =============================================================================
# Production Stage
# =============================================================================
FROM python:3.11-slim as production

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-chi-tra \
    tesseract-ocr-chi-sim \
    poppler-utils \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create app directory and set permissions
WORKDIR /app
RUN mkdir -p /app/logs /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Copy Python dependencies from production-deps stage
COPY --from=production-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=production-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser prompts/ ./prompts/
COPY --chown=appuser:appuser sql/ ./sql/
COPY --chown=appuser:appuser config/ ./config/
COPY --chown=appuser:appuser pyproject.toml ./
COPY --chown=appuser:appuser run_hk_data_pipeline.py ./

# Switch to app user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production command
CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# =============================================================================
# Testing Stage
# =============================================================================
FROM base as testing

# Install test dependencies as root before switching user
RUN pip install -e ".[dev]"

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/uploads /app/data && \
    chown -R appuser:appuser /app

# Copy source code
COPY --chown=appuser:appuser . .

# Switch to app user
USER appuser

# Run tests
CMD ["python", "-m", "pytest", "src/tests/", "-v", "--cov=src", "--cov-report=html"]
