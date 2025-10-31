FROM tiangolo/uvicorn-gunicorn:python3.10

LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies with optimized pip flags and cleanup in same layer
RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt && rm -rf /tmp/requirements.txt

# Copy application code last to maximize cache hits
COPY ./app /app
