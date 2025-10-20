"""
Test suite for validating Docker build performance improvements.

This module contains tests to measure and validate build performance:
- Measure cold build time (no cache) for each variant
- Measure warm build time (with cache) for each variant
- Calculate and validate cache effectiveness
- Validate image size is within expected ranges
- Ensure warm builds are significantly faster than cold builds
"""
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import docker
import pytest

client = docker.from_env()

# Test configuration
DOCKER_IMAGES_DIR = Path("/code/docker-images")
PERFORMANCE_RESULTS_FILE = Path("/tmp/build-performance-results.json")

# All image variants to test
IMAGE_VARIANTS = [
    "python3.9",
    "python3.9-slim",
    "python3.10",
    "python3.10-slim",
    "python3.11",
    "python3.11-slim",
]

# Expected image size ranges (in MB)
IMAGE_SIZE_RANGES = {
    "python3.9": (50, 1000),  # Standard images
    "python3.9-slim": (50, 500),  # Slim images
    "python3.10": (50, 1000),
    "python3.10-slim": (50, 500),
    "python3.11": (50, 1000),
    "python3.11-slim": (50, 500),
}

# Performance targets
MIN_CACHE_EFFECTIVENESS = 0.50  # 50% improvement minimum
OPTIMAL_CACHE_EFFECTIVENESS = 0.70  # 70% improvement is optimal


def get_image_name(variant: str) -> str:
    """Get the full image name for a variant."""
    return f"tiangolo/uvicorn-gunicorn-fastapi:{variant}"


