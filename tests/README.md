# Test Suite for Optimized Docker Images

This directory contains the test suite for validating the uvicorn-gunicorn-fastapi Docker images with build optimizations.

## Overview

The test suite validates that the optimized Dockerfiles produce functionally correct images that maintain all expected runtime behavior. The optimizations focus on build-time improvements (layer caching, build context reduction, BuildKit features) without affecting runtime functionality.

## Test Structure

```
tests/
├── README.md                          # This file
├── TEST_COMPATIBILITY_ANALYSIS.md     # Detailed compatibility analysis
├── test_01_main/                      # Runtime functionality tests
│   ├── __init__.py
│   └── test_defaults.py              # Main test suite
└── utils.py                          # Test utilities and helpers
```

## Test Coverage

### Current Tests (test_01_main/test_defaults.py)

The main test suite validates:

1. **Application Functionality**
   - FastAPI app responds correctly at root endpoint (`/`)
   - Response message includes correct Python version
   - JSON response format is correct

2. **Gunicorn Configuration**
   - Workers per core setting
   - Maximum workers configuration
   - Host and port binding (0.0.0.0:80)
   - Log level (info)
   - Worker count (>= 2)
   - Timeouts (graceful: 120s, timeout: 120s)
   - Keepalive settings (5s)
   - Error and access log configuration

3. **Environment Variables**
   - Implicitly validated through configuration checks
   - Base image environment properly propagated

4. **Startup Process**
   - Prestart script detection and execution (`/app/prestart.sh`)
   - Uvicorn worker initialization
   - Application startup completion
   - Request logging

5. **Container Lifecycle**
   - Container starts successfully
   - Container can be stopped and restarted
   - Configuration persists across restarts

### Image Variants Tested

All 6 production variants are tested:

| Variant | Python Version | Base Image |
|---------|----------------|------------|
| python3.11 | 3.11 | tiangolo/uvicorn-gunicorn:python3.11 |
| python3.10 | 3.10 | tiangolo/uvicorn-gunicorn:python3.10 |
| python3.9 | 3.9 | tiangolo/uvicorn-gunicorn:python3.9 |
| python3.11-slim | 3.11 | tiangolo/uvicorn-gunicorn:python3.11-slim |
| python3.10-slim | 3.10 | tiangolo/uvicorn-gunicorn:python3.10-slim |
| python3.9-slim | 3.9 | tiangolo/uvicorn-gunicorn:python3.9-slim |

## Running Tests

### Prerequisites

1. **Docker** (18.09+ with BuildKit support)
   ```bash
   docker --version
   export DOCKER_BUILDKIT=1
   ```

2. **Python** (3.10+ recommended)
   ```bash
   python --version
   ```

3. **Python Dependencies**
   ```bash
   pip install pytest docker requests
   ```

### Quick Start

#### Test All Variants (Recommended)
```bash
# Build and test all variants
./scripts/test-all-variants.sh

# Test existing images without rebuilding
./scripts/test-all-variants.sh --skip-build

# Clean build (no cache) and test
./scripts/test-all-variants.sh --no-cache
```

#### Test Single Variant
```bash
# Test specific variant
./scripts/test-all-variants.sh --variant python3.11-slim

# Verbose output for debugging
./scripts/test-all-variants.sh --variant python3.11 --verbose
```

#### Manual Test Execution

Build an image:
```bash
cd /code
export DOCKER_BUILDKIT=1
docker build -t tiangolo/uvicorn-gunicorn-fastapi:python3.11 \
  -f docker-images/python3.11.dockerfile \
  docker-images/
```

Run tests:
```bash
export NAME=python3.11
export PYTHON_VERSION=3.11
pytest tests/test_01_main/test_defaults.py -v
```

### CI/CD Testing

The GitHub Actions workflow automatically tests all variants:

**Workflow**: `.github/workflows/test.yml`

