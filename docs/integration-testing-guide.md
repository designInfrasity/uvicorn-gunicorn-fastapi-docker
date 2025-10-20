# Integration Testing Guide for Optimized Docker Images

## Overview

This guide covers the comprehensive integration testing suite for all optimized Docker image variants in the uvicorn-gunicorn-fastapi-docker repository. The integration tests serve as the final validation gate before deployment, ensuring all build optimizations maintain production functionality.

## Table of Contents

1. [What are Integration Tests?](#what-are-integration-tests)
2. [Test Coverage](#test-coverage)
3. [Running Integration Tests](#running-integration-tests)
4. [Test Architecture](#test-architecture)
5. [CI/CD Integration](#cicd-integration)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

## What are Integration Tests?

Integration tests validate the complete end-to-end functionality of all Docker image variants. Unlike unit tests that test individual components, integration tests verify:

- **Complete workflows**: Build → Start → Request → Verify → Restart → Verify
- **Real container behavior**: Actual Docker containers running on the host
- **HTTP interactions**: Real HTTP requests to FastAPI endpoints
- **Process management**: Gunicorn master and worker processes
- **Configuration integrity**: All settings preserved across optimizations
- **Health and resilience**: Container stability and restart capability

## Test Coverage

### All Variants Tested

Integration tests cover all 6 production image variants:

| Variant | Python Version | Base Image | Type |
|---------|----------------|------------|------|
| python3.11 | 3.11 | tiangolo/uvicorn-gunicorn:python3.11 | Standard |
| python3.10 | 3.10 | tiangolo/uvicorn-gunicorn:python3.10 | Standard |
| python3.9 | 3.9 | tiangolo/uvicorn-gunicorn:python3.9 | Standard |
| python3.11-slim | 3.11 | tiangolo/uvicorn-gunicorn:python3.11-slim | Slim |
| python3.10-slim | 3.10 | tiangolo/uvicorn-gunicorn:python3.10-slim | Slim |
| python3.9-slim | 3.9 | tiangolo/uvicorn-gunicorn:python3.9-slim | Slim |

### Test Classes and Coverage

#### 1. TestImageBuild
**Purpose**: Verify images exist or can be built

**Tests**:
- Image availability check
- Buildability validation

**Why it matters**: Ensures all images are accessible before running functional tests.

#### 2. TestContainerStartup
**Purpose**: Validate container initialization

**Tests**:
- Container starts without errors
- FastAPI application initializes
- Uvicorn workers start successfully
- Prestart script executes

**Why it matters**: Container startup is the foundation for all other functionality.

#### 3. TestHTTPEndpoints
**Purpose**: Verify HTTP API functionality

**Tests**:
- Root endpoint (`/`) responds with 200 OK
- Response includes correct Python version
- Retry logic handles startup delays

**Why it matters**: Validates the primary purpose of these images - serving HTTP requests.

#### 4. TestPythonVersion
**Purpose**: Confirm correct Python version

**Tests**:
- Python version in container matches expected
- Version validation via `python --version`

**Why it matters**: Ensures images are built with the correct Python version.

#### 5. TestProcessManagement
**Purpose**: Validate process orchestration

**Tests**:
- Gunicorn master process running
- Worker processes active (≥2 total)
- Process hierarchy correct

**Why it matters**: Proper process management is critical for production reliability.

#### 6. TestGunicornConfiguration
**Purpose**: Verify server configuration

**Tests**:
- Workers per core setting (1)
- Host and port binding (0.0.0.0:80)
- Timeout settings (120s)
- Keepalive (5s)
- Log configuration (stdout/stderr)

**Why it matters**: Configuration correctness ensures optimal performance and observability.

#### 7. TestHealthAndReadiness
**Purpose**: Validate production readiness

**Tests**:
- Container remains healthy during operation
- Multiple requests handled successfully
- Container restart resilience

**Why it matters**: Production systems must handle restarts and sustained load.

#### 8. TestLogOutput
**Purpose**: Verify logging and observability

**Tests**:
- Startup sequence messages present
- Prestart script execution logged
- Application startup completion
- Access logs for requests

**Why it matters**: Proper logging enables debugging and monitoring in production.

#### 9. TestIntegrationSummary
**Purpose**: Provide overall test report

**Tests**:
- Variants tested summary
- Image availability report
- Comprehensive status overview

**Why it matters**: Gives a high-level view of test execution and results.

## Running Integration Tests

### Prerequisites

1. **Docker** (18.09+ with BuildKit)
   ```bash
   docker --version
   export DOCKER_BUILDKIT=1
   ```

2. **Python** (3.10+ recommended)
   ```bash
   python3 --version
   ```

3. **Python Dependencies**
   ```bash
   pip install pytest docker requests
   ```

### Quick Start

#### Run All Integration Tests

```bash
# Build images and run all integration tests
./scripts/test-integration.sh

# Output example:
# ================================
# Docker Image Integration Testing
# ================================
#
# Testing 6 variant(s)
#
# Building images...
# ✓ Built python3.9
# ✓ Built python3.10
# ...
#
# Running integration tests...
# Testing python3.9 (Python 3.9)...
# ✓ python3.9 tests passed
# ...
#
# ================================
# Integration Test Summary
# ================================
# Total variants tested: 6
# Passed: 6
# Failed: 0
# Total time: 180s
```

#### Test Specific Variant

```bash
# Test only python3.11-slim
./scripts/test-integration.sh --variant python3.11-slim

# Test with verbose output for debugging
./scripts/test-integration.sh --variant python3.11 --verbose
```

#### Quick Mode (Skip Slow Tests)

```bash
# Skip restart and health tests for faster execution
./scripts/test-integration.sh --quick

# Typical time: 2-3 minutes vs 3-5 minutes for full test
```

#### Using Existing Images

```bash
# Skip building, test existing images
./scripts/test-integration.sh --skip-build

# Typical time: 1-2 minutes
```

#### Clean Build and Test

```bash
# Rebuild without cache and test
./scripts/test-integration.sh --rebuild

# Typical time: 10-15 minutes (cold builds)
```

### Manual Test Execution

Build an image:
```bash
cd /code
export DOCKER_BUILDKIT=1
docker build -t tiangolo/uvicorn-gunicorn-fastapi:python3.11 \
  -f docker-images/python3.11.dockerfile \
  docker-images/
```

Run integration tests:
```bash
export NAME=python3.11
export PYTHON_VERSION=3.11
pytest tests/test_05_integration.py -v
```

Run specific test class:
```bash
pytest tests/test_05_integration.py::TestHTTPEndpoints -v
```

Run specific test method:
```bash
pytest tests/test_05_integration.py::TestHTTPEndpoints::test_root_endpoint_responds -v
```

## Test Architecture

### Design Principles

1. **Test Isolation**: Each test cleans up previous containers before starting
2. **Idempotency**: Tests can be run multiple times without side effects
3. **Retry Logic**: HTTP requests retry with exponential backoff
4. **Proper Cleanup**: Always clean up containers in finally blocks
5. **Environment-Aware**: Respects NAME env var for single-variant testing

### Port Configuration

Integration tests use **port 8001** (not default 8000) to avoid conflicts:

```python
CONTAINER_PORT = "80"       # Inside container
HOST_PORT = "8001"          # On host machine
```

This allows integration tests to run simultaneously with other tests.

### Timeout and Retry Settings

```python
CONTAINER_START_TIMEOUT = 10  # seconds
HTTP_RETRY_COUNT = 5
HTTP_RETRY_DELAY = 2          # seconds between retries
```

These settings handle various system speeds and startup times.

### Environment Variables

- **NAME**: Image variant name (e.g., `python3.11-slim`)
- **PYTHON_VERSION**: Python version (e.g., `3.11`)

If `NAME` is set, only that variant is tested (CI/CD optimization).

## CI/CD Integration

### GitHub Actions Workflow

Integration tests are designed to run in CI/CD pipelines:

```yaml
# Hypothetical workflow step
- name: Run Integration Tests
  run: |
    export NAME=${{ matrix.image.name }}
    export PYTHON_VERSION=${{ matrix.image.python_version }}
    pytest tests/test_05_integration.py -v
```

### Benefits in CI/CD

1. **Fast Execution**: Only tests relevant variant (via NAME env var)
2. **Comprehensive Validation**: All aspects tested before deployment
3. **Early Detection**: Catches issues before images are pushed
4. **Confidence Gate**: Ensures optimizations don't break functionality

### Recommended CI/CD Strategy

```bash
# Per-variant in matrix build
for variant in python3.9 python3.10 python3.11 python3.9-slim python3.10-slim python3.11-slim; do
  export NAME=$variant
  export PYTHON_VERSION=${variant#python}  # Extract version
  export PYTHON_VERSION=${PYTHON_VERSION%-slim}  # Remove -slim

  pytest tests/test_05_integration.py -v || exit 1
done
```

## Troubleshooting

### Common Issues

#### Port Already in Use

**Error**:
```
Error: port 8001 already allocated
```

**Solution**:
```bash
docker stop uvicorn-gunicorn-fastapi-test
docker rm uvicorn-gunicorn-fastapi-test

# Or use the script which handles cleanup automatically
./scripts/test-integration.sh
```

#### Container Won't Start

**Error**:
```
Container exited with code 1
```

**Solution**:
```bash
# Check container logs
docker logs uvicorn-gunicorn-fastapi-test

# Run with verbose mode
./scripts/test-integration.sh --verbose
```

#### HTTP Request Timeouts

**Error**:
```
requests.exceptions.ConnectionError: Connection refused
```

**Solution**:
- Increase `CONTAINER_START_TIMEOUT` if system is slow
- Check container logs for startup errors
- Verify port 8001 is not blocked by firewall

#### Image Not Found

**Error**:
```
ImageNotFound: tiangolo/uvicorn-gunicorn-fastapi:python3.11
```

**Solution**:
```bash
# Build missing images
./scripts/test-integration.sh --rebuild

# Or build specific image
docker build -t tiangolo/uvicorn-gunicorn-fastapi:python3.11 \
  -f docker-images/python3.11.dockerfile docker-images/
```

#### Tests Hang

**Symptoms**: Tests run indefinitely without completing

**Solution**:
- Check for orphaned containers: `docker ps -a`
- Kill hanging containers: `docker kill uvicorn-gunicorn-fastapi-test`
- Increase timeout values in test code
- Run with `--verbose` to see where it hangs

### Debug Mode

Run with maximum verbosity:

```bash
# Script verbose mode
./scripts/test-integration.sh --verbose

# Pytest verbose with output
pytest tests/test_05_integration.py -v -s

# Docker build verbose
DOCKER_BUILDKIT=1 docker build --progress=plain ...
```

## Best Practices

### For Developers

1. **Run Integration Tests Before Committing**
   ```bash
   # Quick validation
   ./scripts/test-integration.sh --quick --skip-build
   ```

2. **Test Specific Variant You Modified**
   ```bash
   ./scripts/test-integration.sh --variant python3.11-slim
   ```

3. **Use Quick Mode During Development**
   - Faster iterations
   - Full tests in CI/CD

4. **Check Logs on Failures**
   ```bash
   docker logs uvicorn-gunicorn-fastapi-test
   ```

### For CI/CD

1. **Run Full Integration Tests Before Deployment**
   - All variants
   - All test classes
   - No quick mode

2. **Use Matrix Strategy**
   - Test variants in parallel
   - Faster overall execution

3. **Cache Docker Images Between Jobs**
   - Faster test execution
   - Reduced build times

4. **Fail Fast on Integration Test Failures**
   - Don't deploy broken images
   - Integration tests are the final gate

### For Production

1. **Images That Pass Integration Tests Are Production-Ready**
   - All functionality validated
   - All configurations verified
   - Restart resilience tested

2. **Monitor Similar Metrics in Production**
   - Container health
   - Process management
   - Response times
   - Log output

3. **Use Same Configuration in Tests as Production**
   - Same base images
   - Same environment variables
   - Same port bindings

## Performance Expectations

### Execution Times

| Scenario | Expected Time | Notes |
|----------|--------------|-------|
| Single variant (skip-build) | 30-45s | Tests only |
| Single variant (with build, cached) | 1-2 min | Fast rebuild |
| Single variant (with build, no cache) | 3-5 min | Cold build |
| All variants (skip-build) | 3-4 min | Tests only |
| All variants (cached builds) | 5-8 min | Fast rebuilds |
| All variants (no cache) | 15-20 min | Cold builds |
| Quick mode (all variants) | 2-3 min | Skip slow tests |

### Resource Usage

- **CPU**: Moderate (Docker builds and container execution)
- **Memory**: ~2-4GB for all variants simultaneously
- **Disk**: ~5-10GB for all images
- **Network**: Minimal (only initial base image pulls)

## Summary

Integration tests provide comprehensive validation that:

✅ All 6 image variants build successfully
✅ Containers start and run correctly
✅ FastAPI application responds to HTTP requests
✅ Python versions are correct
✅ Gunicorn and Uvicorn processes work properly
✅ Configuration is preserved across optimizations
✅ Containers can restart successfully
✅ All logs contain expected startup messages

**Result**: Confidence that optimized images are production-ready.

## References

- **Test File**: `/code/tests/test_05_integration.py` (627 lines)
- **Test Script**: `/code/scripts/test-integration.sh` (333 lines)
- **Test README**: `/code/tests/README.md`
- **Build Optimization Guide**: `/code/docs/docker-build-optimization.md`
- **Build Scripts Guide**: `/code/docs/build-scripts-guide.md`
- **Multi-Arch Validation**: `/code/docs/multiarch-build-validation.md`

---

**Last Updated**: 2025-10-20
**Version**: 1.0 (Step 6.5 - Integration Testing for All Variants)
