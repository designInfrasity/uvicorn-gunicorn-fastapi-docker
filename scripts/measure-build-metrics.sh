#!/bin/bash

# Build Performance Monitoring Script for uvicorn-gunicorn-fastapi-docker
# Tracks and compares build metrics over time including build time, image size, and layer count

set -e

# Enable BuildKit by default for optimal performance
export DOCKER_BUILDKIT=1

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
BUILD_DIR="/code/docker-images"
IMAGE_PREFIX="tiangolo/uvicorn-gunicorn-fastapi"
METRICS_FILE="/code/build-metrics.json"
BASELINE_FILE="/code/baseline-metrics.json"
SKIP_UNCACHED=false
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
Usage: $0 [OPTIONS]

Build performance monitoring script that tracks and compares build metrics over time.

OPTIONS:
    --skip-uncached     Skip uncached (cold) builds (faster, only measures cached builds)
    --verbose           Enable verbose output
    --baseline          Save current metrics as baseline for future comparisons
    -h, --help          Display this help message

METRICS TRACKED:
    - Build time (cached and uncached)
    - Image size
    - Layer count
    - Git commit hash
    - Timestamp

OUTPUT:
    Results are saved to: $METRICS_FILE

EXAMPLES:
    # Measure all metrics (cached and uncached builds)
    $0

    # Quick measurement (cached builds only)
    $0 --skip-uncached

    # Establish baseline metrics
    $0 --baseline

    # Verbose output for debugging
    $0 --verbose

NOTES:
    - Uncached builds can take 5-10 minutes total
    - Use --skip-uncached for faster feedback in development
    - Metrics include timestamp and git commit for tracking changes over time
    - Baseline comparison shows improvement percentages

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

print_metric() {
    echo -e "${CYAN}[METRIC]${NC} $1"
}