def build_image_with_timing(
    variant: str,
    use_cache: bool = True,
    verbose: bool = False
) -> Dict[str, any]:
    """
    Build an image and measure build time.

    Args:
        variant: Image variant name (e.g., "python3.11-slim")
        use_cache: Whether to use Docker build cache
        verbose: Whether to print verbose output

    Returns:
        Dict with keys: 'success', 'build_time_seconds', 'output', 'error'
    """
    dockerfile = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"
    image_name = get_image_name(variant)

    # Prepare build command
    build_cmd = [
        "docker", "build",
        "-f", str(dockerfile),
        "-t", image_name,
        str(DOCKER_IMAGES_DIR)
    ]

    if not use_cache:
        build_cmd.insert(2, "--no-cache")

    # Enable BuildKit for optimal performance
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"

    try:
        start_time = time.time()

        result = subprocess.run(
            build_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        end_time = time.time()
        build_time = end_time - start_time

        if verbose:
            print(f"\nBuild output for {variant}:")
            print(result.stdout)
            if result.stderr:
                print("Build stderr:")
                print(result.stderr)

        return {
            "success": result.returncode == 0,
            "build_time_seconds": build_time,
            "output": result.stdout + result.stderr,
            "error": None if result.returncode == 0 else result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "build_time_seconds": None,
            "output": "",
            "error": "Build timed out after 600 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "build_time_seconds": None,
            "output": "",
            "error": str(e)
        }


def get_image_size_mb(variant: str) -> Optional[float]:
    """
    Get the size of an image in megabytes.

    Args:
        variant: Image variant name

    Returns:
        Image size in MB, or None if image not found
    """
    image_name = get_image_name(variant)

    try:
        image = client.images.get(image_name)
        size_bytes = image.attrs.get("Size", 0)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb
    except docker.errors.ImageNotFound:
        return None


def calculate_cache_effectiveness(
    cold_build_time: float,
    warm_build_time: float
) -> float:
    """
    Calculate cache effectiveness as a ratio.

    Formula: (cold_time - warm_time) / cold_time

    Args:
        cold_build_time: Build time without cache (seconds)
        warm_build_time: Build time with cache (seconds)

    Returns:
        Cache effectiveness ratio (0.0 to 1.0)
    """
    if cold_build_time <= 0:
        return 0.0

    improvement = (cold_build_time - warm_build_time) / cold_build_time
    return max(0.0, min(1.0, improvement))  # Clamp between 0 and 1


def save_performance_results(results: Dict[str, any]) -> None:
    """
    Save performance test results to a JSON file.

    Args:
        results: Performance test results dictionary
    """
    with open(PERFORMANCE_RESULTS_FILE, 'w') as f:
        json.dump(results, f, indent=2)


def load_performance_results() -> Optional[Dict[str, any]]:
    """
    Load performance test results from JSON file.

    Returns:
        Performance results dictionary, or None if file doesn't exist
    """
    if not PERFORMANCE_RESULTS_FILE.exists():
        return None

    try:
        with open(PERFORMANCE_RESULTS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


class TestColdBuildPerformance:
    """Test cold build performance (no cache)."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_cold_build_completes_successfully(self, variant):
        """
        Test that cold build completes successfully.

        This establishes baseline build time without cache.
        """
        # Only test the current variant in CI
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        # Check if we should skip cold build tests (they're slow)
        if os.getenv("SKIP_COLD_BUILD_TESTS", "false").lower() == "true":
            pytest.skip("Skipping cold build test (SKIP_COLD_BUILD_TESTS=true)")

        print(f"\n🧊 Cold build test for {variant} (this may take 60-120 seconds)...")

        result = build_image_with_timing(variant, use_cache=False, verbose=False)

        assert result["success"], \
            f"Cold build failed for {variant}: {result['error']}"

        assert result["build_time_seconds"] is not None, \
            f"Build time was not measured for {variant}"

        # Store result for later comparison
        results = load_performance_results() or {}
        if variant not in results:
            results[variant] = {}
        results[variant]["cold_build_time"] = result["build_time_seconds"]
        save_performance_results(results)

        print(f"✅ Cold build completed in {result['build_time_seconds']:.2f} seconds")


class TestWarmBuildPerformance:
    """Test warm build performance (with cache)."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_warm_build_completes_successfully(self, variant):
        """
        Test that warm build (with cache) completes successfully.

        This measures build time when cache is available.
        """
        # Only test the current variant in CI
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        print(f"\n🔥 Warm build test for {variant}...")

        # First, ensure image is built to populate cache
        # (In CI, this will already be done by previous test or workflow)
        image_name = get_image_name(variant)
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            # Build once to populate cache
            print(f"  Building {variant} to populate cache...")
            initial_build = build_image_with_timing(variant, use_cache=True)
            assert initial_build["success"], \
                f"Initial build failed for {variant}: {initial_build['error']}"

        # Now measure warm build time
        result = build_image_with_timing(variant, use_cache=True, verbose=False)

        assert result["success"], \
            f"Warm build failed for {variant}: {result['error']}"

        assert result["build_time_seconds"] is not None, \
            f"Build time was not measured for {variant}"

        # Store result for later comparison
        results = load_performance_results() or {}
        if variant not in results:
            results[variant] = {}
        results[variant]["warm_build_time"] = result["build_time_seconds"]
        save_performance_results(results)

        print(f"✅ Warm build completed in {result['build_time_seconds']:.2f} seconds")


class TestCacheEffectiveness:
    """Test cache effectiveness by comparing cold vs warm builds."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_cache_effectiveness_meets_target(self, variant):
        """
        Test that cache effectiveness meets minimum target (50% improvement).

        Cache effectiveness = (cold_time - warm_time) / cold_time
        Must be at least 0.50 (50% faster with cache).
        """
        # Only test the current variant in CI
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        # Load performance results
        results = load_performance_results()

        if not results or variant not in results:
            pytest.skip(f"No performance data available for {variant}. "
                       "Run cold and warm build tests first.")

        variant_data = results[variant]
        cold_time = variant_data.get("cold_build_time")
        warm_time = variant_data.get("warm_build_time")

        if cold_time is None or warm_time is None:
            pytest.skip(f"Incomplete performance data for {variant}. "
                       "Need both cold and warm build times.")

        # Calculate cache effectiveness
        effectiveness = calculate_cache_effectiveness(cold_time, warm_time)

        # Store effectiveness in results
        variant_data["cache_effectiveness"] = effectiveness
        results[variant] = variant_data
        save_performance_results(results)

        improvement_pct = effectiveness * 100

        print(f"\n📊 Cache effectiveness for {variant}:")
        print(f"  Cold build: {cold_time:.2f}s")
        print(f"  Warm build: {warm_time:.2f}s")
        print(f"  Improvement: {improvement_pct:.1f}%")

        if effectiveness >= OPTIMAL_CACHE_EFFECTIVENESS:
            print(f"  ✨ Excellent! Exceeds optimal target ({OPTIMAL_CACHE_EFFECTIVENESS*100:.0f}%)")
        elif effectiveness >= MIN_CACHE_EFFECTIVENESS:
            print(f"  ✅ Good! Meets minimum target ({MIN_CACHE_EFFECTIVENESS*100:.0f}%)")
        else:
            print(f"  ❌ Below target! Must be at least {MIN_CACHE_EFFECTIVENESS*100:.0f}%")

        # Assert minimum cache effectiveness
        assert effectiveness >= MIN_CACHE_EFFECTIVENESS, \
            f"Cache effectiveness ({improvement_pct:.1f}%) is below minimum target " \
            f"({MIN_CACHE_EFFECTIVENESS*100:.0f}%). Warm builds must be at least " \
            f"50% faster than cold builds. Cold: {cold_time:.2f}s, Warm: {warm_time:.2f}s"

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_warm_build_is_faster_than_cold_build(self, variant):
        """
        Test that warm build is faster than cold build.

        Basic sanity check that caching provides some benefit.
        """
        # Only test the current variant in CI
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        results = load_performance_results()

        if not results or variant not in results:
            pytest.skip(f"No performance data available for {variant}")

        variant_data = results[variant]
        cold_time = variant_data.get("cold_build_time")
        warm_time = variant_data.get("warm_build_time")

        if cold_time is None or warm_time is None:
            pytest.skip(f"Incomplete performance data for {variant}")

        assert warm_time < cold_time, \
            f"Warm build ({warm_time:.2f}s) should be faster than cold build " \
            f"({cold_time:.2f}s) for {variant}"


class TestImageSizeValidation:
    """Test that image sizes are within expected ranges."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_image_size_within_expected_range(self, variant):
        """
        Test that image size is within expected range.

        Expected ranges:
        - Standard images: < 1GB
        - Slim images: < 500MB
        """
        # Only test the current variant in CI
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        size_mb = get_image_size_mb(variant)

        if size_mb is None:
            pytest.skip(f"Image {variant} not found. Build the image first.")

        # Get expected range for this variant
        expected_min, expected_max = IMAGE_SIZE_RANGES.get(
            variant, (50, 1000)  # Default range
        )

        print(f"\n💾 Image size for {variant}: {size_mb:.1f} MB")

        # Determine if it's a slim image
        is_slim = "slim" in variant
        size_limit = 500 if is_slim else 1000  # 500MB for slim, 1GB for standard

        # Assert size is within limit
        assert size_mb < size_limit, \
            f"Image {variant} size ({size_mb:.1f} MB) exceeds limit " \
            f"({size_limit} MB). {'Slim' if is_slim else 'Standard'} images " \
            f"should be under {size_limit} MB."

        # Store size in results
        results = load_performance_results() or {}
        if variant not in results:
            results[variant] = {}
        results[variant]["image_size_mb"] = size_mb
        save_performance_results(results)

        # Provide feedback on size
        if is_slim and size_mb < 400:
            print(f"  ✨ Excellent! Well under 500MB limit for slim images")
        elif not is_slim and size_mb < 800:
            print(f"  ✅ Good! Well under 1GB limit for standard images")
        else:
            print(f"  ⚠️  Within limits but could be optimized further")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_slim_image_is_smaller_than_standard(self, variant):
        """
        Test that slim images are smaller than their standard counterparts.

        For example, python3.11-slim should be smaller than python3.11.
        """
        # Only run this test for slim variants
        if "slim" not in variant:
            pytest.skip(f"{variant} is not a slim variant")

        # Only test the current variant in CI
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        # Get corresponding standard variant
        standard_variant = variant.replace("-slim", "")

        slim_size = get_image_size_mb(variant)
        standard_size = get_image_size_mb(standard_variant)

        if slim_size is None:
            pytest.skip(f"Slim image {variant} not found")

        if standard_size is None:
            pytest.skip(f"Standard image {standard_variant} not found for comparison")

        print(f"\n📊 Size comparison:")
        print(f"  {standard_variant}: {standard_size:.1f} MB")
        print(f"  {variant}: {slim_size:.1f} MB")
        print(f"  Reduction: {standard_size - slim_size:.1f} MB ({(1 - slim_size/standard_size)*100:.1f}%)")

        assert slim_size < standard_size, \
            f"Slim image {variant} ({slim_size:.1f} MB) should be smaller than " \
            f"standard image {standard_variant} ({standard_size:.1f} MB)"


class TestBuildPerformanceSummary:
    """Generate summary of all build performance tests."""

    def test_generate_performance_summary(self):
        """
        Generate and display a summary of all build performance tests.

        This test always passes but provides a comprehensive summary.
        """
        results = load_performance_results()

        if not results:
            pytest.skip("No performance data available. Run tests first.")

        print("\n" + "="*80)
        print("BUILD PERFORMANCE SUMMARY")
        print("="*80)

        for variant in sorted(results.keys()):
            data = results[variant]
            print(f"\n📦 {variant}:")

            cold_time = data.get("cold_build_time")
            warm_time = data.get("warm_build_time")
            effectiveness = data.get("cache_effectiveness")
            size_mb = data.get("image_size_mb")

            if cold_time:
                print(f"  🧊 Cold build: {cold_time:.2f}s")
            if warm_time:
                print(f"  🔥 Warm build: {warm_time:.2f}s")
            if effectiveness:
                print(f"  ⚡ Cache effectiveness: {effectiveness*100:.1f}%")
            if size_mb:
                print(f"  💾 Image size: {size_mb:.1f} MB")

        print("\n" + "="*80)
        print(f"Results saved to: {PERFORMANCE_RESULTS_FILE}")
        print("="*80 + "\n")

        # This test always passes - it's just for informational output
        assert True
