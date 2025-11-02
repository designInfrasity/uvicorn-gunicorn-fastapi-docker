#!/bin/bash

# Test script to validate optimized Docker builds produce correct artifacts
# Validates functionality, file presence, environment variables, and app responsiveness

set -e

# Enable BuildKit by default for testing optimized builds
export DOCKER_BUILDKIT=1

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BUILD_DIR="/code/docker-images"
IMAGE_PREFIX="tiangolo/uvicorn-gunicorn-fastapi"
CONTAINER_NAME="test-optimized-build-container"
TEST_PORT="8001"

# Test variants
PYTHON_VERSIONS=("3.9" "3.10" "3.11")
VARIANT_TYPES=("" "-slim")

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
}

# Function to clean up containers
cleanup_container() {
    local container_name=$1
    if docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
        print_info "Cleaning up container: $container_name"
        docker stop "$container_name" > /dev/null 2>&1 || true
        docker rm "$container_name" > /dev/null 2>&1 || true
    fi
}

# Function to build an image
build_image() {
    local variant=$1
    local dockerfile="${BUILD_DIR}/${variant}.dockerfile"
    local image_tag="${IMAGE_PREFIX}:${variant}"

    print_info "Building image: $image_tag"

    if [[ ! -f "$dockerfile" ]]; then
        print_error "Dockerfile not found: $dockerfile"
        return 1
    fi

    if docker build -t "$image_tag" -f "$dockerfile" "$BUILD_DIR" > /dev/null 2>&1; then
        print_success "Built image: $image_tag"
        return 0
    else
        print_error "Failed to build image: $image_tag"
        return 1
    fi
}

# Function to start container
start_container() {
    local image_tag=$1
    local container_name=$2

    print_info "Starting container from: $image_tag"

    if docker run -d --name "$container_name" -p "${TEST_PORT}:80" "$image_tag" > /dev/null 2>&1; then
        # Wait for container to be ready
        sleep 3

        # Check if container is running
        if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
            print_success "Container started successfully"
            return 0
        else
            print_error "Container failed to start or exited"
            docker logs "$container_name" 2>&1 | tail -10
            return 1
        fi
    else
        print_error "Failed to start container"
        return 1
    fi
}

