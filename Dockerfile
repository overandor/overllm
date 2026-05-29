FROM python:3.12-slim

WORKDIR /app

# Install Node.js for UI build
RUN apt-get update && apt-get install -y curl nodejs npm && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full repo
COPY . .

# Build React UI
RUN cd ui && npm install && npm run build

# Set Python path
ENV PYTHONPATH=/app
ENV PORT=7860
ENV OVERLLM_MODE=paper
ENV LIVE_TRADING_ENABLED=false

EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
