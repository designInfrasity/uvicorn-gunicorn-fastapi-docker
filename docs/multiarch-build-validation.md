# Multi-Architecture Build Validation

This document describes the multi-architecture build validation strategy for the uvicorn-gunicorn-fastapi-docker project, ensuring that optimized Docker images build and run correctly on both amd64 and arm64 platforms.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Support](#architecture-support)
3. [Testing Strategy](#testing-strategy)
4. [QEMU Emulation Setup](#qemu-emulation-setup)
5. [Running Multi-Arch Validation Tests](#running-multi-arch-validation-tests)
6. [Test Coverage](#test-coverage)
7. [GitHub Actions Integration](#github-actions-integration)
8. [Performance Considerations](#performance-considerations)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

## Overview

Multi-architecture (multi-arch) support allows Docker images to run natively on different CPU architectures. This project builds images for:

- **linux/amd64** - Intel/AMD 64-bit processors (most common in cloud environments)
- **linux/arm64** - ARM 64-bit processors (AWS Graviton, Apple Silicon, Raspberry Pi, etc.)

### Why Multi-Arch Matters

1. **Performance**: Native execution is faster than emulation
2. **Cost**: ARM instances (like AWS Graviton) often offer better price/performance
3. **Flexibility**: Users can run images on any supported platform without modification
4. **Future-proofing**: ARM adoption is growing in data centers and edge computing

## Architecture Support

### Current Support Matrix

| Image Variant | linux/amd64 | linux/arm64 |
|--------------|-------------|-------------|
| python3.9 | ✅ | ✅ |
| python3.9-slim | ✅ | ✅ |
| python3.10 | ✅ | ✅ |
| python3.10-slim | ✅ | ✅ |
| python3.11 | ✅ | ✅ |
| python3.11-slim | ✅ | ✅ |

All image variants are built and tested for both architectures.

### Base Image Compatibility

The project uses `tiangolo/uvicorn-gunicorn` base images, which support multi-arch builds:

- `tiangolo/uvicorn-gunicorn:python3.9` - Multi-arch base
- `tiangolo/uvicorn-gunicorn:python3.10` - Multi-arch base
- `tiangolo/uvicorn-gunicorn:python3.11` - Multi-arch base
- `tiangolo/uvicorn-gunicorn:python3.9-slim` - Multi-arch base
- `tiangolo/uvicorn-gunicorn:python3.10-slim` - Multi-arch base
- `tiangolo/uvicorn-gunicorn:python3.11-slim` - Multi-arch base

## Testing Strategy

### Test Approach

Multi-arch validation uses a comprehensive testing strategy:

1. **Single-Platform Builds**: Test each platform independently
2. **Multi-Platform Builds**: Test building for both platforms simultaneously
3. **QEMU Emulation**: Use QEMU to test non-native architectures
4. **Functionality Tests**: Verify images run correctly on both platforms
5. **Performance Tests**: Measure build times for multi-arch builds
6. **Cache Validation**: Ensure BuildKit cache works across architectures
7. **Workflow Validation**: Verify GitHub Actions workflow compatibility

### Test Layers

```
┌─────────────────────────────────────────────────┐
│  Layer 1: QEMU & Buildx Setup Validation       │
├─────────────────────────────────────────────────┤
│  Layer 2: Single-Platform Build Tests          │
│    • linux/amd64 builds                         │
│    • linux/arm64 builds (with emulation)        │
├─────────────────────────────────────────────────┤
│  Layer 3: Multi-Platform Build Tests           │
│    • Simultaneous amd64 + arm64 builds          │
│    • Cache effectiveness validation             │
├─────────────────────────────────────────────────┤
│  Layer 4: Runtime Functionality Tests          │
│    • Container startup on amd64                 │
│    • Container startup on arm64 (with emulation)│
│    • Application responsiveness                 │
├─────────────────────────────────────────────────┤
│  Layer 5: Optimization Preservation Tests      │
│    • Layer ordering preserved                   │
│    • Cache-friendly structure maintained        │
├─────────────────────────────────────────────────┤
│  Layer 6: GitHub Actions Compatibility         │
│    • Workflow configuration validation          │
│    • Matrix build setup validation              │
│    • Buildx action validation                   │
└─────────────────────────────────────────────────┘
```

## QEMU Emulation Setup

### What is QEMU?

QEMU is a processor emulator that allows running ARM binaries on x86 machines (and vice versa). Docker uses QEMU through `binfmt_misc` to enable multi-platform builds.

### Automatic Setup

The test script automatically sets up QEMU:

```bash
docker run --rm --privileged tonistiigi/binfmt --install all
```

This command:
- Installs QEMU emulators for various architectures
- Configures Linux `binfmt_misc` to use QEMU transparently
- Enables Docker to build for non-native platforms

### Manual Setup (if needed)

```bash
# Install QEMU for all architectures
docker run --rm --privileged tonistiigi/binfmt --install all

# Verify QEMU is working
docker run --rm --platform linux/arm64 alpine uname -m
# Should output: aarch64
```

### Platform Detection

The test suite automatically detects the host platform:

```python
def get_host_architecture() -> str:
    result = subprocess.run(["uname", "-m"], capture_output=True, text=True)
    arch = result.stdout.strip()
    arch_map = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return arch_map.get(arch, arch)
```

## Running Multi-Arch Validation Tests

### Quick Start

```bash
# Run full multi-arch validation (all variants, both platforms)
./scripts/test-multiarch.sh

# Test specific variant
./scripts/test-multiarch.sh --variant python3.11

# Skip emulation tests (faster, amd64 only)
./scripts/test-multiarch.sh --skip-emulation

# Quick validation (skip slow multi-platform builds)
./scripts/test-multiarch.sh --quick

# Verbose output for debugging
./scripts/test-multiarch.sh --verbose
```

### Using pytest Directly

```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1

# Run all multi-arch tests
pytest tests/test_04_multiarch_validation.py -v

# Test specific variant
NAME=python3.11-slim pytest tests/test_04_multiarch_validation.py -v

# Skip emulation tests
SKIP_EMULATION_TESTS=1 pytest tests/test_04_multiarch_validation.py -v

# Run specific test class
pytest tests/test_04_multiarch_validation.py::TestMultiArchBuildSuccess -v

# Run specific test method
pytest tests/test_04_multiarch_validation.py::TestMultiArchBuildSuccess::test_single_platform_build_amd64 -v
```

### Test Modes

| Mode | Command | Speed | Coverage | Use Case |
|------|---------|-------|----------|----------|
| Full | `./scripts/test-multiarch.sh` | Slow | Complete | Pre-release validation |
| Quick | `./scripts/test-multiarch.sh --quick` | Fast | Essential | Development iteration |
| Single Platform | `./scripts/test-multiarch.sh --skip-emulation` | Fast | amd64 only | Quick validation |
| Single Variant | `./scripts/test-multiarch.sh --variant python3.11` | Medium | One image | Targeted testing |

### Expected Test Duration

| Test Scope | Duration (with cache) | Duration (cold) |
|------------|----------------------|-----------------|
| Single platform (amd64) | 2-5 minutes | 10-15 minutes |
| Multi-platform (both) | 5-10 minutes | 20-30 minutes |
| All variants, quick mode | 8-12 minutes | 30-45 minutes |
| All variants, full mode | 15-25 minutes | 60-90 minutes |

*Duration depends on hardware, network speed, and Docker cache state.*

## Test Coverage

### Test Classes

#### 1. TestQEMUSetup
Validates QEMU emulation environment.

**Tests:**
- `test_qemu_available`: Checks QEMU can be installed/configured
- `test_buildx_available`: Verifies docker buildx is available
- `test_buildx_builder_exists`: Ensures buildx builder instance exists

#### 2. TestMultiArchBuildSuccess
Tests that images build successfully for both architectures.

**Tests:**
- `test_single_platform_build_amd64`: Builds for amd64 only
- `test_single_platform_build_arm64`: Builds for arm64 (with emulation)
- `test_multi_platform_build_both`: Builds for both platforms simultaneously

**Parameterized across all 6 variants.**

#### 3. TestBuildKitCacheMultiArch
Validates BuildKit cache effectiveness for multi-arch builds.

**Tests:**
- `test_cache_effectiveness_multiarch`: Measures cache improvement
  - Cold build (no cache): baseline performance
  - Warm build (with cache): should be ≥30% faster

#### 4. TestImageFunctionality
Tests that images run correctly on both platforms.

**Tests:**
- `test_image_runs_on_amd64`: Verifies container starts on amd64
- `test_image_runs_on_arm64`: Verifies container starts on arm64 (emulated)
- Checks for "Uvicorn running" in logs to confirm app started

**Parameterized across all 6 variants.**

#### 5. TestGitHubActionsCompatibility
Validates GitHub Actions workflow configuration.

**Tests:**
- `test_workflow_file_exists`: Workflow file present
- `test_workflow_has_multiarch_platforms`: Includes both platforms
- `test_workflow_has_buildx_setup`: Uses setup-buildx-action
- `test_workflow_matrix_includes_all_variants`: All 6 variants in matrix
- `test_workflow_uses_correct_context`: Uses docker-images directory
- `test_dockerfile_syntax_compatible_with_buildx`: No arch-specific commands

#### 6. TestMultiArchPerformance
Measures multi-arch build performance.

**Tests:**
- `test_multiarch_build_time_reasonable`: Builds complete within time limits
  - Performance categories: Excellent (<2min), Good (<5min), Fair (<10min), Slow (>10min)

#### 7. TestDockerfileOptimizationPreservation
Ensures optimizations are preserved in multi-arch builds.

**Tests:**
- `test_layer_ordering_preserved_multiarch`: Optimal layer order maintained
  - Verifies: FROM → COPY requirements → RUN pip install → COPY app

**Parameterized across all 6 variants.**

### Coverage Summary

| Test Category | Tests | Variants Tested | Platforms Tested |
|--------------|-------|-----------------|------------------|
| Setup Validation | 3 | - | - |
| Build Success | 18 (3×6) | All 6 | amd64, arm64 |
| Cache Effectiveness | 1 | 1 (configurable) | Both |
| Functionality | 12 (2×6) | All 6 | amd64, arm64 |
| Workflow Compatibility | 6 | - | - |
| Performance | 1 | 1 (configurable) | Both |
| Optimization Preservation | 6 | All 6 | Both |
| **Total** | **47 tests** | **All variants** | **Both platforms** |

## GitHub Actions Integration

### Current Workflow Configuration

The deploy workflow (`.github/workflows/deploy.yml`) includes multi-arch support:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build and push
  uses: docker/build-push-action@v6
  with:
    push: true
    platforms: linux/amd64,linux/arm64  # Multi-arch platforms
    tags: |
      tiangolo/uvicorn-gunicorn-fastapi:${{ matrix.image.name }}
      tiangolo/uvicorn-gunicorn-fastapi:${{ matrix.image.name }}-${{ env.DATE_TAG }}
    context: ./docker-images/
    file: ./docker-images/${{ env.DOCKERFILE_NAME }}.dockerfile
```

### Workflow Features

1. **Matrix Strategy**: Builds all 6 variants in parallel
2. **Multi-Platform**: Each variant built for amd64 and arm64
3. **Docker Buildx**: Uses buildx for multi-platform support
4. **Automated**: Runs on push to master, weekly schedule, or manual trigger

### Validation Tests for Workflow

The test suite validates:
- ✅ Buildx setup action is configured
- ✅ Platforms include both linux/amd64 and linux/arm64
- ✅ All 6 variants are in the matrix
- ✅ Correct build context (docker-images/)
- ✅ Dockerfiles are compatible with multi-platform builds

## Performance Considerations

### Build Time Comparison

| Build Type | amd64 Native | arm64 Emulated | Multi-Platform |
|------------|--------------|----------------|----------------|
| Cold Build | 60-90s | 90-150s | 120-200s |
| Warm Build | 2-5s | 3-8s | 5-10s |
| Cache Effectiveness | 90-95% | 85-90% | 80-85% |

*arm64 builds on amd64 hosts use QEMU emulation, which adds overhead.*

### Optimization Impact on Multi-Arch

| Optimization | Single-Arch Benefit | Multi-Arch Benefit | Notes |
|--------------|--------------------|--------------------|-------|
| Layer Ordering | +++++ | +++++ | Same benefit, applies to all platforms |
| BuildKit Cache | +++++ | ++++ | Slightly less effective with emulation |
| .dockerignore | +++++ | +++++ | Reduces context for all platforms |
| Cache Mounts | ++++ | +++ | Emulation adds slight overhead |

### Performance Tips

1. **Use Native Builds When Possible**: Run on ARM hardware for faster arm64 builds
2. **Leverage CI/CD**: GitHub Actions uses native runners, no emulation needed
3. **Cache Effectively**: BuildKit cache helps both platforms
4. **Parallel Matrix Builds**: GitHub Actions builds all variants concurrently
5. **Quick Mode for Development**: Use `--skip-emulation` for faster iteration

## Troubleshooting

### Common Issues and Solutions

#### Issue: QEMU Not Available

**Symptom:**
```
Error: QEMU emulation not available
```

**Solution:**
```bash
# Install QEMU emulation
docker run --rm --privileged tonistiigi/binfmt --install all

# Verify installation
docker run --rm --platform linux/arm64 alpine uname -m
```

#### Issue: Buildx Builder Not Found

**Symptom:**
```
Error: buildx builder not found
```

**Solution:**
```bash
# Create a new builder
docker buildx create --name multiarch-builder --use --platform linux/amd64,linux/arm64

# Use the builder
docker buildx use multiarch-builder

# Inspect builder
docker buildx inspect --bootstrap
```

#### Issue: Multi-Platform Build Fails

**Symptom:**
```
Error: multiple platforms feature is currently not supported for docker driver
```

**Solution:**
```bash
# Switch to docker-container driver
docker buildx create --name multiarch-builder --driver docker-container --use

# Rebuild
docker buildx build --platform linux/amd64,linux/arm64 -t myimage:tag .
```

#### Issue: Slow ARM64 Builds

**Symptom:**
ARM64 builds take 3-5x longer than amd64 builds.

**Solution:**
- This is expected with QEMU emulation
- Use `--skip-emulation` flag for faster testing during development
- Full multi-platform tests are better suited for CI/CD
- Consider using native ARM hardware for faster builds

#### Issue: Cache Not Working Across Platforms

**Symptom:**
Build cache doesn't help when switching platforms.

**Solution:**
```bash
# Use cache-from to pull cache from registry
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --cache-from type=registry,ref=myimage:cache \
  --cache-to type=inline \
  -t myimage:tag .
```

#### Issue: Container Won't Start on ARM64

**Symptom:**
```
Error: exec format error
```

**Solution:**
- Ensure QEMU is properly installed
- Verify base image supports arm64
- Check Dockerfile doesn't have architecture-specific commands
- Test with: `docker run --rm --platform linux/arm64 myimage:tag`

### Debug Commands

```bash
# Check host architecture
uname -m

# List available builders
docker buildx ls

# Inspect builder capabilities
docker buildx inspect

# Check QEMU registration
docker run --rm --privileged tonistiigi/binfmt

# Test arm64 emulation
docker run --rm --platform linux/arm64 alpine uname -m

# Build with verbose output
BUILDKIT_PROGRESS=plain docker buildx build --platform linux/amd64,linux/arm64 .

# Test image architecture
docker inspect myimage:tag | grep Architecture
```

## Best Practices

### 1. Dockerfile Best Practices for Multi-Arch

#### ✅ DO:

```dockerfile
# Use multi-arch base images
FROM tiangolo/uvicorn-gunicorn:python3.11

# Use architecture-agnostic commands
RUN pip install -r requirements.txt

# Copy files normally
COPY ./app /app
```

#### ❌ DON'T:

```dockerfile
# Don't use architecture-specific base images
FROM amd64/python:3.11  # Bad

# Don't use architecture-specific commands
RUN if [ "$(uname -m)" = "x86_64" ]; then ...; fi  # Bad

# Don't download architecture-specific binaries without detection
RUN wget https://example.com/binary-amd64  # Bad
```

### 2. Testing Strategy

- **Development**: Use `--skip-emulation` for fast iteration
- **Pre-Commit**: Run quick mode validation
- **Pre-Release**: Run full multi-arch validation
- **CI/CD**: Let GitHub Actions handle multi-arch builds

### 3. Performance Optimization

- Keep Dockerfiles architecture-agnostic
- Maintain optimal layer ordering (benefits all platforms)
- Use BuildKit cache mounts (works across architectures)
- Leverage registry cache in CI/CD

### 4. Validation Checklist

Before releasing multi-arch images:

- [ ] All variants build successfully for amd64
- [ ] All variants build successfully for arm64 (with emulation)
- [ ] Multi-platform builds complete without errors
- [ ] Images run correctly on amd64
- [ ] Images run correctly on arm64 (with emulation)
- [ ] Cache effectiveness is ≥30% for multi-arch builds
- [ ] Layer ordering is optimal
- [ ] GitHub Actions workflow validates successfully
- [ ] Build times are within acceptable ranges

### 5. CI/CD Integration

```yaml
# Example GitHub Actions workflow
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3

- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build and push
  uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64,linux/arm64
    cache-from: type=registry,ref=${{ env.IMAGE }}:cache
    cache-to: type=inline
    push: true
    tags: ${{ env.IMAGE }}:${{ env.TAG }}
```

## Conclusion

Multi-architecture build validation ensures that optimized Docker images work correctly on both amd64 and arm64 platforms. The comprehensive test suite validates:

1. ✅ Build success on both platforms
2. ✅ Runtime functionality on both platforms
3. ✅ Cache effectiveness for multi-arch builds
4. ✅ GitHub Actions workflow compatibility
5. ✅ Optimization preservation across architectures
6. ✅ Performance within acceptable ranges

By following the testing strategy and best practices outlined in this document, you can confidently deploy multi-architecture images that provide optimal performance on any supported platform.

## Related Documentation

- [Docker Build Optimization Guide](docker-build-optimization.md)
- [Build Scripts Guide](build-scripts-guide.md)
- [Test Suite Documentation](/code/tests/README.md)
- [GitHub Actions Deploy Workflow](/.github/workflows/deploy.yml)
- [Docker Buildx Documentation](https://docs.docker.com/build/buildx/)
- [QEMU User Emulation](https://www.qemu.org/docs/master/user/main.html)
