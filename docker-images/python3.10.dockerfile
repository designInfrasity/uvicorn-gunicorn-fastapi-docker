# syntax=docker/dockerfile:1
FROM tiangolo/uvicorn-gunicorn:python3.10

LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies with BuildKit cache mount for faster builds
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir --upgrade -r /tmp/requirements.txt && rm -rf /tmp/requirements.txt

# Copy application code last to maximize cache hits
COPY ./app /app
