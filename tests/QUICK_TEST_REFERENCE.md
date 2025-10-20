# Quick Test Reference Card

Fast reference for testing optimized Docker images.

## Prerequisites

```bash
# Check Docker
docker --version  # Need 18.09+

# Enable BuildKit
export DOCKER_BUILDKIT=1

# Install Python dependencies
pip install pytest docker requests
```

## Quick Commands

### Test All Variants
```bash
./scripts/test-all-variants.sh
```

### Test Single Variant
```bash
./scripts/test-all-variants.sh --variant python3.11
```

### Test Without Rebuilding
```bash
./scripts/test-all-variants.sh --skip-build
```

### Clean Build Test
```bash
./scripts/test-all-variants.sh --no-cache
```

### Verbose Mode
```bash
./scripts/test-all-variants.sh --verbose
```

## Manual Testing

### Build Image
```bash
docker build -t tiangolo/uvicorn-gunicorn-fastapi:python3.11 \
  -f docker-images/python3.11.dockerfile docker-images/
```

### Run Tests
```bash
export NAME=python3.11 PYTHON_VERSION=3.11
pytest tests/test_01_main/test_defaults.py -v
```

## All Image Variants

| Variant | Python | Command |
|---------|--------|---------|
| python3.11 | 3.11 | `--variant python3.11` |
| python3.10 | 3.10 | `--variant python3.10` |
| python3.9 | 3.9 | `--variant python3.9` |
| python3.11-slim | 3.11 | `--variant python3.11-slim` |
| python3.10-slim | 3.10 | `--variant python3.10-slim` |
| python3.9-slim | 3.9 | `--variant python3.9-slim` |

## Expected Performance

| Operation | Time |
|-----------|------|
| Cold build | 60-120s |
| Warm build | 1-3s |
| Single test | 5-8s |
| All tests (warm) | 2-3 min |

## Troubleshooting

### Port in Use
```bash
docker stop uvicorn-gunicorn-fastapi-test
docker rm uvicorn-gunicorn-fastapi-test
```

### Image Not Found
```bash
# Build it first
docker build -t tiangolo/uvicorn-gunicorn-fastapi:<variant> \
  -f docker-images/<variant>.dockerfile docker-images/
```

### Permission Denied
```bash
sudo usermod -aG docker $USER
# Then log out and back in
```

## CI/CD

```bash
# Trigger workflow
gh workflow run test.yml

# Check status
gh run list --workflow=test.yml
```

## Documentation

- Full guide: `/code/tests/README.md`
- Compatibility: `/code/tests/TEST_COMPATIBILITY_ANALYSIS.md`
- Build optimization: `/code/docs/docker-build-optimization.md`

## Script Help

```bash
./scripts/test-all-variants.sh --help
```

---
**Quick Reference v1.0** | Step 6.1
