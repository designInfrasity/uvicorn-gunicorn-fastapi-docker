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
├── test_02_build_optimization.py     # Build optimization validation tests
├── test_03_build_performance.py      # Build performance measurement tests
├── test_04_multiarch_validation.py   # Multi-architecture validation tests
├── test_05_integration.py            # Comprehensive integration tests
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

### Build Optimization Tests (test_02_build_optimization.py)

The build optimization test suite validates build-time optimizations are working correctly:


1. **Dockerignore Exclusions** (TestDockerignoreExclusions)
   - Verify .dockerignore file exists
   - Check exclusion of .git and .github directories
   - Validate test files and directories are excluded
   - Confirm documentation files (*.md) are excluded
   - Verify Python cache directories (__pycache__, *.pyc) are excluded

2. **Build Context Size** (TestBuildContextSize)
   - Validate build context size is under 50KB limit
   - Ensure .dockerignore effectively reduces build context
   - Parse and measure actual build context from Docker output

3. **Layer Optimization** (TestLayerOptimization)
   - Verify layer count is reasonable (≤ 15 layers)
   - Validate proper layer ordering (requirements before app code)
   - Ensure optimal caching structure

4. **BuildKit Cache Mount Syntax** (TestBuildKitCacheMountSyntax)
   - Verify BuildKit syntax directive (# syntax=docker/dockerfile:1)
   - Check cache mount configuration (--mount=type=cache)
   - Validate pip cache directory target (/root/.cache/pip)

5. **Dependency Installation** (TestDependencyInstallation)
   - Verify FastAPI is installed correctly
   - Verify Uvicorn is installed correctly
   - Confirm requirements.txt is removed from final image

6. **Unnecessary Files Exclusion** (TestUnnecessaryFilesExclusion)
   - Verify .git directory is NOT in final image
   - Verify tests directory is NOT in final image
   - Verify .github directory is NOT in final image
   - Confirm /app directory DOES exist
   - Confirm /app/main.py DOES exist

7. **Image Size Ranges** (TestImageSizeRanges)
   - Validate image sizes are reasonable
   - Standard images: 800-1200MB expected
   - Slim images: 300-600MB expected
   - Detect size regressions

**Test Count**: 20 test methods across 7 test classes
**Parametrization**: Tests run for all 6 image variants using pytest.mark.parametrize

### Build Performance Tests (test_03_build_performance.py)

The build performance test suite measures and validates build time improvements:

1. **Cold Build Performance** (TestColdBuildPerformance)
   - Measure baseline build times with --no-cache
   - Establish performance baselines for each variant

2. **Warm Build Performance** (TestWarmBuildPerformance)
   - Measure optimized build times with cache
   - Validate cache significantly improves build speed

3. **Cache Effectiveness** (TestCacheEffectiveness)
   - Calculate cache improvement percentage
   - Assert minimum 50% improvement threshold
   - Target 70%+ for optimal cache performance

4. **Image Size Validation** (TestImageSizeValidation)
   - Standard images must be < 1GB
   - Slim images must be < 500MB
   - Slim variants smaller than standard counterparts

5. **Build Performance Summary** (TestBuildPerformanceSummary)
   - Comprehensive reporting of all metrics
   - JSON output for historical tracking

**Test Count**: 24 test methods across 5 test classes
**Performance Tracking**: Results stored in `/tmp/build-performance-results.json`

### Multi-Architecture Validation Tests (test_04_multiarch_validation.py)

The multi-architecture test suite validates optimizations work across platforms:

1. **QEMU Setup** (TestQEMUSetup)
   - Verify QEMU emulation available
   - Check buildx installation
   - Validate builder instance configuration

2. **Multi-Arch Build Success** (TestMultiArchBuildSuccess)
   - Single-platform amd64 builds
   - Single-platform arm64 builds (emulated)
   - Multi-platform builds (both simultaneously)

3. **BuildKit Cache Multi-Arch** (TestBuildKitCacheMultiArch)
   - Cache effectiveness ≥30% for multi-arch
   - Validate cache works across architectures

4. **Image Functionality** (TestImageFunctionality)
   - Containers start on amd64
   - Containers start on arm64 (emulated)
   - Uvicorn/Gunicorn run correctly on both

5. **GitHub Actions Compatibility** (TestGitHubActionsCompatibility)
   - Workflow file validation
   - Multi-arch platform configuration
   - Buildx setup verification
   - Matrix variant coverage

6. **Multi-Arch Performance** (TestMultiArchPerformance)
   - Build time measurement for both platforms
   - Performance categorization (Excellent/Good/Fair/Slow)

7. **Dockerfile Optimization Preservation** (TestDockerfileOptimizationPreservation)
   - Layer ordering remains optimal
   - BuildKit syntax preserved
   - Cache mount configuration verified

**Test Count**: 47 test methods across 7 test classes
**Platforms**: linux/amd64, linux/arm64
**Script**: `/code/scripts/test-multiarch.sh` (comprehensive multi-arch test runner)

### Integration Tests (test_05_integration.py)

Comprehensive end-to-end integration tests for all optimized image variants:

1. **Image Build** (TestImageBuild)
   - Verify images exist or can be built
   - Validate all variants are available

2. **Container Startup** (TestContainerStartup)
   - Container starts without errors
   - FastAPI app initializes correctly
   - Uvicorn workers start successfully

3. **HTTP Endpoints** (TestHTTPEndpoints)
   - Root endpoint responds with 200 OK
   - Response contains correct Python version
   - Retry logic handles startup delays

4. **Python Version** (TestPythonVersion)
   - Verify Python version inside container
   - Match expected version for each variant

5. **Process Management** (TestProcessManagement)
   - Gunicorn master process running
   - Worker processes active (≥2 total)
   - Process inspection and validation

6. **Gunicorn Configuration** (TestGunicornConfiguration)
   - All default settings validated
   - Workers, timeout, binding, logging
   - Configuration matches expectations

7. **Health and Readiness** (TestHealthAndReadiness)
   - Container remains healthy during operation
   - Multiple requests handled successfully
   - Container restart resilience

8. **Log Output** (TestLogOutput)
   - Startup sequence messages present
   - Prestart script execution logged
   - Application startup completion
   - Access logs for requests

9. **Integration Summary** (TestIntegrationSummary)
   - Overall integration test report
   - Image availability check
   - Comprehensive status summary

**Test Count**: 17 test methods across 9 test classes
**Retry Logic**: HTTP requests with 5 retries, 2s delay
**Port**: Uses 8001 to avoid conflicts with other tests
**Script**: `/code/scripts/test-integration.sh` (comprehensive integration test runner)

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

#### Integration Tests (End-to-End)
```bash
# Run comprehensive integration tests for all variants
./scripts/test-integration.sh

# Test specific variant
./scripts/test-integration.sh --variant python3.11-slim

# Quick mode (skip slow tests)
./scripts/test-integration.sh --quick

# Rebuild images before testing
./scripts/test-integration.sh --rebuild --verbose
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

# Run runtime tests
pytest tests/test_01_main/test_defaults.py -v

# Run integration tests
pytest tests/test_05_integration.py -v

# Run all tests
pytest tests/ -v
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

### Step 6.2: Build Validation Tests ✅ COMPLETED
- ✅ Validate .dockerignore effectiveness
- ✅ Test build context size reduction
- ✅ Verify layer count optimization
- ✅ Check final image doesn't contain excluded files
- ✅ Verify BuildKit cache mount syntax
- ✅ Test dependency installation
- ✅ Validate image size ranges
- **File**: `test_02_build_optimization.py` (567 lines, 20 test methods)

### Step 6.3: Build Performance Tests
- Measure cold vs warm build times
- Calculate cache effectiveness
- Validate build time improvements (50%+ target)
- Test image size within expected ranges

### Step 6.4: Multi-Architecture Tests ✅ COMPLETED
- ✅ Test amd64 and arm64 builds separately
- ✅ Validate BuildKit cache works for multi-arch
- ✅ Ensure functionality on both architectures
- ✅ QEMU emulation for cross-platform testing
- ✅ GitHub Actions workflow validation
- **File**: `test_04_multiarch_validation.py` (608 lines, 47 test methods)

### Step 6.5: Integration Tests ✅ COMPLETED
- ✅ End-to-end tests for all variants
- ✅ Health check and readiness validation
- ✅ Container restart resilience
- ✅ HTTP endpoint testing with retries
- ✅ Python version verification
- ✅ Process management validation
- ✅ Gunicorn configuration testing
- ✅ Log output verification
- **File**: `test_05_integration.py` (693 lines, 8 test classes, 17+ test methods)
- **Script**: `/code/scripts/test-integration.sh` (comprehensive test runner)

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
