#!/bin/bash
#
# Integration Test Runner for Docker Image Variants
#
# This script runs comprehensive end-to-end integration tests for all
# optimized Docker image variants. It validates that all optimizations
# maintain production functionality.
#
# Usage:
#   ./scripts/test-integration.sh [OPTIONS]
#
# Options:
#   --variant NAME       Test only specific variant (e.g., python3.11-slim)
#   --skip-build         Skip building images before testing
#   --rebuild            Rebuild images without cache before testing
#   --verbose            Show detailed test output
#   --quick              Run quick subset of tests
#   --help               Show this help message
#
# Examples:
#   ./scripts/test-integration.sh
#   ./scripts/test-integration.sh --variant python3.11-slim
#   ./scripts/test-integration.sh --rebuild --verbose
#   ./scripts/test-integration.sh --quick
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGES_DIR="/code/docker-images"
TEST_DIR="/code/tests"
IMAGE_PREFIX="tiangolo/uvicorn-gunicorn-fastapi"

# All variants to test
ALL_VARIANTS=(
    "python3.9:3.9"
    "python3.10:3.10"
    "python3.11:3.11"
    "python3.9-slim:3.9"
    "python3.10-slim:3.10"
    "python3.11-slim:3.11"
)

# Parse command-line options
VARIANT=""
SKIP_BUILD=false
REBUILD=false
VERBOSE=false
QUICK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --variant)
            VARIANT="$2"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --rebuild)
            REBUILD=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --quick)
            QUICK=true
            shift
            ;;
        --help)
            grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# *//'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Enable BuildKit for optimal build performance
export DOCKER_BUILDKIT=1

echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}Docker Image Integration Testing${NC}"
echo -e "${CYAN}================================${NC}"
echo ""

# Check prerequisites
echo -e "${CYAN}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker command not found${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${RED}Error: pytest not installed${NC}"
    echo "Install with: pip install pytest"
    exit 1
fi

if ! python3 -c "import docker" 2>/dev/null; then
    echo -e "${RED}Error: docker-py not installed${NC}"
    echo "Install with: pip install docker"
    exit 1
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "${RED}Error: requests not installed${NC}"
    echo "Install with: pip install requests"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites satisfied${NC}"
echo ""

# Determine which variants to test
if [ -n "$VARIANT" ]; then
    # Test specific variant
    VARIANTS_TO_TEST=()
    for variant_info in "${ALL_VARIANTS[@]}"; do
        name="${variant_info%%:*}"
        if [ "$name" == "$VARIANT" ]; then
            VARIANTS_TO_TEST+=("$variant_info")
            break
        fi
    done

    if [ ${#VARIANTS_TO_TEST[@]} -eq 0 ]; then
        echo -e "${RED}Error: Unknown variant: $VARIANT${NC}"
        echo "Available variants:"
        for variant_info in "${ALL_VARIANTS[@]}"; do
            name="${variant_info%%:*}"
            echo "  - $name"
        done
        exit 1
    fi
else
    # Test all variants
    VARIANTS_TO_TEST=("${ALL_VARIANTS[@]}")
fi

echo -e "${CYAN}Testing ${#VARIANTS_TO_TEST[@]} variant(s)${NC}"
echo ""

# Build images if needed
if [ "$SKIP_BUILD" = false ]; then
    echo -e "${CYAN}Building images...${NC}"

    BUILD_FLAGS=""
    if [ "$REBUILD" = true ]; then
        BUILD_FLAGS="--no-cache"
        echo "Building without cache (clean build)"
    else
        echo "Building with cache (faster)"
    fi

    for variant_info in "${VARIANTS_TO_TEST[@]}"; do
        name="${variant_info%%:*}"
        version="${variant_info##*:}"

        dockerfile="${DOCKER_IMAGES_DIR}/${name}.dockerfile"
        image_tag="${IMAGE_PREFIX}:${name}"

        echo -e "${CYAN}Building ${name}...${NC}"

        if [ "$VERBOSE" = true ]; then
            docker build $BUILD_FLAGS \
                -t "$image_tag" \
                -f "$dockerfile" \
                "$DOCKER_IMAGES_DIR"
        else
            docker build $BUILD_FLAGS \
                -t "$image_tag" \
                -f "$dockerfile" \
                "$DOCKER_IMAGES_DIR" > /dev/null 2>&1
        fi

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Built ${name}${NC}"
        else
            echo -e "${RED}✗ Failed to build ${name}${NC}"
            exit 1
        fi
    done

    echo ""
else
    echo -e "${YELLOW}Skipping build (using existing images)${NC}"
    echo ""
fi

# Verify images exist
echo -e "${CYAN}Verifying images...${NC}"
MISSING_IMAGES=()

for variant_info in "${VARIANTS_TO_TEST[@]}"; do
    name="${variant_info%%:*}"
    image_tag="${IMAGE_PREFIX}:${name}"

    if docker image inspect "$image_tag" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ ${name}${NC}"
    else
        echo -e "${RED}✗ ${name} (not found)${NC}"
        MISSING_IMAGES+=("$name")
    fi
done

if [ ${#MISSING_IMAGES[@]} -gt 0 ]; then
    echo -e "${RED}Error: ${#MISSING_IMAGES[@]} image(s) not found${NC}"
    echo "Build missing images or run without --skip-build"
    exit 1
fi

echo ""

# Run integration tests
echo -e "${CYAN}Running integration tests...${NC}"
echo ""

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v -s"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$QUICK" = true ]; then
    # Quick mode: skip slow tests
    PYTEST_CMD="$PYTEST_CMD -k 'not restart and not health'"
    echo -e "${YELLOW}Quick mode: skipping slow tests${NC}"
    echo ""
fi

# Add test file
PYTEST_CMD="$PYTEST_CMD ${TEST_DIR}/test_05_integration.py"

# Run tests for each variant
TEST_RESULTS=()
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
START_TIME=$(date +%s)

for variant_info in "${VARIANTS_TO_TEST[@]}"; do
    name="${variant_info%%:*}"
    version="${variant_info##*:}"

    echo -e "${CYAN}Testing ${name} (Python ${version})...${NC}"

    # Set environment variables for this variant
    export NAME="$name"
    export PYTHON_VERSION="$version"

    # Run tests
    if $PYTEST_CMD; then
        result="PASS"
        TEST_RESULTS+=("${name}:${result}")
        echo -e "${GREEN}✓ ${name} tests passed${NC}"
        ((PASSED_TESTS++))
    else
        result="FAIL"
        TEST_RESULTS+=("${name}:${result}")
        echo -e "${RED}✗ ${name} tests failed${NC}"
        ((FAILED_TESTS++))
    fi

    ((TOTAL_TESTS++))
    echo ""
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# Print summary
echo ""
echo -e "${CYAN}================================${NC}"
echo -e "${CYAN}Integration Test Summary${NC}"
echo -e "${CYAN}================================${NC}"
echo ""
echo "Total variants tested: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
else
    echo "Failed: 0"
fi
echo "Total time: ${ELAPSED}s"
echo ""

# Print results for each variant
echo "Results by variant:"
for result in "${TEST_RESULTS[@]}"; do
    name="${result%%:*}"
    status="${result##*:}"

    if [ "$status" == "PASS" ]; then
        echo -e "  ${GREEN}✓${NC} $name"
    else
        echo -e "  ${RED}✗${NC} $name"
    fi
done
echo ""

# Final status
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Integration tests FAILED${NC}"
    echo -e "${RED}================================${NC}"
    exit 1
else
    echo -e "${GREEN}All integration tests PASSED${NC}"
    echo -e "${GREEN}================================${NC}"
    exit 0
fi
