FROM python:3.12-slim

WORKDIR /app

# Install Node.js 20.x, git, and build essentials
RUN apt-get update && apt-get install -y curl git ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node.js version
RUN node --version && npm --version

# Copy and install Python deps first (better caching)
COPY api/requirements.txt ./api/
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy full repo
COPY . .

# Build React UI
RUN cd ui && npm ci && npm run build

# Set environment
ENV PYTHONPATH=/app
ENV PORT=7860
ENV OVERLLM_MODE=paper
ENV LIVE_TRADING_ENABLED=false

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers"]