**Triggers**:
- Push to master branch
- Pull requests (opened, synchronized)
- Manual workflow dispatch
- Weekly schedule (Mondays)

**Matrix Strategy**: Tests all 7 image variants (including `latest` alias) across all triggers.

View workflow runs: https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker/actions

## Test Utilities

### utils.py

Provides helper functions for testing:

- `get_process_names(container)`: Extract Gunicorn process names
- `get_gunicorn_conf_path(container)`: Get Gunicorn configuration file path
- `get_config(container)`: Extract and parse Gunicorn configuration
- `remove_previous_container(client)`: Clean up test containers
- `get_logs(container)`: Retrieve container logs as string
- `get_response_text1()`: Generate expected response text with Python version

### Environment Variables

Tests rely on these environment variables:

- `NAME`: Image variant name (e.g., `python3.11`, `python3.10-slim`)
- `PYTHON_VERSION`: Python version string (e.g., `3.11`, `3.10`, `3.9`)
- `SLEEP_TIME`: Container startup wait time in seconds (default: 1)

## Optimized Dockerfile Compatibility

### Why No Test Changes Were Needed

The build optimizations are **transparent to runtime behavior**:

1. **Layer Ordering**: Only affects build caching, not runtime
2. **Build Context Reduction**: .dockerignore excludes files from build, not from image
3. **Dependency Installation**: Same dependencies, just installed more efficiently
4. **BuildKit Features**: Build-time performance features, runtime unchanged

### Key Compatibility Points

✅ **Base Images Unchanged**: Still using `tiangolo/uvicorn-gunicorn:pythonX.X` bases
✅ **Application Structure Identical**: Code still in `/app`, same file paths
✅ **Configuration Preserved**: All environment variables and settings from base image
✅ **Startup Process Identical**: Same prestart script, same initialization sequence

See `TEST_COMPATIBILITY_ANALYSIS.md` for detailed analysis.

## Test Development Guidelines

### Adding New Tests

When adding new tests for build optimizations:

1. **Separate Concerns**:
   - Runtime tests: Keep in `test_01_main/`
   - Build validation tests: Create in `test_02_build_optimization/` (Step 6.2)
   - Performance tests: Create in `test_03_build_performance/` (Step 6.3)

2. **Follow Existing Patterns**:
   - Use utilities from `utils.py`
   - Set environment variables (NAME, PYTHON_VERSION)
   - Clean up containers after tests
   - Use descriptive assertion messages

3. **Test All Variants**:
   - Use matrix or loop to test all 6 variants
   - Consider differences between standard and slim images
   - Test across Python versions (3.9, 3.10, 3.11)

### Test Naming Convention

- `test_01_main/`: Runtime functionality tests (existing)
- `test_02_build_optimization/`: Build validation tests (future - Step 6.2)
- `test_03_build_performance/`: Build performance tests (future - Step 6.3)
- `test_04_multi_arch/`: Multi-architecture tests (future - Step 6.4)

## Troubleshooting

### Common Issues

#### Port Already in Use
```
Error: port 8000 already allocated
```
**Solution**: Stop existing container or change test port:
```bash
docker stop uvicorn-gunicorn-fastapi-test
docker rm uvicorn-gunicorn-fastapi-test
```

#### Container Won't Start
```
Container exited immediately
```
**Solution**: Check container logs:
```bash
docker logs uvicorn-gunicorn-fastapi-test
```

#### Image Not Found
```
Error: Image not found: tiangolo/uvicorn-gunicorn-fastapi:python3.11
```
**Solution**: Build the image first:
```bash
docker build -t tiangolo/uvicorn-gunicorn-fastapi:python3.11 \
  -f docker-images/python3.11.dockerfile docker-images/
```

#### Tests Hang or Timeout
**Solution**: Increase SLEEP_TIME for slower systems:
```bash
export SLEEP_TIME=5
pytest tests/
```

