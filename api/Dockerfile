FROM gcc:12 as builder

WORKDIR /app

# Install CMake
RUN apt-get update && apt-get install -y \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy C++ source
COPY cpp/CMakeLists.txt cpp/
COPY cpp/include/ cpp/include/
COPY cpp/src/ cpp/src/
COPY cpp/vocab.txt cpp/

# Build C++ library
RUN cd cpp && mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc)

# Python runtime
FROM python:3.14-slim

WORKDIR /app

# Install Python dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built library from builder
COPY --from=builder /app/cpp/build/liboverllm.so /app/lib/
COPY --from=builder /app/cpp/build/overllm_inference /app/
COPY --from=builder /app/cpp/build/test_overllm /app/

# Copy API code
COPY api/main.py .

# Set library path
ENV LD_LIBRARY_PATH=/app/lib:$LD_LIBRARY_PATH

# Expose port
EXPOSE 8001

# Run API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
