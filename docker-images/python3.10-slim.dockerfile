# syntax=docker/dockerfile:1
# Stage 1: Builder - Install dependencies with build tools
FROM python:3.10-slim AS builder

# Install build essentials for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies with BuildKit cache mount for faster builds
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir --upgrade -r /tmp/requirements.txt && rm -rf /tmp/requirements.txt

# Stage 2: Runtime - Use slim base image without build tools
FROM tiangolo/uvicorn-gunicorn:python3.10-slim

# Add maintainer label immediately after FROM for optimal layer caching
LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code last to maximize cache hits
COPY ./app /app
