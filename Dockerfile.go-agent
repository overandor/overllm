# Use official Go image as base
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go/go.mod go/go.sum* ./

# Download dependencies
RUN go mod download

# Copy source code
COPY go/ ./go/

# Build the application
WORKDIR /app/go
RUN CGO_ENABLED=0 GOOS=linux go build -o overllm-agent ./cmd/overllm-agent

# Use alpine for final image
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/go/overllm-agent .

# Expose port
EXPOSE 7749

# Run the application
CMD ["./overllm-agent"]
