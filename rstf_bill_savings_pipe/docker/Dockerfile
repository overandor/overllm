# Production Dockerfile for RSTF API Service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY rstf_core.py .
COPY bill_savings_pipe.py .
COPY automated_benchmark_runner.py .

# Create non-root user
RUN useradd -m -u 1000 rstf && chown -R rstf:rstf /app
USER rstf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import rstf_core; print('OK')" || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["python3", "bill_savings_pipe.py", "--help"]
