# =============================================================================
# Base stage: Common setup for all stages
# =============================================================================
FROM python:3.11-slim AS base

WORKDIR /app

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# =============================================================================
# Builder stage: Install dependencies
# =============================================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project file and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# =============================================================================
# Development stage: For local development with hot reload
# =============================================================================
FROM builder AS development

# Copy application code
COPY app ./app
COPY frontend ./frontend
COPY migrations ./migrations
COPY alembic.ini .
COPY scripts ./scripts

# Create directories
RUN mkdir -p uploads

# Expose port
EXPOSE 8000

# Development command with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production stage: Optimized for production deployment
# =============================================================================
FROM base AS production

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup frontend ./frontend
COPY --chown=appuser:appgroup migrations ./migrations
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup scripts ./scripts
COPY --chown=appuser:appgroup docker-entrypoint.sh .

# Create directories with proper ownership
RUN mkdir -p uploads && chown -R appuser:appgroup uploads

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Use entrypoint script for migrations
ENTRYPOINT ["./docker-entrypoint.sh"]

# Production command with workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
