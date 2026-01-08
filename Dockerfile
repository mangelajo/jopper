# Dockerfile for Jopper
# Multi-stage build using uv for efficient Python package management

FROM python:3.12-slim as builder

# Install curl for uv installer
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv (compatible with both docker and podman)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files and source code
COPY pyproject.toml README.md ./
COPY src/ /app/src/

# Create a virtual environment and install dependencies
RUN uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install --no-cache -e .

# Final stage
FROM python:3.12-slim

# Install Node.js, npm for Joplin CLI, and procps for liveness probe
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    ca-certificates \
    procps && \
    rm -rf /var/lib/apt/lists/*

# Install Joplin CLI globally
RUN npm install -g joplin

# Set working directory
WORKDIR /app

# Copy virtual environment and installed package from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/README.md /app/README.md

# Create directories for state database and Joplin data
RUN mkdir -p /data /home/node/.config/joplin && \
    chmod -R 777 /home/node/.config/joplin

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    JOPPER_STATE_DB_PATH=/data/state.db \
    NODE_PATH=/usr/local/lib/node_modules \
    HOME=/root

# Run daemon mode by default
CMD ["jopper", "daemon"]