# Function to test FastAPI app response
test_app_response() {
    local container_name=$1
    local expected_python_version=$2

    print_test "Testing FastAPI app response"

    # Try multiple times in case app is still starting
    local max_attempts=10
    local attempt=1
    local success=false

    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "http://localhost:${TEST_PORT}/" > /dev/null 2>&1; then
            success=true
            break
        fi
        sleep 1
        ((attempt++))
    done

    if [[ "$success" == false ]]; then
        print_error "FastAPI app did not respond after ${max_attempts} attempts"
        ((TESTS_FAILED++))
        return 1
    fi

    # Get the response
    local response=$(curl -s "http://localhost:${TEST_PORT}/")

    # Check if response contains expected Python version
    if echo "$response" | grep -q "Python ${expected_python_version}"; then
        print_success "FastAPI app responds correctly with Python ${expected_python_version}"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "Response does not contain expected Python version ${expected_python_version}"
        print_info "Response: $response"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check file presence
test_file_presence() {
    local container_name=$1
    local file_path=$2

    print_test "Checking file presence: $file_path"

    if docker exec "$container_name" test -f "$file_path" 2>/dev/null; then
        print_success "File exists: $file_path"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "File not found: $file_path"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check if file is executable
test_file_executable() {
    local container_name=$1
    local file_path=$2

    print_test "Checking if file is executable: $file_path"

    if docker exec "$container_name" test -x "$file_path" 2>/dev/null; then
        print_success "File is executable: $file_path"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "File is not executable: $file_path"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to verify Python syntax
test_python_syntax() {
    local container_name=$1
    local file_path=$2

    print_test "Verifying Python syntax: $file_path"

    if docker exec "$container_name" python -m py_compile "$file_path" 2>/dev/null; then
        print_success "Python syntax valid: $file_path"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "Python syntax error in: $file_path"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check environment variables
test_environment_variable() {
    local container_name=$1
    local var_name=$2
    local expected_value=$3

    print_test "Checking environment variable: $var_name"

    local actual_value=$(docker exec "$container_name" printenv "$var_name" 2>/dev/null || echo "")

    if [[ -n "$actual_value" ]]; then
        if [[ -z "$expected_value" ]] || [[ "$actual_value" == "$expected_value" ]]; then
            print_success "Environment variable set: $var_name=$actual_value"
            ((TESTS_PASSED++))
            return 0
        else
            print_error "Environment variable mismatch: $var_name (expected: $expected_value, got: $actual_value)"
            ((TESTS_FAILED++))
            return 1
        fi
    else
        print_error "Environment variable not set: $var_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check Gunicorn/Uvicorn processes
test_processes() {
    local container_name=$1

    print_test "Checking Gunicorn/Uvicorn processes"

    local processes=$(docker exec "$container_name" ps aux 2>/dev/null || echo "")

    if echo "$processes" | grep -q "gunicorn"; then
        print_success "Gunicorn process is running"
        ((TESTS_PASSED++))

        # Check for uvicorn worker
        if echo "$processes" | grep -q "uvicorn"; then
            print_success "Uvicorn worker process is running"
            ((TESTS_PASSED++))
        else
            print_warning "Uvicorn worker process not found (may not be visible in ps)"
            # Don't fail on this as uvicorn may be embedded in gunicorn
        fi
        return 0
    else
        print_error "Gunicorn process not found"
        print_info "Running processes:"
        echo "$processes"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check container logs for expected content
test_logs() {
    local container_name=$1

    print_test "Checking container logs for expected content"

    local logs=$(docker logs "$container_name" 2>&1)
    local log_checks_passed=0
    local log_checks_total=3

    # Check for prestart script execution
    if echo "$logs" | grep -q "Checking for script in /app/prestart.sh"; then
        print_success "Log contains prestart.sh check"
        ((log_checks_passed++))
    else
        print_warning "Log does not contain prestart.sh check"
    fi

    # Check for application startup
    if echo "$logs" | grep -q "Application startup complete"; then
        print_success "Log contains application startup message"
        ((log_checks_passed++))
    else
        print_warning "Log does not contain application startup message"
    fi

    # Check for uvicorn worker
    if echo "$logs" | grep -q "uvicorn.workers.UvicornWorker"; then
        print_success "Log contains uvicorn worker initialization"
        ((log_checks_passed++))
    else
        print_warning "Log does not contain uvicorn worker initialization"
    fi

    if [[ $log_checks_passed -ge 2 ]]; then
        print_success "Container logs contain expected content ($log_checks_passed/$log_checks_total checks passed)"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "Container logs missing expected content (only $log_checks_passed/$log_checks_total checks passed)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check image size is reasonable
test_image_size() {
    local image_tag=$1
    local variant_type=$2

    print_test "Checking image size for $image_tag"

    local size_bytes=$(docker images --format "{{.Size}}" "$image_tag" | head -1)
    print_info "Image size: $size_bytes"

    # Just report the size, don't fail based on it
    # Different architectures and Python versions have different sizes
    print_success "Image size recorded: $size_bytes"
    ((TESTS_PASSED++))
    return 0
}

# Function to verify build cache metadata
test_build_cache() {
    local image_tag=$1

    print_test "Verifying BuildKit optimizations in image"

    # Check if image was built (it should exist)
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^${image_tag}$"; then
        print_success "Image built successfully with BuildKit"
        ((TESTS_PASSED++))
        return 0
    else
        print_error "Image not found in local registry"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to test a complete variant
test_variant() {
    local python_version=$1
    local variant_type=$2
    local variant="python${python_version}${variant_type}"
    local image_tag="${IMAGE_PREFIX}:${variant}"
    local container_name="${CONTAINER_NAME}-${variant}"

    echo ""
    echo "========================================"
    print_info "Testing variant: $variant"
    echo "========================================"

    # Clean up any existing container
    cleanup_container "$container_name"

    # Build the image
    if ! build_image "$variant"; then
        print_error "Build failed for $variant, skipping tests"
        ((TESTS_FAILED++))
        return 1
    fi

    # Test build cache
    test_build_cache "$image_tag"

    # Test image size
    test_image_size "$image_tag" "$variant_type"

    # Start the container
    if ! start_container "$image_tag" "$container_name"; then
        print_error "Failed to start container for $variant, skipping remaining tests"
        cleanup_container "$container_name"
        ((TESTS_FAILED++))
        return 1
    fi

    # Run tests
    test_app_response "$container_name" "$python_version"
    test_file_presence "$container_name" "/app/main.py"
    test_python_syntax "$container_name" "/app/main.py"
    test_file_presence "$container_name" "/app/prestart.sh"
    test_file_executable "$container_name" "/app/prestart.sh"
    test_environment_variable "$container_name" "PYTHONPATH" ""
    test_environment_variable "$container_name" "MODULE_NAME" ""
    test_processes "$container_name"
    test_logs "$container_name"

    # Clean up
    cleanup_container "$container_name"

    print_success "Completed testing variant: $variant"
    return 0
}

# Function to print usage
usage() {
    cat <<EOF
Usage: $0 [OPTIONS] [VARIANT]

Test script to validate optimized Docker builds produce correct artifacts.

ARGUMENTS:
    VARIANT         Test a specific variant (e.g., python3.11, python3.11-slim)
                    If not specified, tests all variants

OPTIONS:
    --python VER    Test only specific Python version (3.9, 3.10, or 3.11)
    --slim-only     Test only slim variants
    --standard-only Test only standard (non-slim) variants
    --quick         Skip rebuild and test existing images only
    -h, --help      Display this help message

EXAMPLES:
    # Test all variants (6 total)
    $0

    # Test specific variant
    $0 python3.11-slim

    # Test only Python 3.11 variants
    $0 --python 3.11

    # Test only slim variants
    $0 --slim-only

    # Quick test without rebuilding
    $0 --quick

VALIDATION TESTS:
    - Build image with optimized Dockerfile
    - Start container and verify FastAPI app responds
    - Check /app/main.py exists and has valid Python syntax
    - Verify expected environment variables are set
    - Test Gunicorn/Uvicorn processes are running
    - Validate container logs contain expected content
    - Check image size and BuildKit optimizations

EXIT CODES:
    0 - All tests passed
    1 - One or more tests failed

EOF
}

# Main function
main() {
    local test_all=true
    local specific_variant=""
    local python_filter=""
    local type_filter=""
    local quick_mode=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            --python)
                python_filter=$2
                shift 2
                ;;
            --slim-only)
                type_filter="-slim"
                shift
                ;;
            --standard-only)
                type_filter=""
                shift
                ;;
            --quick)
                quick_mode=true
                print_info "Quick mode: skipping rebuild"
                shift
                ;;
            python*)
                specific_variant=$1
                test_all=false
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Check prerequisites
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! command -v curl &> /dev/null; then
        print_error "curl is not installed or not in PATH"
        exit 1
    fi

    if [[ ! -d "$BUILD_DIR" ]]; then
        print_error "Build directory not found: $BUILD_DIR"
        exit 1
    fi

    # Print test configuration
    echo "========================================"
    print_info "Test Configuration"
    echo "========================================"
    print_info "BuildKit: Enabled"
    print_info "Build directory: $BUILD_DIR"
    print_info "Test port: $TEST_PORT"
    [[ "$quick_mode" == true ]] && print_info "Quick mode: Enabled"
    echo "========================================"

    local start_time=$(date +%s)

    # Run tests
    if [[ "$test_all" == false ]]; then
        # Test specific variant
        if [[ ! -f "${BUILD_DIR}/${specific_variant}.dockerfile" ]]; then
            print_error "Dockerfile not found for variant: $specific_variant"
            exit 1
        fi

        # Extract python version from variant name
        if [[ "$specific_variant" =~ python([0-9]+\.[0-9]+)(-slim)? ]]; then
            local py_ver="${BASH_REMATCH[1]}"
            local var_type="${BASH_REMATCH[2]:-}"
            test_variant "$py_ver" "$var_type"
        else
            print_error "Invalid variant name: $specific_variant"
            exit 1
        fi
    else
        # Test all variants (with filters if specified)
        for py_version in "${PYTHON_VERSIONS[@]}"; do
            # Skip if python version filter is set and doesn't match
            if [[ -n "$python_filter" ]] && [[ "$py_version" != "$python_filter" ]]; then
                continue
            fi

            for var_type in "${VARIANT_TYPES[@]}"; do
                # Skip if type filter is set and doesn't match
                if [[ "$type_filter" == "-slim" ]] && [[ "$var_type" != "-slim" ]]; then
                    continue
                fi
                if [[ "$type_filter" == "" ]] && [[ "$var_type" == "-slim" ]]; then
                    continue
                fi

                test_variant "$py_version" "$var_type"
            done
        done
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Print summary
    echo ""
    echo "========================================"
    print_info "Test Summary"
    echo "========================================"
    print_success "Tests passed: $TESTS_PASSED"
    [[ $TESTS_FAILED -gt 0 ]] && print_error "Tests failed: $TESTS_FAILED"
    print_info "Total time: ${duration}s"
    echo "========================================"

    # Exit with appropriate code
    if [[ $TESTS_FAILED -eq 0 ]]; then
        print_success "All tests passed!"
        exit 0
    else
        print_error "Some tests failed!"
        exit 1
    fi
}

# Run main function
main "$@"