# Function to get git commit hash
get_git_commit() {
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git rev-parse --short HEAD 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

# Function to get timestamp
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Function to measure build time
measure_build_time() {
    local variant=$1
    local use_cache=$2
    local dockerfile="${BUILD_DIR}/${variant}.dockerfile"
    local image_tag="${IMAGE_PREFIX}:${variant}"

    if [[ ! -f "$dockerfile" ]]; then
        print_error "Dockerfile not found: $dockerfile"
        return 1
    fi

    local cache_flag=""
    local build_type="cached"
    if [[ "$use_cache" == "false" ]]; then
        cache_flag="--no-cache"
        build_type="uncached"
    fi

    if [[ "$VERBOSE" == true ]]; then
        print_info "Measuring $build_type build time for: $variant"
    fi

    local start_time=$(date +%s)

    if [[ "$VERBOSE" == true ]]; then
        docker build $cache_flag -t "$image_tag" -f "$dockerfile" "$BUILD_DIR"
    else
        docker build $cache_flag -t "$image_tag" -f "$dockerfile" "$BUILD_DIR" > /dev/null 2>&1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "$duration"
}

# Function to measure image size
measure_image_size() {
    local variant=$1
    local image_tag="${IMAGE_PREFIX}:${variant}"

    # Get size in bytes for accurate comparison
    local size_bytes=$(docker images --format "{{.Size}}" "$image_tag" | head -1)

    # Also get human-readable size
    local size_human=$(docker images --format "{{.Size}}" "$image_tag" | head -1)

    echo "$size_human"
}

# Function to measure layer count
measure_layer_count() {
    local variant=$1
    local image_tag="${IMAGE_PREFIX}:${variant}"

    # Count non-empty layers from docker history (excluding <missing> intermediate layers)
    local layer_count=$(docker history "$image_tag" --format "{{.CreatedBy}}" | grep -v "^$" | wc -l)

    echo "$layer_count"
}

# Function to measure all metrics for a variant
measure_variant_metrics() {
    local variant=$1
    local skip_uncached=$2

    echo "{"
    echo "  \"variant\": \"$variant\","

    # Measure cached build time (fast)
    print_info "Measuring cached build time: $variant"
    local cached_time=$(measure_build_time "$variant" "true")
    echo "  \"build_time_cached_seconds\": $cached_time,"
    print_metric "$variant cached build: ${cached_time}s"

    # Measure uncached build time (slow) if not skipped
    if [[ "$skip_uncached" == "false" ]]; then
        print_info "Measuring uncached build time: $variant (this may take a while...)"
        local uncached_time=$(measure_build_time "$variant" "false")
        echo "  \"build_time_uncached_seconds\": $uncached_time,"
        print_metric "$variant uncached build: ${uncached_time}s"

        # Calculate cache effectiveness
        local cache_improvement=0
        if [[ $uncached_time -gt 0 ]]; then
            cache_improvement=$(awk "BEGIN {printf \"%.1f\", (($uncached_time - $cached_time) / $uncached_time) * 100}")
        fi
        echo "  \"cache_effectiveness_percent\": $cache_improvement,"
        print_success "$variant cache effectiveness: ${cache_improvement}%"
    else
        echo "  \"build_time_uncached_seconds\": null,"
        echo "  \"cache_effectiveness_percent\": null,"
    fi

    # Measure image size
    local image_size=$(measure_image_size "$variant")
    echo "  \"image_size\": \"$image_size\","
    print_metric "$variant image size: $image_size"

    # Measure layer count
    local layer_count=$(measure_layer_count "$variant")
    echo "  \"layer_count\": $layer_count"
    print_metric "$variant layer count: $layer_count"

    echo "}"
}

# Function to generate full metrics JSON
generate_metrics_json() {
    local skip_uncached=$1
    local git_commit=$(get_git_commit)
    local timestamp=$(get_timestamp)

    echo "{"
    echo "  \"timestamp\": \"$timestamp\","
    echo "  \"git_commit\": \"$git_commit\","
    echo "  \"buildkit_enabled\": true,"
    echo "  \"variants\": ["

    local first=true
    for variant in "${VARIANTS[@]}"; do
        if [[ "$first" == false ]]; then
            echo "    ,"
        fi
        first=false

        print_info "========================================="
        print_info "Measuring metrics for: $variant"
        print_info "========================================="

        measure_variant_metrics "$variant" "$skip_uncached" | sed 's/^/    /'

        echo ""
    done

    echo "  ]"
    echo "}"
}

# Function to compare with baseline
compare_with_baseline() {
    if [[ ! -f "$BASELINE_FILE" ]]; then
        print_warning "No baseline metrics found at $BASELINE_FILE"
        print_info "Run with --baseline flag to establish baseline"
        return
    fi

    print_info "========================================="
    print_info "Comparing with baseline metrics"
    print_info "========================================="

    # Use Python or jq if available for JSON parsing, otherwise skip detailed comparison
    if command -v python3 &> /dev/null; then
        python3 <<EOF
import json
import sys

try:
    with open('$METRICS_FILE', 'r') as f:
        current = json.load(f)
    with open('$BASELINE_FILE', 'r') as f:
        baseline = json.load(f)

    print("\nComparison Results:")
    print("=" * 60)

    for curr_var in current['variants']:
        variant_name = curr_var['variant']

        # Find matching baseline variant
        base_var = next((v for v in baseline['variants'] if v['variant'] == variant_name), None)

        if not base_var:
            print(f"\n{variant_name}: No baseline data")
            continue

        print(f"\n{variant_name}:")

        # Compare cached build time
        if curr_var['build_time_cached_seconds'] and base_var['build_time_cached_seconds']:
            curr_cached = curr_var['build_time_cached_seconds']
            base_cached = base_var['build_time_cached_seconds']
            diff_pct = ((curr_cached - base_cached) / base_cached) * 100 if base_cached > 0 else 0
            status = "↓" if diff_pct < 0 else "↑" if diff_pct > 0 else "="
            print(f"  Cached build time: {curr_cached}s vs {base_cached}s ({status} {abs(diff_pct):.1f}%)")

        # Compare uncached build time
        if curr_var['build_time_uncached_seconds'] and base_var['build_time_uncached_seconds']:
            curr_uncached = curr_var['build_time_uncached_seconds']
            base_uncached = base_var['build_time_uncached_seconds']
            diff_pct = ((curr_uncached - base_uncached) / base_uncached) * 100 if base_uncached > 0 else 0
            status = "↓" if diff_pct < 0 else "↑" if diff_pct > 0 else "="
            print(f"  Uncached build time: {curr_uncached}s vs {base_uncached}s ({status} {abs(diff_pct):.1f}%)")

        # Compare layer count
        if curr_var['layer_count'] and base_var['layer_count']:
            curr_layers = curr_var['layer_count']
            base_layers = base_var['layer_count']
            diff = curr_layers - base_layers
            status = "↓" if diff < 0 else "↑" if diff > 0 else "="
            print(f"  Layer count: {curr_layers} vs {base_layers} ({status} {abs(diff)})")

        # Compare image size (just show both, no percentage)
        print(f"  Image size: {curr_var['image_size']} vs {base_var['image_size']}")

    print("\n" + "=" * 60)
    print(f"Baseline from: {baseline['git_commit']} ({baseline['timestamp']})")
    print(f"Current from:  {current['git_commit']} ({current['timestamp']})")

except Exception as e:
    print(f"Error comparing metrics: {e}", file=sys.stderr)
    sys.exit(1)
EOF
    else
        print_warning "Python3 not available, skipping detailed comparison"
        print_info "Install python3 for detailed baseline comparison"
    fi
}

# Main script execution
main() {
    local save_baseline=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            --skip-uncached)
                SKIP_UNCACHED=true
                print_info "Skipping uncached builds (faster measurement)"
                shift
                ;;
            --verbose)
                VERBOSE=true
                print_info "Verbose mode enabled"
                shift
                ;;
            --baseline)
                save_baseline=true
                print_info "Will save metrics as baseline"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

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
    print_info "Build Metrics Configuration"
    echo "======================================"
    print_info "BuildKit: Enabled"
    print_info "Build directory: $BUILD_DIR"
    print_info "Output file: $METRICS_FILE"
    print_info "Skip uncached: $SKIP_UNCACHED"
    print_info "Verbose: $VERBOSE"
    [[ "$save_baseline" == true ]] && print_info "Mode: Establish baseline"
    echo "======================================"
    echo ""

    # Generate metrics
    print_info "Starting build metrics measurement..."
    print_info "Git commit: $(get_git_commit)"
    print_info "Timestamp: $(get_timestamp)"
    echo ""

    if [[ "$SKIP_UNCACHED" == false ]]; then
        print_warning "This will perform uncached builds and may take 5-10 minutes"
        print_info "Use --skip-uncached for faster measurement"
        echo ""
    fi

    # Generate and save metrics
    generate_metrics_json "$SKIP_UNCACHED" > "$METRICS_FILE"

    print_success "Metrics saved to: $METRICS_FILE"
    echo ""

    # Save as baseline if requested
    if [[ "$save_baseline" == true ]]; then
        cp "$METRICS_FILE" "$BASELINE_FILE"
        print_success "Baseline metrics saved to: $BASELINE_FILE"
        echo ""
    fi

    # Compare with baseline if not establishing new baseline
    if [[ "$save_baseline" == false ]]; then
        compare_with_baseline
    fi

    print_success "Build metrics measurement complete!"
}

# Run main function
main "$@"
