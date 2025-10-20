#!/bin/bash
# Test All Docker Image Variants
#
# This script builds and tests all Docker image variants (standard and slim)
# for Python 3.9, 3.10, and 3.11 to ensure optimized Dockerfiles work correctly.
#
# Usage:
#   ./scripts/test-all-variants.sh [options]
#
# Options:
#   --skip-build       Skip building images, test existing images only
#   --no-cache         Build images without cache (clean build)
#   --variant NAME     Test only specific variant (e.g., python3.11-slim)
#   --verbose          Show detailed output from builds and tests
#   --help             Show this help message
#
# Examples:
#   ./scripts/test-all-variants.sh                    # Build and test all variants
#   ./scripts/test-all-variants.sh --skip-build       # Test existing images
#   ./scripts/test-all-variants.sh --variant python3.11-slim  # Test one variant
#   ./scripts/test-all-variants.sh --no-cache         # Clean build and test all

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default options
SKIP_BUILD=false
NO_CACHE=false
SPECIFIC_VARIANT=""
VERBOSE=false

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Build directory
BUILD_DIR="docker-images"

# All variants to test
VARIANTS=(
    "python3.9:3.9"
    "python3.10:3.10"
    "python3.11:3.11"
    "python3.9-slim:3.9"
    "python3.10-slim:3.10"
    "python3.11-slim:3.11"
)

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --variant)
            SPECIFIC_VARIANT="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            head -n 20 "$0" | grep "^#" | sed 's/^# //' | sed 's/^#!//'
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Helper functions
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check Python
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        log_error "Python is not installed or not in PATH"
        exit 1
    fi

    # Determine Python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi

    # Check pytest
    if ! $PYTHON_CMD -c "import pytest" 2>/dev/null; then
        log_warning "pytest is not installed. Installing..."
        $PYTHON_CMD -m pip install pytest docker requests
    fi

    # Check docker Python library
    if ! $PYTHON_CMD -c "import docker" 2>/dev/null; then
        log_warning "docker Python library is not installed. Installing..."
        $PYTHON_CMD -m pip install docker
    fi

    # Check requests library
    if ! $PYTHON_CMD -c "import requests" 2>/dev/null; then
        log_warning "requests library is not installed. Installing..."
        $PYTHON_CMD -m pip install requests
    fi

    # Check build directory
    if [ ! -d "$BUILD_DIR" ]; then
        log_error "Build directory $BUILD_DIR does not exist"
        exit 1
    fi

    # Enable BuildKit
    export DOCKER_BUILDKIT=1

    log_success "All prerequisites satisfied"
}

# Build a specific variant
build_variant() {
    local variant=$1
    local python_version=$2
    local dockerfile="${BUILD_DIR}/${variant}.dockerfile"
    local image_tag="tiangolo/uvicorn-gunicorn-fastapi:${variant}"

    if [ ! -f "$dockerfile" ]; then
        log_error "Dockerfile not found: $dockerfile"
        return 1
    fi

    log_info "Building image: $image_tag"

    local build_args="build -t $image_tag -f $dockerfile $BUILD_DIR"
    if [ "$NO_CACHE" = true ]; then
        build_args="$build_args --no-cache"
    fi

    local start_time=$(date +%s)

    if [ "$VERBOSE" = true ]; then
        docker $build_args
    else
        docker $build_args > /dev/null 2>&1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [ $? -eq 0 ]; then
        log_success "Built $variant in ${duration}s"
        return 0
    else
        log_error "Failed to build $variant"
        return 1
    fi
}

# Test a specific variant
test_variant() {
    local variant=$1
    local python_version=$2
    local image_tag="tiangolo/uvicorn-gunicorn-fastapi:${variant}"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    log_info "Testing image: $image_tag"

    # Check if image exists
    if ! docker image inspect "$image_tag" > /dev/null 2>&1; then
        log_error "Image not found: $image_tag. Build it first or remove --skip-build flag."
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi

    # Set environment variables for pytest
    export NAME="$variant"
    export PYTHON_VERSION="$python_version"
    export SLEEP_TIME=3

    # Run tests
    log_info "Running pytest for $variant (Python $python_version)..."

    local test_output
    if [ "$VERBOSE" = true ]; then
        $PYTHON_CMD -m pytest tests/test_01_main/test_defaults.py -v
    else
        test_output=$($PYTHON_CMD -m pytest tests/test_01_main/test_defaults.py -v 2>&1)
    fi

    local test_result=$?

    if [ $test_result -eq 0 ]; then
        log_success "Tests passed for $variant"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "Tests failed for $variant"
        if [ "$VERBOSE" = false ]; then
            echo "$test_output"
        fi
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Build and test a variant
build_and_test_variant() {
    local variant=$1
    local python_version=$2

    echo ""
    echo "=========================================="
    log_info "Processing variant: $variant (Python $python_version)"
    echo "=========================================="

    # Build if not skipped
    if [ "$SKIP_BUILD" = false ]; then
        if ! build_variant "$variant" "$python_version"; then
            log_error "Build failed for $variant, skipping tests"
            TOTAL_TESTS=$((TOTAL_TESTS + 1))
            FAILED_TESTS=$((FAILED_TESTS + 1))
            return 1
        fi
    fi

    # Test
    if ! test_variant "$variant" "$python_version"; then
        return 1
    fi

    return 0
}

# Main execution
main() {
    echo "=========================================="
    echo "Docker Image Variant Test Suite"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_prerequisites

    # Print configuration
    echo ""
    log_info "Configuration:"
    echo "  Skip Build: $SKIP_BUILD"
    echo "  No Cache: $NO_CACHE"
    echo "  Verbose: $VERBOSE"
    echo "  BuildKit: Enabled"
    if [ -n "$SPECIFIC_VARIANT" ]; then
        echo "  Testing: $SPECIFIC_VARIANT only"
    else
        echo "  Testing: All variants (${#VARIANTS[@]} total)"
    fi
    echo ""

    local start_time=$(date +%s)

    # Process variants
    if [ -n "$SPECIFIC_VARIANT" ]; then
        # Test specific variant
        local found=false
        for variant_spec in "${VARIANTS[@]}"; do
            IFS=':' read -r variant python_version <<< "$variant_spec"
            if [ "$variant" = "$SPECIFIC_VARIANT" ]; then
                found=true
                build_and_test_variant "$variant" "$python_version"
                break
            fi
        done

        if [ "$found" = false ]; then
            log_error "Variant '$SPECIFIC_VARIANT' not found in variant list"
            echo "Available variants:"
            for variant_spec in "${VARIANTS[@]}"; do
                IFS=':' read -r variant python_version <<< "$variant_spec"
                echo "  - $variant"
            done
            exit 1
        fi
    else
        # Test all variants
        for variant_spec in "${VARIANTS[@]}"; do
            IFS=':' read -r variant python_version <<< "$variant_spec"
            build_and_test_variant "$variant" "$python_version"
        done
    fi

    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))

    # Summary
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo "Total tests: $TOTAL_TESTS"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
    echo "Total time: ${total_duration}s"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        log_success "All tests passed! ✓"
        exit 0
    else
        log_error "Some tests failed. Please review the output above."
        exit 1
    fi
}

# Run main function
main