#### Permission Denied on Docker Socket
```
Error: Permission denied while trying to connect to Docker daemon
```
**Solution**: Add user to docker group or run with sudo:
```bash
sudo usermod -aG docker $USER
# Then log out and log back in
```

### Debug Mode

Run tests with verbose output:
```bash
# Pytest verbose mode
pytest tests/test_01_main/test_defaults.py -v -s

# Script verbose mode
./scripts/test-all-variants.sh --verbose

# Docker build verbose mode
DOCKER_BUILDKIT=1 docker build --progress=plain ...
```

### Test Isolation

Each test run should:
1. Clean up previous containers: `remove_previous_container(client)`
2. Use unique container names: `CONTAINER_NAME = "uvicorn-gunicorn-fastapi-test"`
3. Stop and remove containers after tests: `container.stop()` + `container.remove()`

## Performance Expectations

### Build Times (with optimizations)

| Scenario | Expected Time | Cache Hit Rate |
|----------|--------------|----------------|
| Cold build (no cache) | 60-120s | 0% |
| Warm rebuild (no changes) | 1-3s | 90-98% |
| Code change only | 3-5s | 80% (4/5 layers) |
| Requirements change | 20-30s | 40% (2/5 layers) |

### Test Execution Times

| Test Scope | Expected Time |
|------------|--------------|
| Single variant | 10-15s (including build) |
| All variants (sequential) | 8-12 minutes (cold build) |
| All variants (sequential, warm cache) | 2-3 minutes |
| Single variant (skip build) | 5-8s (tests only) |

## Integration with CI/CD

### GitHub Actions Workflow

The test workflow integrates seamlessly with optimizations:

1. **Build Step**: Uses `docker/build-push-action@v6` with BuildKit
2. **Cache Configuration**: Registry cache enabled (cache-from/cache-to)
3. **Test Step**: Runs pytest with environment variables
4. **Matrix Strategy**: Tests all 7 variants in parallel

### Pre-commit Testing

Recommended pre-commit test command:
```bash
# Quick test: single variant
./scripts/test-all-variants.sh --variant python3.11 --skip-build

# Full test: all variants with fresh build
./scripts/test-all-variants.sh --no-cache
```

## Future Test Development (Roadmap)

### Step 6.2: Build Validation Tests
- Validate .dockerignore effectiveness
- Test build context size reduction
- Verify layer count optimization
- Check final image doesn't contain excluded files

### Step 6.3: Build Performance Tests
- Measure cold vs warm build times
- Calculate cache effectiveness
- Validate build time improvements (50%+ target)
- Test image size within expected ranges

### Step 6.4: Multi-Architecture Tests
- Test amd64 and arm64 builds separately
- Validate BuildKit cache works for multi-arch
- Ensure functionality on both architectures

### Step 6.5: Integration Tests
- End-to-end tests for all variants
- Health check and readiness validation
- Load testing with multiple workers
- Container restart resilience

## Contributing

When contributing test improvements:

1. **Maintain backward compatibility**: Don't break existing tests
2. **Test locally first**: Run full test suite before committing
3. **Update documentation**: Keep this README and analysis docs current
4. **Follow conventions**: Use existing patterns and utilities
5. **Add coverage**: Include new tests for new features

## References

- **Test Compatibility Analysis**: `TEST_COMPATIBILITY_ANALYSIS.md`
- **Build Optimization Guide**: `/code/docs/docker-build-optimization.md`
- **Build Scripts Guide**: `/code/docs/build-scripts-guide.md`
- **Test Script**: `/code/scripts/test-all-variants.sh`
- **GitHub Actions Workflow**: `/code/.github/workflows/test.yml`
- **Original Repository**: https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test compatibility analysis
3. Check GitHub Actions workflow runs
4. Review Docker and pytest documentation
5. Open an issue on GitHub (if applicable)

---

**Last Updated**: 2025-10-20
**Test Suite Version**: 1.0 (Step 6.1 - Optimized Dockerfile Compatibility)
