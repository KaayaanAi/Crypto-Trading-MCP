# Multi-stage build for optimal image size
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1001 trader \
    && useradd -r -u 1001 -g trader trader

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=trader:trader . .

# Create logs directory
RUN mkdir -p logs && chown trader:trader logs

# Create health check script
RUN echo '#!/bin/bash\npython -c "import sys; sys.exit(0)"' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh && \
    chown trader:trader /app/healthcheck.sh

# Switch to non-root user
USER trader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/healthcheck.sh

# Expose ports (if needed for future HTTP endpoints)
EXPOSE 8080

# Default command
CMD ["python", "client/crypto_trader.py"]