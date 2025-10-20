#!/bin/bash

# Comprehensive Docker image build script for uvicorn-gunicorn-fastapi-docker
# Supports building individual variants, all variants, parallel builds, and performance monitoring

set -e

# Enable BuildKit by default for optimal caching and performance
export DOCKER_BUILDKIT=1

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
BUILD_DIR="/code/docker-images"
IMAGE_PREFIX="tiangolo/uvicorn-gunicorn-fastapi"
NO_CACHE=""
PARALLEL=false
VERBOSE=false

# Available image variants
VARIANTS=(
    "python3.9"
    "python3.10"
    "python3.11"
    "python3.9-slim"
    "python3.10-slim"
    "python3.11-slim"
)

# Function to print usage information
usage() {
    cat <<EOF
Usage: $0 [OPTIONS] [VARIANT|all]

Comprehensive Docker build script with BuildKit optimization and performance monitoring.

ARGUMENTS:
    VARIANT         Build a specific image variant (e.g., python3.11, python3.11-slim)
    all             Build all image variants

OPTIONS:
    --no-cache      Build without using cache (clean build)
    --parallel      Build multiple variants in parallel (only with 'all')
    --verbose       Enable verbose output
    -h, --help      Display this help message

AVAILABLE VARIANTS:
    python3.9           Standard Python 3.9 image
    python3.10          Standard Python 3.10 image
    python3.11          Standard Python 3.11 image
    python3.9-slim      Slim Python 3.9 image (multi-stage build)
    python3.10-slim     Slim Python 3.10 image (multi-stage build)
    python3.11-slim     Slim Python 3.11 image (multi-stage build)

EXAMPLES:
    # Build a single variant
    $0 python3.11

    # Build a slim variant
    $0 python3.11-slim

    # Build all variants sequentially
    $0 all

    # Build all variants in parallel (faster)
    $0 --parallel all

    # Clean build without cache
    $0 --no-cache python3.11

    # Verbose output for debugging
    $0 --verbose python3.11

NOTES:
    - BuildKit is enabled by default (DOCKER_BUILDKIT=1)
    - Build times and results are reported for each variant
    - Parallel builds spawn background jobs for each variant
    - All builds are performed in $BUILD_DIR

EOF
}

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to validate variant name
validate_variant() {
    local variant=$1
    for valid_variant in "${VARIANTS[@]}"; do
        if [[ "$variant" == "$valid_variant" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to build a single variant
build_variant() {
    local variant=$1
    local dockerfile="${BUILD_DIR}/${variant}.dockerfile"
    local image_tag="${IMAGE_PREFIX}:${variant}"

    print_info "Building variant: $variant"
    print_info "Dockerfile: $dockerfile"
    print_info "Image tag: $image_tag"

    if [[ ! -f "$dockerfile" ]]; then
        print_error "Dockerfile not found: $dockerfile"
        return 1
    fi

    # Start timing
    local start_time=$(date +%s)

    # Build command
    local build_cmd="docker build"
    [[ -n "$NO_CACHE" ]] && build_cmd="$build_cmd --no-cache"
    build_cmd="$build_cmd -t $image_tag -f $dockerfile $BUILD_DIR"

    if [[ "$VERBOSE" == true ]]; then
        print_info "Running: $build_cmd"
    fi

    # Execute build
    if [[ "$VERBOSE" == true ]]; then
        eval $build_cmd
    else
        eval $build_cmd > /dev/null 2>&1
    fi

    local build_status=$?

    # End timing
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [[ $build_status -eq 0 ]]; then
        print_success "Built $variant in ${duration}s"

        # Get image size
        local image_size=$(docker images --format "{{.Size}}" "$image_tag" | head -1)
        print_info "Image size: $image_size"

        return 0
    else
        print_error "Failed to build $variant (took ${duration}s)"
        return 1
    fi
}

# Function to build a variant in the background (for parallel builds)
build_variant_background() {
    local variant=$1
    local log_file="/tmp/build-${variant}.log"

    print_info "Starting background build for: $variant (log: $log_file)"

    {
        build_variant "$variant"
    } > "$log_file" 2>&1 &

    echo $!
}

# Function to build all variants sequentially
build_all_sequential() {
    local success_count=0
    local fail_count=0
    local total_start=$(date +%s)

    print_info "Building all variants sequentially..."
    echo ""

    for variant in "${VARIANTS[@]}"; do
        if build_variant "$variant"; then
            ((success_count++))
        else
            ((fail_count++))
        fi
        echo ""
    done

    local total_end=$(date +%s)
    local total_duration=$((total_end - total_start))

    echo "======================================"
    print_info "Build Summary"
    echo "======================================"
    print_success "Successful: $success_count"
    [[ $fail_count -gt 0 ]] && print_error "Failed: $fail_count"
    print_info "Total time: ${total_duration}s"
    echo "======================================"

    return $fail_count
}

# Function to build all variants in parallel
build_all_parallel() {
    local pids=()
    local variants_started=()
    local total_start=$(date +%s)

    print_info "Building all variants in parallel..."
    echo ""

    # Start all builds in background
    for variant in "${VARIANTS[@]}"; do
        local pid=$(build_variant_background "$variant")
        pids+=("$pid")
        variants_started+=("$variant")
    done

    print_info "Waiting for ${#pids[@]} parallel builds to complete..."
    echo ""

    # Wait for all background jobs and collect results
    local success_count=0
    local fail_count=0

    for i in "${!pids[@]}"; do
        local pid="${pids[$i]}"
        local variant="${variants_started[$i]}"
        local log_file="/tmp/build-${variant}.log"

        if wait "$pid"; then
            ((success_count++))
            cat "$log_file"
        else
            ((fail_count++))
            print_error "Build failed for $variant"
            cat "$log_file"
        fi

        # Clean up log file
        rm -f "$log_file"
        echo ""
    done

    local total_end=$(date +%s)
    local total_duration=$((total_end - total_start))

    echo "======================================"
    print_info "Parallel Build Summary"
    echo "======================================"
    print_success "Successful: $success_count"
    [[ $fail_count -gt 0 ]] && print_error "Failed: $fail_count"
    print_info "Total time: ${total_duration}s"
    print_info "Time savings: Building in parallel vs sequential"
    echo "======================================"

    return $fail_count
}

# Main script execution
main() {
    local variant=""
    local build_all=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            --no-cache)
                NO_CACHE="--no-cache"
                print_info "Clean build mode enabled (no cache)"
                shift
                ;;
            --parallel)
                PARALLEL=true
                print_info "Parallel build mode enabled"
                shift
                ;;
            --verbose)
                VERBOSE=true
                print_info "Verbose mode enabled"
                shift
                ;;
            all)
                build_all=true
                shift
                ;;
            *)
                if [[ -z "$variant" ]]; then
                    variant=$1
                    shift
                else
                    print_error "Unknown option: $1"
                    usage
                    exit 1
                fi
                ;;
        esac
    done

    # Validate arguments
    if [[ "$build_all" == false ]] && [[ -z "$variant" ]]; then
        print_error "No variant specified"
        echo ""
        usage
        exit 1
    fi

    if [[ "$build_all" == false ]] && ! validate_variant "$variant"; then
        print_error "Invalid variant: $variant"
        echo ""
        print_info "Available variants:"
        for v in "${VARIANTS[@]}"; do
            echo "  - $v"
        done
        exit 1
    fi

    if [[ "$PARALLEL" == true ]] && [[ "$build_all" == false ]]; then
        print_warning "Parallel mode only works with 'all', ignoring --parallel flag"
        PARALLEL=false
    fi

    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi

    # Check if build directory exists
    if [[ ! -d "$BUILD_DIR" ]]; then
        print_error "Build directory not found: $BUILD_DIR"
        exit 1
    fi

    # Print configuration
    echo "======================================"
    print_info "Build Configuration"
    echo "======================================"
    print_info "BuildKit: Enabled"
    print_info "Build directory: $BUILD_DIR"
    [[ -n "$NO_CACHE" ]] && print_info "Cache: Disabled"
    [[ "$PARALLEL" == true ]] && print_info "Mode: Parallel"
    [[ "$VERBOSE" == true ]] && print_info "Verbose: Enabled"
    echo "======================================"
    echo ""

    # Execute build
    if [[ "$build_all" == true ]]; then
        if [[ "$PARALLEL" == true ]]; then
            build_all_parallel
        else
            build_all_sequential
        fi
        exit $?
    else
        build_variant "$variant"
        exit $?
    fi
}

# Run main function
main "$@"
