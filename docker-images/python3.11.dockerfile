FROM tiangolo/uvicorn-gunicorn:python3.11

LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies with --no-cache-dir and --upgrade flags
RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt

# Copy application code last to maximize cache hits
COPY ./app /app
