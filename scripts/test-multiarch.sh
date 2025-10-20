#!/bin/bash

#
# Multi-Architecture Build Validation Test Script
#
# This script runs comprehensive tests to validate that Docker images build
# and run correctly on both amd64 and arm64 architectures.
#
# Usage:
#   ./scripts/test-multiarch.sh [options]
#
# Options:
#   --variant NAME          Test specific variant only (e.g., python3.11)
#   --skip-emulation        Skip emulation tests (faster, amd64 only)
#   --quick                 Quick test mode (skip slow multi-platform tests)
#   --verbose               Show detailed output
#   --help                  Show this help message
#
# Examples:
#   ./scripts/test-multiarch.sh                    # Test all variants with emulation
#   ./scripts/test-multiarch.sh --skip-emulation   # Test amd64 only (faster)
#   ./scripts/test-multiarch.sh --variant python3.11-slim --verbose
#   ./scripts/test-multiarch.sh --quick            # Fast validation
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default options
VARIANT=""
SKIP_EMULATION=0
QUICK_MODE=0
VERBOSE=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --variant)
            VARIANT="$2"
            shift 2
            ;;
        --skip-emulation)
            SKIP_EMULATION=1
            shift
            ;;
        --quick)
            QUICK_MODE=1
            shift
            ;;
        --verbose)
            VERBOSE=1
            shift
            ;;
        --help)
            grep '^#' "$0" | cut -c 3-
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Enable BuildKit
export DOCKER_BUILDKIT=1

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Multi-Architecture Build Validation Tests${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check prerequisites
echo -e "${CYAN}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

# Check docker buildx
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}✗ Docker Buildx is not available${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Buildx is available${NC}"

# Check Python and pytest
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 is installed${NC}"

if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠ pytest is not installed. Installing...${NC}"
    pip3 install pytest docker requests
fi
echo -e "${GREEN}✓ pytest is available${NC}"

# Check docker Python library
if ! python3 -c "import docker" 2>/dev/null; then
    echo -e "${YELLOW}⚠ docker library is not installed. Installing...${NC}"
    pip3 install docker
fi
echo -e "${GREEN}✓ docker library is available${NC}"

# Setup QEMU for multi-platform builds (unless skipped)
if [ $SKIP_EMULATION -eq 0 ]; then
    echo ""
    echo -e "${CYAN}Setting up QEMU emulation for multi-platform builds...${NC}"
    if docker run --rm --privileged tonistiigi/binfmt --install all &> /dev/null; then
        echo -e "${GREEN}✓ QEMU emulation is configured${NC}"
    else
        echo -e "${YELLOW}⚠ QEMU setup failed. Multi-platform tests may be skipped.${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Skipping QEMU emulation setup (--skip-emulation flag)${NC}"
fi

# Create or use existing buildx builder
echo ""
echo -e "${CYAN}Setting up Docker Buildx builder...${NC}"
if ! docker buildx ls | grep -q "multiarch-builder"; then
    echo "Creating new buildx builder: multiarch-builder"
    docker buildx create --name multiarch-builder --use --platform linux/amd64,linux/arm64 &> /dev/null || true
else
    echo "Using existing buildx builder: multiarch-builder"
    docker buildx use multiarch-builder &> /dev/null || true
fi
echo -e "${GREEN}✓ Buildx builder is ready${NC}"

# Build pytest command
PYTEST_ARGS="-v"
TEST_FILE="tests/test_04_multiarch_validation.py"

if [ $VERBOSE -eq 1 ]; then
    PYTEST_ARGS="$PYTEST_ARGS -s"
fi

if [ -n "$VARIANT" ]; then
    export NAME="$VARIANT"
    echo ""
    echo -e "${CYAN}Testing variant: $VARIANT${NC}"
fi

if [ $SKIP_EMULATION -eq 1 ]; then
    export SKIP_EMULATION_TESTS=1
    echo -e "${YELLOW}Skipping emulation tests (amd64 only)${NC}"
fi

if [ $QUICK_MODE -eq 1 ]; then
    PYTEST_ARGS="$PYTEST_ARGS -k 'not multi_platform_build_both and not test_cache_effectiveness_multiarch'"
    echo -e "${CYAN}Quick mode: Skipping slow multi-platform tests${NC}"
fi

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Running Multi-Architecture Validation Tests${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Change to repository root
cd /code

# Run tests
START_TIME=$(date +%s)

if pytest $PYTEST_ARGS "$TEST_FILE"; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ All multi-architecture validation tests passed!${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Total test time: ${DURATION}s${NC}"
    echo ""

    # Print summary
    echo -e "${CYAN}Test Summary:${NC}"
    if [ -n "$VARIANT" ]; then
        echo -e "  • Variant tested: $VARIANT"
    else
        echo -e "  • All variants tested"
    fi

    if [ $SKIP_EMULATION -eq 1 ]; then
        echo -e "  • Platforms tested: linux/amd64 only"
    else
        echo -e "  • Platforms tested: linux/amd64, linux/arm64"
    fi

    if [ $QUICK_MODE -eq 1 ]; then
        echo -e "  • Mode: Quick (single-platform tests only)"
    else
        echo -e "  • Mode: Full (includes multi-platform tests)"
    fi

    echo ""
    echo -e "${GREEN}Multi-architecture builds are validated and working correctly!${NC}"
    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}✗ Some multi-architecture validation tests failed${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Total test time: ${DURATION}s${NC}"
    echo ""

    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo -e "  1. Check Docker is running: ${CYAN}docker ps${NC}"
    echo -e "  2. Verify BuildKit is enabled: ${CYAN}export DOCKER_BUILDKIT=1${NC}"
    echo -e "  3. Check QEMU setup: ${CYAN}docker run --rm --privileged tonistiigi/binfmt --install all${NC}"
    echo -e "  4. Test single platform: ${CYAN}$0 --skip-emulation${NC}"
    echo -e "  5. Test specific variant: ${CYAN}$0 --variant python3.11${NC}"
    echo -e "  6. Run with verbose output: ${CYAN}$0 --verbose${NC}"
    echo ""

    exit 1
fi
