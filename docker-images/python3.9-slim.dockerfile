# Stage 1: Builder - Install dependencies with build tools
FROM python:3.9-slim AS builder

# Install build essentials for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies with optimized pip flags and cleanup
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt && rm -rf /tmp/requirements.txt

# Stage 2: Runtime - Use slim base image without build tools
FROM tiangolo/uvicorn-gunicorn:python3.9-slim

LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code last to maximize cache hits
COPY ./app /app
