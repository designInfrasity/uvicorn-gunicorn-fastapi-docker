# Build Scripts Guide

**Repository**: uvicorn-gunicorn-fastapi-docker
**Last Updated**: 2025-10-20
**Audience**: Developers working with Docker image builds locally

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Build Script (build.sh)](#build-script-buildsh)
4. [Performance Monitoring Script (measure-build-metrics.sh)](#performance-monitoring-script-measure-build-metricssh)
5. [Test Build Script (test-optimized-build.sh)](#test-build-script-test-optimized-buildsh)
6. [Common Workflows](#common-workflows)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This guide documents the build scripts created to streamline the Docker image build process for local development. These scripts provide convenient wrappers around Docker build commands, enable performance monitoring, and automate testing of built images.

### Available Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `build.sh` | Build Docker images with optimization | `/code/scripts/build.sh` |
| `measure-build-metrics.sh` | Track build performance metrics | `/code/scripts/measure-build-metrics.sh` |
| `test-optimized-build.sh` | Validate built images | `/code/scripts/test-optimized-build.sh` |

### Why Use These Scripts?

- **Convenience**: Simple commands instead of long docker build invocations
- **Performance**: Automatic BuildKit enablement and parallel build support
- **Visibility**: Real-time feedback on build times and image sizes
- **Quality**: Automated testing ensures builds produce functional images
- **Metrics**: Track performance improvements over time

---

## Prerequisites

### Required Software

1. **Docker 18.09+** with BuildKit support
   ```bash
   docker version
   # Docker version 18.09 or higher required
   ```

2. **Bash 4.0+** (usually pre-installed on Linux/macOS)
   ```bash
   bash --version
   # GNU bash, version 4.0 or higher
   ```

3. **Git** (for commit tracking in metrics)
   ```bash
   git --version
   ```

### Optional Software

- **Python 3.6+** (for enhanced metrics comparison features)
- **curl** (for HTTP endpoint testing)
- **jq** (for JSON parsing)

### Enable BuildKit

While the scripts automatically enable BuildKit, you can set it permanently:

```bash
# Add to ~/.bashrc or ~/.zshrc
export DOCKER_BUILDKIT=1

# Or configure in Docker daemon.json
echo '{ "features": { "buildkit": true } }' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

### Clone Repository

```bash
git clone https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker.git
cd uvicorn-gunicorn-fastapi-docker
```

---

## Build Script (build.sh)

### Overview

`build.sh` is the primary script for building Docker images locally. It provides a convenient interface for building single variants, all variants, with parallel execution support and performance monitoring.

**Location**: `/code/scripts/build.sh`

### Basic Usage

```bash
# Make script executable (first time only)
chmod +x /code/scripts/build.sh

# Build a single variant
/code/scripts/build.sh python3.11

# Build all variants
/code/scripts/build.sh all
```

### Syntax

```bash
./scripts/build.sh [OPTIONS] <VARIANT>
```

### Available Variants

The script supports all 6 image variants:

| Variant | Base Image | Use Case |
|---------|------------|----------|
| `python3.9` | Standard Python 3.9 | Development, full tooling |
| `python3.10` | Standard Python 3.10 | Development, full tooling |
| `python3.11` | Standard Python 3.11 | Development, full tooling |
| `python3.9-slim` | Slim Python 3.9 | Production, minimal size |
| `python3.10-slim` | Slim Python 3.10 | Production, minimal size |
| `python3.11-slim` | Slim Python 3.11 | Production, minimal size |
| `all` | All variants | Build everything |

### Command Options

#### `--no-cache`

Build without using Docker cache (clean build from scratch).

**Usage**:
```bash
./scripts/build.sh --no-cache python3.11
```

**When to use**:
- Testing Dockerfile changes from scratch
- Troubleshooting cache issues
- Verifying dependencies install correctly
- Creating baseline performance metrics

**Build time**: 90-120 seconds per variant (no cache benefits)

#### `--parallel`

Build multiple variants in parallel using background jobs.

**Usage**:
```bash
# Build all variants in parallel
./scripts/build.sh --parallel all

# Build multiple specific variants in parallel
./scripts/build.sh --parallel python3.9 python3.10 python3.11
```

**When to use**:
- Building multiple variants
- Faster iteration during development
- Taking advantage of multi-core CPUs

**Performance**:
- Sequential builds: ~6-10 minutes for all variants
- Parallel builds: ~2-4 minutes for all variants (on 4+ core CPU)

**Note**: Output is buffered and displayed after each variant completes to avoid interleaved logs.

#### `--verbose`

Show detailed Docker build output.

**Usage**:
```bash
./scripts/build.sh --verbose python3.11
```

**When to use**:
- Debugging build issues
- Understanding layer cache behavior
- Investigating performance problems
- Seeing full pip install output

#### `--help`

Display usage information and examples.

**Usage**:
```bash
./scripts/build.sh --help
```

### Common Scenarios

#### Scenario 1: Build Single Variant

Build the python3.11-slim image for quick testing.

```bash
./scripts/build.sh python3.11-slim
```

**Expected output**:
```
[INFO] Building Docker images...
[INFO] BuildKit enabled: DOCKER_BUILDKIT=1
[INFO] Building variant: python3.11-slim
[INFO] Build started at: 2025-10-20 10:30:00
[+] Building 3.2s (12/12) FINISHED
[SUCCESS] Built: python3.11-slim (3.2s, 470MB)
[INFO] Total time: 3 seconds
```

**Build time**:
- Cold build: ~120s
- Warm build (with cache): ~2-3s
- Code change: ~3-5s

#### Scenario 2: Build All Variants (Sequential)

Build all 6 variants one after another.

```bash
./scripts/build.sh all
```

**Expected output**:
```
[INFO] Building all variants sequentially...
[INFO] Building variant: python3.9
[SUCCESS] Built: python3.9 (2.1s, 950MB)
[INFO] Building variant: python3.10
[SUCCESS] Built: python3.10 (2.3s, 980MB)
[INFO] Building variant: python3.11
[SUCCESS] Built: python3.11 (2.2s, 1.0GB)
[INFO] Building variant: python3.9-slim
[SUCCESS] Built: python3.9-slim (2.8s, 450MB)
[INFO] Building variant: python3.10-slim
[SUCCESS] Built: python3.10-slim (2.9s, 460MB)
[INFO] Building variant: python3.11-slim
[SUCCESS] Built: python3.11-slim (3.0s, 470MB)
[INFO] Total time: 15 seconds
[INFO] Success: 6, Failed: 0
```

**Total build time**:
- Cold build: ~10-12 minutes
- Warm build: ~15-20 seconds

#### Scenario 3: Clean Build Without Cache

Perform a clean build to verify Dockerfile changes work from scratch.

```bash
./scripts/build.sh --no-cache python3.11
```

**Use case**:
- After modifying Dockerfile
- Verifying dependencies install correctly
- Creating baseline performance metrics
- Troubleshooting cache-related issues

**Expected output**:
```
[INFO] Building with --no-cache flag
[INFO] Building variant: python3.11
[INFO] Build started at: 2025-10-20 10:30:00
[+] Building 92.4s (12/12) FINISHED
[SUCCESS] Built: python3.11 (92.4s, 1.0GB)
```

**Build time**: 90-120 seconds (full dependency download and installation)

#### Scenario 4: Parallel Builds for Faster Iteration

Build all variants in parallel to save time.

```bash
./scripts/build.sh --parallel all
```

**Expected output**:
```
[INFO] Building all variants in parallel...
[INFO] Starting build: python3.9 (PID: 12345, log: /tmp/build-python3.9.log)
[INFO] Starting build: python3.10 (PID: 12346, log: /tmp/build-python3.10.log)
[INFO] Starting build: python3.11 (PID: 12347, log: /tmp/build-python3.11.log)
[INFO] Starting build: python3.9-slim (PID: 12348, log: /tmp/build-python3.9-slim.log)
[INFO] Starting build: python3.10-slim (PID: 12349, log: /tmp/build-python3.10-slim.log)
[INFO] Starting build: python3.11-slim (PID: 12350, log: /tmp/build-python3.11-slim.log)
[INFO] Waiting for parallel builds to complete...
[SUCCESS] Built: python3.9 (2.3s, 950MB)
[SUCCESS] Built: python3.10 (2.5s, 980MB)
[SUCCESS] Built: python3.11 (2.4s, 1.0GB)
[SUCCESS] Built: python3.9-slim (3.1s, 450MB)
[SUCCESS] Built: python3.10-slim (3.2s, 460MB)
[SUCCESS] Built: python3.11-slim (3.3s, 470MB)
[INFO] Total time: 8 seconds
[INFO] Success: 6, Failed: 0
```

**Performance gain**:
- Sequential: ~15-20s for all variants
- Parallel: ~5-8s for all variants (on 4+ core CPU)
- **Speedup**: ~2-3x faster

#### Scenario 5: Verbose Build for Debugging

See detailed output to debug build issues.

```bash
./scripts/build.sh --verbose python3.11-slim
```

**Expected output**:
```
[INFO] Building variant: python3.11-slim with verbose output
[+] Building 3.2s (12/12) FINISHED
=> [internal] load build definition from python3.11-slim.dockerfile
=> => transferring dockerfile: 876B
=> [internal] load .dockerignore
=> => transferring context: 619B
=> [internal] load metadata for docker.io/tiangolo/uvicorn-gunicorn:python3.11-slim
=> [builder 1/4] FROM python:3.11-slim@sha256:...
=> CACHED [builder 2/4] RUN apt-get update && apt-get install...
=> CACHED [builder 3/4] COPY requirements.txt /tmp/requirements.txt
=> CACHED [builder 4/4] RUN --mount=type=cache,target=/root/.cache/pip...
=> [stage-1 1/3] FROM docker.io/tiangolo/uvicorn-gunicorn:python3.11-slim
=> CACHED [stage-1 2/3] COPY --from=builder /usr/local/lib/python3.11/site-packages...
=> [stage-1 3/3] COPY ./app /app
=> exporting to image
[SUCCESS] Built: python3.11-slim (3.2s, 470MB)
```

**Use case**:
- Understanding which layers are cached
- Debugging build failures
- Verifying cache mount is working
- Seeing pip package installation details

#### Scenario 6: Build Specific Subset

Build only standard (non-slim) variants.

```bash
./scripts/build.sh python3.9 python3.10 python3.11
```

**Expected output**:
```
[INFO] Building variants: python3.9 python3.10 python3.11
[SUCCESS] Built: python3.9 (2.1s, 950MB)
[SUCCESS] Built: python3.10 (2.3s, 980MB)
[SUCCESS] Built: python3.11 (2.2s, 1.0GB)
[INFO] Total time: 7 seconds
[INFO] Success: 3, Failed: 0
```

### Output Information

The script provides the following information for each build:

1. **Build time**: How long the build took (in seconds)
2. **Image size**: Final image size (in MB/GB)
3. **Cache status**: Which layers were cached (in verbose mode)
4. **Success/failure status**: Whether the build succeeded
5. **Error details**: Full error output if build fails

### Environment Variables

The script automatically sets:

```bash
DOCKER_BUILDKIT=1          # Enable BuildKit features
BUILDKIT_PROGRESS=auto     # Auto-detect progress output format
```

You can override these:

```bash
# Use plain progress for CI/CD
BUILDKIT_PROGRESS=plain ./scripts/build.sh python3.11

# Disable BuildKit (not recommended)
DOCKER_BUILDKIT=0 ./scripts/build.sh python3.11
```

### Script Location and Paths

The script assumes the following directory structure:

```
/code/
├── scripts/
│   └── build.sh              ← Script location
└── docker-images/
    ├── python3.9.dockerfile
    ├── python3.10.dockerfile
    ├── python3.11.dockerfile
    ├── python3.9-slim.dockerfile
    ├── python3.10-slim.dockerfile
    ├── python3.11-slim.dockerfile
    ├── requirements.txt
    ├── app/
    └── .dockerignore
```

**Important**: Always run the script from the `/code` directory or use absolute paths.

```bash
# From /code directory
./scripts/build.sh python3.11

# From anywhere using absolute path
/code/scripts/build.sh python3.11

# Or add to PATH
export PATH=$PATH:/code/scripts
build.sh python3.11
```

---

## Performance Monitoring Script (measure-build-metrics.sh)

### Overview

`measure-build-metrics.sh` tracks build performance metrics over time, helping you monitor the effectiveness of optimizations and detect performance regressions.

**Location**: `/code/scripts/measure-build-metrics.sh`

### Basic Usage

```bash
# Measure metrics for all variants
./scripts/measure-build-metrics.sh

# Skip uncached builds (faster, cached metrics only)
./scripts/measure-build-metrics.sh --skip-uncached

# Compare against baseline
./scripts/measure-build-metrics.sh --baseline
```

### Syntax

```bash
./scripts/measure-build-metrics.sh [OPTIONS]
```

### Command Options

#### `--skip-uncached`

Skip uncached (cold) builds to save time during development.

**Usage**:
```bash
./scripts/measure-build-metrics.sh --skip-uncached
```

**When to use**:
- During active development
- Quick cache effectiveness checks
- When uncached metrics aren't needed

**Time savings**:
- Full run: ~10-15 minutes
- Skip uncached: ~30-60 seconds

#### `--baseline`

Establish or compare against a baseline metrics file.

**Usage**:
```bash
# First run: establish baseline
./scripts/measure-build-metrics.sh --baseline

# Subsequent runs: compare against baseline
./scripts/measure-build-metrics.sh --baseline
```

**When to use**:
- After implementing optimizations (establish new baseline)
- Before/after Dockerfile changes (comparison)
- Tracking performance over time
- Detecting regressions

#### `--verbose`

Show detailed Docker build output during measurements.

**Usage**:
```bash
./scripts/measure-build-metrics.sh --verbose
```

#### `--help`

Display usage information.

**Usage**:
```bash
./scripts/measure-build-metrics.sh --help
```

### What Gets Measured

For each variant, the script measures:

1. **Build Time (Cached)**: Time to rebuild with full cache
2. **Build Time (Uncached)**: Time to build from scratch (--no-cache)
3. **Image Size**: Final image size in human-readable format
4. **Layer Count**: Number of layers in the final image
5. **Cache Effectiveness**: Percentage improvement from caching
6. **Git Commit**: Current git commit hash
7. **Timestamp**: When the measurement was taken

### Output Format

Metrics are saved to `/code/build-metrics.json` in the following format:

```json
{
  "timestamp": "2025-10-20T10:30:00Z",
  "git_commit": "a1890cf",
  "variants": {
    "python3.11": {
      "cached_build_time": 2.3,
      "uncached_build_time": 92.4,
      "image_size": "1.0GB",
      "layer_count": 5,
      "cache_effectiveness": "97.5%"
    },
    "python3.11-slim": {
      "cached_build_time": 3.1,
      "uncached_build_time": 118.6,
      "image_size": "470MB",
      "layer_count": 8,
      "cache_effectiveness": "97.4%"
    }
  }
}
```

### Common Scenarios

#### Scenario 1: Quick Cache Check

Measure only cached build performance (skip slow uncached builds).

```bash
./scripts/measure-build-metrics.sh --skip-uncached
```

**Expected output**:
```
[INFO] Measuring build metrics for all variants
[INFO] Skipping uncached builds (--skip-uncached flag)
[INFO] Measuring python3.9...
  Cached build time: 2.1s
  Image size: 950MB
  Layer count: 5
[INFO] Measuring python3.10...
  Cached build time: 2.3s
  Image size: 980MB
  Layer count: 5
[INFO] Measuring python3.11...
  Cached build time: 2.2s
  Image size: 1.0GB
  Layer count: 5
[INFO] Measuring python3.9-slim...
  Cached build time: 2.8s
  Image size: 450MB
  Layer count: 8
[INFO] Measuring python3.10-slim...
  Cached build time: 2.9s
  Image size: 460MB
  Layer count: 8
[INFO] Measuring python3.11-slim...
  Cached build time: 3.0s
  Image size: 470MB
  Layer count: 8
[INFO] Metrics saved to: /code/build-metrics.json
[INFO] Total time: 45 seconds
```

**Use case**:
- Regular development workflow
- Quick performance checks
- Verifying cache is working

**Duration**: ~30-60 seconds

#### Scenario 2: Full Metrics Collection

Measure both cached and uncached build times for comprehensive metrics.

```bash
./scripts/measure-build-metrics.sh
```

**Expected output**:
```
[INFO] Measuring build metrics for all variants
[INFO] Measuring python3.9...
  Uncached build time: 90.2s
  Cached build time: 2.1s
  Cache effectiveness: 97.7%
  Image size: 950MB
  Layer count: 5
[INFO] Measuring python3.10...
  Uncached build time: 91.5s
  Cached build time: 2.3s
  Cache effectiveness: 97.5%
  Image size: 980MB
  Layer count: 5
[... continues for all variants ...]
[INFO] Metrics saved to: /code/build-metrics.json
[INFO] Total time: 12 minutes 34 seconds
```

**Use case**:
- Baseline establishment
- Performance validation after optimizations
- Comprehensive performance reports
- Before/after comparisons

**Duration**: ~10-15 minutes

#### Scenario 3: Establish Performance Baseline

Create a baseline for future comparisons.

```bash
# First run: establish baseline
./scripts/measure-build-metrics.sh --baseline
```

**Expected output**:
```
[INFO] Establishing baseline metrics
[INFO] Measuring build metrics for all variants
[... measurement output ...]
[INFO] Metrics saved to: /code/build-metrics.json
[INFO] Baseline saved to: /code/build-metrics-baseline.json
[INFO] Future runs with --baseline will compare against this baseline
```

**Use case**:
- After implementing optimizations
- Before making major Dockerfile changes
- Setting performance targets

#### Scenario 4: Compare Against Baseline

Compare current performance against established baseline.

```bash
# Subsequent run: compare against baseline
./scripts/measure-build-metrics.sh --baseline
```

**Expected output**:
```
[INFO] Comparing against baseline metrics
[INFO] Measuring build metrics for all variants
[... measurement output ...]
[INFO] Metrics saved to: /code/build-metrics.json

[INFO] Comparison vs Baseline:
python3.9:
  Cached build time: 2.1s (baseline: 2.3s) ↓ 0.2s faster
  Uncached build time: 90.2s (baseline: 92.5s) ↓ 2.3s faster
  Image size: 950MB (baseline: 980MB) ↓ 30MB smaller
  Layer count: 5 (baseline: 6) ↓ 1 layer removed

python3.10:
  Cached build time: 2.3s (baseline: 2.5s) ↓ 0.2s faster
  Uncached build time: 91.5s (baseline: 91.0s) ↑ 0.5s slower
  Image size: 980MB (baseline: 980MB) = no change
  Layer count: 5 (baseline: 5) = no change

[... continues for all variants ...]
```

**Indicators**:
- ↓ = Improvement (faster/smaller)
- ↑ = Regression (slower/larger)
- = No change

**Use case**:
- After making Dockerfile changes
- Validating optimizations worked
- Detecting performance regressions
- Tracking improvements over time

### Interpreting Metrics

#### Cache Effectiveness

```
Cache Effectiveness = ((Uncached Time - Cached Time) / Uncached Time) × 100
```

**Expected values**:
- **90-98%**: Excellent (optimized builds)
- **70-89%**: Good (some optimization)
- **50-69%**: Fair (needs improvement)
- **<50%**: Poor (cache not working effectively)

**Example**:
- Uncached: 90s
- Cached: 2s
- Effectiveness: ((90-2)/90) × 100 = 97.8%

#### Build Time Targets

| Build Type | Target Time | Status |
|-----------|-------------|---------|
| Cached build | <5s | Excellent |
| Cached build | 5-10s | Good |
| Cached build | >10s | Needs investigation |
| Uncached build (standard) | <120s | Normal |
| Uncached build (slim) | <150s | Normal |

#### Image Size Targets

| Variant | Target Size | Status |
|---------|-------------|--------|
| Standard (python3.9-3.11) | <1.1GB | Normal |
| Slim (python3.9-slim to 3.11-slim) | <500MB | Excellent |
| Slim (python3.9-slim to 3.11-slim) | 500-600MB | Good |

#### Layer Count

| Image Type | Expected Layers | Notes |
|-----------|----------------|-------|
| Standard | 5 layers | FROM, LABEL, COPY requirements, RUN pip, COPY app |
| Slim (multi-stage) | 8 layers | 4 builder + 4 runtime |

**Red flag**: Unexpected layer count increase may indicate:
- Unnecessary RUN commands added
- Dockerfile structure changed
- Cleanup operations separated from creation

### Tracking Metrics Over Time

Commit metrics to git to track performance trends:

```bash
# After measuring
git add build-metrics.json
git commit -m "chore: update build metrics after optimization"

# View historical metrics
git log --oneline --all -- build-metrics.json
```

Use this data to:
- Track optimization improvements
- Detect regressions
- Report performance gains
- Make data-driven decisions

---

## Test Build Script (test-optimized-build.sh)

### Overview

`test-optimized-build.sh` validates that optimized Docker builds produce correct, functional artifacts. It automates testing of built images to ensure optimizations haven't broken functionality.

**Location**: `/code/scripts/test-optimized-build.sh`

### Basic Usage

```bash
# Test a single variant
./scripts/test-optimized-build.sh python3.11

# Test all variants
./scripts/test-optimized-build.sh all
```

### Syntax

```bash
./scripts/test-optimized-build.sh [OPTIONS] <VARIANT>
```

### Command Options

#### `--quick`

Skip rebuilding images, test existing images only.

**Usage**:
```bash
./scripts/test-optimized-build.sh --quick python3.11
```

**When to use**:
- Images already built
- Quick validation
- CI/CD pipelines (images built separately)

**Time savings**: ~2-3 minutes per variant

#### `--python VERSION`

Test only specific Python version variants.

**Usage**:
```bash
./scripts/test-optimized-build.sh --python 3.11
# Tests both python3.11 and python3.11-slim
```

#### `--slim-only`

Test only slim variants.

**Usage**:
```bash
./scripts/test-optimized-build.sh --slim-only
# Tests python3.9-slim, python3.10-slim, python3.11-slim
```

#### `--standard-only`

Test only standard (non-slim) variants.

**Usage**:
```bash
./scripts/test-optimized-build.sh --standard-only
# Tests python3.9, python3.10, python3.11
```

#### `--verbose`

Show detailed test output and container logs.

**Usage**:
```bash
./scripts/test-optimized-build.sh --verbose python3.11
```

### Test Coverage

For each variant, the script validates:

1. **Build Success**: Image builds without errors
2. **Container Start**: Container starts successfully
3. **HTTP Endpoint**: FastAPI app responds on port 80
4. **Python Version**: Correct Python version in response
5. **File Presence**: `/app/main.py` exists
6. **File Executability**: Application files are executable
7. **Python Syntax**: Application code is valid Python
8. **Environment Variables**: Expected env vars are set
9. **Processes**: Gunicorn and Uvicorn processes are running
10. **Logs**: Container logs show expected startup messages

### Common Scenarios

#### Scenario 1: Test Single Variant

Test python3.11-slim image after building.

```bash
./scripts/test-optimized-build.sh python3.11-slim
```

**Expected output**:
```
[INFO] Testing variant: python3.11-slim
[INFO] Building image: python3.11-slim
[+] Building 3.2s (12/12) FINISHED
[INFO] Starting container: test-python3.11-slim
[INFO] Waiting for container to be ready...
[TEST] Checking HTTP endpoint... ✓ PASS
[TEST] Checking Python version in response... ✓ PASS
[TEST] Checking /app/main.py exists... ✓ PASS
[TEST] Checking /app/main.py is executable... ✓ PASS
[TEST] Validating Python syntax... ✓ PASS
[TEST] Checking environment variables... ✓ PASS
[TEST] Checking Gunicorn process... ✓ PASS
[TEST] Checking Uvicorn workers... ⚠ WARNING (not visible in ps)
[TEST] Checking container logs... ✓ PASS
[TEST] Checking image size... ✓ PASS (470MB)
[INFO] Cleaning up container...
[SUCCESS] python3.11-slim: 9/10 tests passed
[INFO] Total time: 8 seconds
```

**Test duration**: ~5-10 seconds per variant

#### Scenario 2: Test All Variants

Test all 6 variants to ensure consistency.

```bash
./scripts/test-optimized-build.sh all
```

**Expected output**:
```
[INFO] Testing all variants
[INFO] Testing variant: python3.9
[... test output ...]
[SUCCESS] python3.9: 10/10 tests passed

[INFO] Testing variant: python3.10
[... test output ...]
[SUCCESS] python3.10: 10/10 tests passed

[INFO] Testing variant: python3.11
[... test output ...]
[SUCCESS] python3.11: 10/10 tests passed

[INFO] Testing variant: python3.9-slim
[... test output ...]
[SUCCESS] python3.9-slim: 9/10 tests passed

[INFO] Testing variant: python3.10-slim
[... test output ...]
[SUCCESS] python3.10-slim: 9/10 tests passed

[INFO] Testing variant: python3.11-slim
[... test output ...]
[SUCCESS] python3.11-slim: 9/10 tests passed

[INFO] Summary:
  Total tests: 60
  Passed: 58
  Failed: 0
  Warnings: 2
[SUCCESS] All variants tested successfully
[INFO] Total time: 48 seconds
```

**Test duration**: ~45-60 seconds for all variants

#### Scenario 3: Quick Test Without Rebuild

Test existing images without rebuilding (fast validation).

```bash
./scripts/test-optimized-build.sh --quick python3.11
```

**Expected output**:
```
[INFO] Quick mode: skipping rebuild
[INFO] Testing variant: python3.11
[INFO] Using existing image: tiangolo/uvicorn-gunicorn-fastapi:python3.11
[... test output ...]
[SUCCESS] python3.11: 10/10 tests passed
[INFO] Total time: 5 seconds
```

**Use case**:
- Images already built
- Fast validation in CI/CD
- Testing after manual builds
- Rapid iteration during development

**Time savings**: ~2-3 minutes per variant (no rebuild)

#### Scenario 4: Test Only Slim Variants

Test only production-ready slim variants.

```bash
./scripts/test-optimized-build.sh --slim-only
```

**Expected output**:
```
[INFO] Testing slim variants only
[INFO] Testing variant: python3.9-slim
[SUCCESS] python3.9-slim: 9/10 tests passed
[INFO] Testing variant: python3.10-slim
[SUCCESS] python3.10-slim: 9/10 tests passed
[INFO] Testing variant: python3.11-slim
[SUCCESS] python3.11-slim: 9/10 tests passed
[INFO] Summary: 3/3 variants passed
[INFO] Total time: 24 seconds
```

**Use case**:
- Testing production images
- Validating multi-stage builds
- Verifying slim image optimizations

#### Scenario 5: Test Specific Python Version

Test all variants for Python 3.11 (standard and slim).

```bash
./scripts/test-optimized-build.sh --python 3.11
```

**Expected output**:
```
[INFO] Testing Python 3.11 variants
[INFO] Testing variant: python3.11
[SUCCESS] python3.11: 10/10 tests passed
[INFO] Testing variant: python3.11-slim
[SUCCESS] python3.11-slim: 9/10 tests passed
[INFO] Summary: 2/2 variants passed
[INFO] Total time: 16 seconds
```

**Use case**:
- Testing specific Python version changes
- Validating version-specific behavior
- Focused testing during development

#### Scenario 6: Verbose Test Output

See detailed test output and container logs for debugging.

```bash
./scripts/test-optimized-build.sh --verbose python3.11
```

**Expected output**:
```
[INFO] Testing variant: python3.11 (verbose mode)
[INFO] Building image: python3.11
[... detailed docker build output ...]
[INFO] Starting container: test-python3.11
[DEBUG] Container ID: 8f2b4c9d1a3e
[DEBUG] Container port: 8001
[INFO] Waiting for container to be ready...
[TEST] Checking HTTP endpoint...
[DEBUG] $ curl -f http://localhost:8001/
[DEBUG] Response: {"message":"Hello World from Python 3.11"}
[DEBUG] HTTP status: 200
✓ PASS

[TEST] Checking Python version in response...
[DEBUG] Expected: 3.11
[DEBUG] Found: 3.11
✓ PASS

[TEST] Checking /app/main.py exists...
[DEBUG] $ docker exec test-python3.11 test -f /app/main.py
[DEBUG] Exit code: 0
✓ PASS

[... detailed output for all tests ...]

[TEST] Checking container logs...
[DEBUG] Container logs:
Checking for script in /app/prestart.sh
Running script /app/prestart.sh
Running inside /app/prestart.sh, you could add migrations to this file, e.g.:
Uvicorn running on http://0.0.0.0:80 (Press CTRL+C to quit)
[2025-10-20 10:30:00] [INFO] Gunicorn listening at: http://0.0.0.0:80
✓ PASS

[INFO] Cleaning up container...
[SUCCESS] python3.11: 10/10 tests passed
```

### Test Exit Codes

The script uses proper exit codes for CI/CD integration:

| Exit Code | Meaning |
|-----------|---------|
| 0 | All tests passed |
| 1 | One or more tests failed |
| 2 | Script usage error (invalid arguments) |

**Usage in CI/CD**:
```yaml
- name: Test built images
  run: |
    ./scripts/test-optimized-build.sh --quick all
  # CI will fail if exit code != 0
```

### Understanding Test Results

#### PASS ✓

Test completed successfully. No action needed.

#### WARNING ⚠

Test passed but with caveats. Common warnings:
- Uvicorn worker not visible in `ps aux` (normal for some configurations)
- Image size slightly larger than expected (may indicate bloat)

Warnings don't fail the test but should be investigated.

#### FAIL ✗

Test failed. Possible causes:
- Build failed (Dockerfile syntax error, dependency issue)
- Container failed to start (configuration error)
- HTTP endpoint not responding (application error)
- File missing (COPY command issue in Dockerfile)
- Python syntax error (application code issue)
- Environment variable not set (configuration issue)

Check verbose output and container logs for details.

---

## Common Workflows

### Workflow 1: Regular Development

Daily development workflow with frequent code changes.

```bash
# 1. Make code changes
vim docker-images/app/main.py

# 2. Build changed variant
./scripts/build.sh python3.11

# 3. Test the build
./scripts/test-optimized-build.sh --quick python3.11

# 4. Run container manually for testing
docker run -d -p 8000:80 --name dev tiangolo/uvicorn-gunicorn-fastapi:python3.11
curl http://localhost:8000

# 5. Cleanup
docker stop dev && docker rm dev
```

**Expected duration**: ~10-15 seconds per iteration

### Workflow 2: Updating Dependencies

Workflow for updating requirements.txt.

```bash
# 1. Update requirements.txt
vim docker-images/requirements.txt

# 2. Build with cache mount benefits
./scripts/build.sh python3.11

# 3. Test functionality
./scripts/test-optimized-build.sh --quick python3.11

# 4. Measure performance impact
./scripts/measure-build-metrics.sh --skip-uncached --baseline

# 5. If good, build all variants
./scripts/build.sh --parallel all
./scripts/test-optimized-build.sh --quick all
```

**Expected duration**:
- Single variant: ~20-30 seconds
- All variants: ~2-3 minutes

### Workflow 3: Dockerfile Optimization

Workflow for making Dockerfile changes.

```bash
# 1. Establish baseline metrics
./scripts/measure-build-metrics.sh --baseline

# 2. Make Dockerfile changes
vim docker-images/python3.11.dockerfile

# 3. Clean build to test from scratch
./scripts/build.sh --no-cache python3.11

# 4. Test cache effectiveness
./scripts/build.sh python3.11  # Should be fast (warm cache)
echo "# test" >> docker-images/app/main.py
./scripts/build.sh python3.11  # Should only rebuild final layer
git checkout docker-images/app/main.py

# 5. Test functionality
./scripts/test-optimized-build.sh --quick python3.11

# 6. Measure new performance
./scripts/measure-build-metrics.sh --baseline

# 7. Review comparison
cat build-metrics.json

# 8. Apply to other variants if successful
vim docker-images/python3.10.dockerfile
vim docker-images/python3.9.dockerfile
# ... repeat for slim variants ...
```

**Expected duration**: ~15-20 minutes

### Workflow 4: Pre-Commit Validation

Validate changes before committing to git.

```bash
# 1. Build all variants in parallel
./scripts/build.sh --parallel all

# 2. Test all variants
./scripts/test-optimized-build.sh --quick all

# 3. Measure performance (quick check)
./scripts/measure-build-metrics.sh --skip-uncached

# 4. If all pass, commit changes
git add docker-images/
git commit -m "feat: optimize Dockerfile layer ordering"
```

**Expected duration**: ~3-5 minutes

### Workflow 5: Release Preparation

Full validation before releasing new images.

```bash
# 1. Clean build all variants
./scripts/build.sh --no-cache all

# 2. Test all variants thoroughly
./scripts/test-optimized-build.sh all

# 3. Full metrics measurement
./scripts/measure-build-metrics.sh

# 4. Review metrics
cat build-metrics.json

# 5. Update documentation
vim docs/docker-build-optimization.md

# 6. Commit metrics and docs
git add build-metrics.json docs/
git commit -m "docs: update build metrics for release"

# 7. Tag release
git tag v1.2.0
git push origin v1.2.0
```

**Expected duration**: ~15-20 minutes

### Workflow 6: Troubleshooting Build Issues

Debug and fix build problems.

```bash
# 1. Verbose clean build to see errors
./scripts/build.sh --no-cache --verbose python3.11 2>&1 | tee build-error.log

# 2. Analyze error
cat build-error.log

# 3. Fix Dockerfile
vim docker-images/python3.11.dockerfile

# 4. Test fix
./scripts/build.sh python3.11

# 5. Verify with tests
./scripts/test-optimized-build.sh --verbose python3.11

# 6. If fixed, clean build to validate
./scripts/build.sh --no-cache python3.11
```

---

## Best Practices

### General Best Practices

1. **Always enable BuildKit**
   ```bash
   export DOCKER_BUILDKIT=1
   # Add to ~/.bashrc or ~/.zshrc
   ```

2. **Use build scripts instead of raw docker commands**
   ```bash
   # Good
   ./scripts/build.sh python3.11

   # Less convenient
   cd docker-images && DOCKER_BUILDKIT=1 docker build -f python3.11.dockerfile -t tiangolo/uvicorn-gunicorn-fastapi:python3.11 .
   ```

3. **Test after every build**
   ```bash
   ./scripts/build.sh python3.11 && ./scripts/test-optimized-build.sh --quick python3.11
   ```

4. **Use parallel builds for multiple variants**
   ```bash
   # Much faster for multiple variants
   ./scripts/build.sh --parallel all
   ```

5. **Establish baselines before making changes**
   ```bash
   ./scripts/measure-build-metrics.sh --baseline
   ```

### Build Script Best Practices

1. **Use --no-cache for verification**
   - After Dockerfile changes
   - Before important releases
   - When troubleshooting cache issues

2. **Use --parallel for efficiency**
   - Building multiple variants
   - Taking advantage of multi-core CPUs
   - Regular multi-variant builds

3. **Use --verbose for debugging**
   - Understanding cache behavior
   - Debugging build failures
   - Verifying optimizations

4. **Build incrementally during development**
   ```bash
   # Just the variant you're working on
   ./scripts/build.sh python3.11

   # Not necessary to build all every time
   ```

### Metrics Script Best Practices

1. **Use --skip-uncached for quick checks**
   ```bash
   # During development
   ./scripts/measure-build-metrics.sh --skip-uncached
   ```

2. **Full metrics for important milestones**
   ```bash
   # Before release, after optimizations
   ./scripts/measure-build-metrics.sh
   ```

3. **Commit metrics to track over time**
   ```bash
   git add build-metrics.json
   git commit -m "chore: update build metrics"
   ```

4. **Compare against baseline regularly**
   ```bash
   ./scripts/measure-build-metrics.sh --baseline
   ```

### Test Script Best Practices

1. **Use --quick after builds**
   ```bash
   # Images already built, just test them
   ./scripts/test-optimized-build.sh --quick python3.11
   ```

2. **Test all variants before releases**
   ```bash
   ./scripts/test-optimized-build.sh all
   ```

3. **Use filters for focused testing**
   ```bash
   # Only test what you changed
   ./scripts/test-optimized-build.sh --python 3.11
   ./scripts/test-optimized-build.sh --slim-only
   ```

4. **Use --verbose for troubleshooting**
   ```bash
   ./scripts/test-optimized-build.sh --verbose python3.11
   ```

### Workflow Integration Best Practices

1. **Pre-commit hook**
   ```bash
   #!/bin/bash
   # .git/hooks/pre-commit
   if git diff --cached --name-only | grep -q "docker-images/.*\.dockerfile"; then
       echo "Dockerfile changes detected, running tests..."
       ./scripts/build.sh --parallel all
       ./scripts/test-optimized-build.sh --quick all
       exit $?
   fi
   ```

2. **CI/CD integration**
   ```yaml
   - name: Build and test images
     run: |
       ./scripts/build.sh --parallel all
       ./scripts/test-optimized-build.sh --quick all
       ./scripts/measure-build-metrics.sh --skip-uncached
   ```

3. **Development environment setup**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export DOCKER_BUILDKIT=1
   export PATH=$PATH:/code/scripts
   alias build-fast='build.sh --parallel all'
   alias build-test='build.sh --parallel all && test-optimized-build.sh --quick all'
   ```

---

## Troubleshooting

### Common Issues

#### Issue 1: Script Not Executable

**Symptom**:
```
bash: ./scripts/build.sh: Permission denied
```

**Solution**:
```bash
chmod +x /code/scripts/build.sh
chmod +x /code/scripts/measure-build-metrics.sh
chmod +x /code/scripts/test-optimized-build.sh
```

#### Issue 2: Script Not Found

**Symptom**:
```
bash: ./scripts/build.sh: No such file or directory
```

**Solution**:
```bash
# Check current directory
pwd

# Should be in /code directory
cd /code

# Or use absolute path
/code/scripts/build.sh python3.11
```

#### Issue 3: BuildKit Not Enabled

**Symptom**:
```
Error: failed to solve: dockerfile parse error line 1: unknown instruction: #
```

**Solution**:
```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Add to shell profile permanently
echo 'export DOCKER_BUILDKIT=1' >> ~/.bashrc
source ~/.bashrc
```

#### Issue 4: Build Fails in Parallel Mode

**Symptom**:
```
[ERROR] Build failed for variant python3.11
```

**Solution**:
```bash
# Try sequential builds to see error details
./scripts/build.sh python3.11

# Or use verbose mode
./scripts/build.sh --verbose python3.11

# Check logs (in parallel mode)
cat /tmp/build-python3.11.log
```

#### Issue 5: Tests Fail After Build

**Symptom**:
```
[FAIL] HTTP endpoint not responding
```

**Solution**:
```bash
# Check if container is running
docker ps -a | grep test-

# Check container logs
docker logs test-python3.11

# Try manual test
docker run -d -p 8000:80 --name manual-test tiangolo/uvicorn-gunicorn-fastapi:python3.11
curl http://localhost:8000
docker logs manual-test
docker stop manual-test && docker rm manual-test

# Check with verbose output
./scripts/test-optimized-build.sh --verbose python3.11
```

#### Issue 6: Port Already in Use

**Symptom**:
```
Error: bind: address already in use
```

**Solution**:
```bash
# Find what's using port 8001
lsof -i :8001

# Or use docker ps
docker ps | grep 8001

# Stop conflicting container
docker stop <container-name>

# Or clean up all test containers
docker ps -a | grep test- | awk '{print $1}' | xargs docker rm -f
```

#### Issue 7: Metrics Script Takes Too Long

**Symptom**:
```
[INFO] Measuring uncached builds... (very slow)
```

**Solution**:
```bash
# Use --skip-uncached for faster iteration
./scripts/measure-build-metrics.sh --skip-uncached

# Or interrupt and add flag
Ctrl+C
./scripts/measure-build-metrics.sh --skip-uncached
```

#### Issue 8: Image Size Larger Than Expected

**Symptom**:
```
[WARNING] Image size: 1.5GB (expected <1.1GB)
```

**Solution**:
```bash
# Check layer sizes
docker history tiangolo/uvicorn-gunicorn-fastapi:python3.11

# Check for large files in image
docker run --rm tiangolo/uvicorn-gunicorn-fastapi:python3.11 du -sh /* | sort -h

# Verify .dockerignore is working
cd /code/docker-images
docker build --no-cache -f python3.11.dockerfile -t test . 2>&1 | grep "transferring context"
# Should be ~10KB
```

#### Issue 9: Cache Not Working

**Symptom**:
```
[WARNING] Cache effectiveness: 30% (expected >90%)
```

**Solution**:
```bash
# Check BuildKit is enabled
echo $DOCKER_BUILDKIT  # Should be 1

# Check Dockerfile has BuildKit syntax
head -1 /code/docker-images/python3.11.dockerfile
# Should be: # syntax=docker/dockerfile:1

# Check layer ordering
cat /code/docker-images/python3.11.dockerfile

# Clear cache and rebuild
docker builder prune
./scripts/build.sh --no-cache python3.11
./scripts/build.sh python3.11  # Should be fast now
```

### Getting Help

If issues persist:

1. **Check script help**:
   ```bash
   ./scripts/build.sh --help
   ./scripts/measure-build-metrics.sh --help
   ./scripts/test-optimized-build.sh --help
   ```

2. **Run with verbose output**:
   ```bash
   ./scripts/build.sh --verbose python3.11 2>&1 | tee debug.log
   ```

3. **Check documentation**:
   - `/code/docs/docker-build-optimization.md` - Comprehensive optimization guide
   - `/code/docs/build-scripts-guide.md` - This guide
   - `/code/docker-images/cache-effectiveness-validation.md` - Cache testing

4. **Review Docker logs**:
   ```bash
   docker logs <container-name>
   docker events --since 1h
   ```

5. **Check Docker version**:
   ```bash
   docker version
   # BuildKit requires Docker 18.09+
   ```

---

## Summary

### Quick Reference

| Task | Command |
|------|---------|
| Build single variant | `./scripts/build.sh python3.11` |
| Build all variants | `./scripts/build.sh all` |
| Build all in parallel | `./scripts/build.sh --parallel all` |
| Clean build | `./scripts/build.sh --no-cache python3.11` |
| Test single variant | `./scripts/test-optimized-build.sh python3.11` |
| Quick test (no rebuild) | `./scripts/test-optimized-build.sh --quick python3.11` |
| Test all variants | `./scripts/test-optimized-build.sh all` |
| Measure metrics | `./scripts/measure-build-metrics.sh` |
| Quick metrics | `./scripts/measure-build-metrics.sh --skip-uncached` |
| Establish baseline | `./scripts/measure-build-metrics.sh --baseline` |

### Script Locations

- Build script: `/code/scripts/build.sh`
- Metrics script: `/code/scripts/measure-build-metrics.sh`
- Test script: `/code/scripts/test-optimized-build.sh`
- Metrics output: `/code/build-metrics.json`
- Baseline metrics: `/code/build-metrics-baseline.json`

### Key Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Cached build time | <5s | Excellent |
| Warm rebuild (no changes) | <3s | Excellent |
| Code change rebuild | <5s | Excellent |
| Cache effectiveness | >90% | Excellent |
| Build context size | <50KB | Excellent |

### Additional Resources

- **Optimization guide**: `/code/docs/docker-build-optimization.md`
- **Cache validation**: `/code/docker-images/cache-effectiveness-validation.md`
- **Build metrics**: `/code/docker-images/build-optimization-metrics.md`
- **GitHub workflow**: `/code/.github/workflows/deploy.yml`

---

**Document Version**: 1.0
**Last Updated**: 2025-10-20
**Status**: Production Ready
**Target Audience**: Developers, DevOps Engineers
