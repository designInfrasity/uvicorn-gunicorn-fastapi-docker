"""
Multi-Architecture Build Validation Tests

This test suite validates that Docker image builds work correctly for both
amd64 and arm64 platforms with the optimized Dockerfiles.

Test Coverage:
- Multi-architecture build success for all image variants
- BuildKit compatibility with multi-platform builds
- QEMU emulation setup and functionality
- Image functionality verification on both architectures
- GitHub Actions workflow compatibility validation

Usage:
    # Test all variants for multi-arch builds
    pytest tests/test_04_multiarch_validation.py -v

    # Test specific variant
    NAME=python3.11 pytest tests/test_04_multiarch_validation.py -v

    # Skip emulation tests (faster, amd64 only)
    SKIP_EMULATION_TESTS=1 pytest tests/test_04_multiarch_validation.py -v
"""

import docker
import json
import os
import pytest
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

# Initialize Docker client
client = docker.from_env()

# Constants
DOCKER_IMAGES_DIR = Path("/code/docker-images")
PLATFORMS = ["linux/amd64", "linux/arm64"]
IMAGE_VARIANTS = [
    "python3.9",
    "python3.9-slim",
    "python3.10",
    "python3.10-slim",
    "python3.11",
    "python3.11-slim",
]

# Get environment variables
CURRENT_VARIANT = os.getenv("NAME")
SKIP_EMULATION_TESTS = os.getenv("SKIP_EMULATION_TESTS", "0") == "1"


def get_host_architecture() -> str:
    """
    Get the current host architecture.

    Returns:
        str: Architecture string (e.g., 'amd64', 'arm64')
    """
    result = subprocess.run(
        ["uname", "-m"],
        capture_output=True,
        text=True,
        timeout=10
    )
    arch = result.stdout.strip()
    # Map common arch strings to Docker platform arch
    arch_map = {
        "x86_64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return arch_map.get(arch, arch)


def check_qemu_support() -> bool:
    """
    Check if QEMU emulation is available for multi-platform builds.

    Returns:
        bool: True if QEMU is available, False otherwise
    """
    try:
        # Check if binfmt_misc is setup for QEMU
        result = subprocess.run(
            ["docker", "run", "--rm", "--privileged", "tonistiigi/binfmt", "--install", "all"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except Exception:
        return False


def build_multiarch_image(variant: str, platforms: List[str], use_cache: bool = True) -> Dict[str, any]:
    """
    Build a Docker image for multiple platforms using docker buildx.

    Args:
        variant: Image variant name (e.g., 'python3.11', 'python3.11-slim')
        platforms: List of platform strings (e.g., ['linux/amd64', 'linux/arm64'])
        use_cache: Whether to use Docker cache

    Returns:
        Dict with build results including success status and build time
    """
    dockerfile = f"{variant}.dockerfile"
    platforms_str = ",".join(platforms)

    # Build command using docker buildx
    cmd = [
        "docker", "buildx", "build",
        "--platform", platforms_str,
        "-f", str(DOCKER_IMAGES_DIR / dockerfile),
        "-t", f"tiangolo/uvicorn-gunicorn-fastapi:{variant}-multiarch-test",
        str(DOCKER_IMAGES_DIR)
    ]

    if not use_cache:
        cmd.insert(3, "--no-cache")

    # Add load flag to load image into docker (only works for single platform)
    if len(platforms) == 1:
        cmd.insert(3, "--load")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "DOCKER_BUILDKIT": "1"}
        )

        build_time = time.time() - start_time

        return {
            "success": result.returncode == 0,
            "build_time": build_time,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "platforms": platforms,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "build_time": 600,
            "error": "Build timeout after 10 minutes",
            "platforms": platforms,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "platforms": platforms,
        }


def inspect_image_architecture(image_name: str) -> Optional[str]:
    """
    Inspect a Docker image to determine its architecture.

    Args:
        image_name: Full image name with tag

    Returns:
        Architecture string or None if inspection fails
    """
    try:
        image = client.images.get(image_name)
        return image.attrs.get("Architecture", "unknown")
    except docker.errors.ImageNotFound:
        return None
    except Exception:
        return None


def test_image_on_platform(variant: str, platform: str) -> Dict[str, any]:
    """
    Test that an image runs correctly on a specific platform.

    Args:
        variant: Image variant name
        platform: Platform string (e.g., 'linux/amd64')

    Returns:
        Dict with test results
    """
    image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant}-multiarch-test"
    container_name = f"test-multiarch-{variant}-{platform.replace('/', '-')}"

    # Clean up any existing container
    try:
        old_container = client.containers.get(container_name)
        old_container.remove(force=True)
    except docker.errors.NotFound:
        pass

    try:
        # Run container with platform specification
        container = client.containers.run(
            image_name,
            name=container_name,
            platform=platform,
            detach=True,
            ports={"80/tcp": None},  # Bind to random port
            remove=False
        )

        # Wait for container to start
        time.sleep(5)

        # Reload container to get updated info
        container.reload()

        # Check if container is running
        is_running = container.status == "running"

        # Get logs
        logs = container.logs().decode("utf-8")

        # Cleanup
        container.stop(timeout=5)
        container.remove()

        return {
            "success": is_running,
            "status": container.status,
            "logs": logs,
            "platform": platform,
        }

    except Exception as e:
        # Cleanup on error
        try:
            container = client.containers.get(container_name)
            container.remove(force=True)
        except:
            pass

        return {
            "success": False,
            "error": str(e),
            "platform": platform,
        }


class TestQEMUSetup:
    """Test QEMU emulation setup for multi-platform builds."""

    def test_qemu_available(self):
        """Test that QEMU emulation is available or can be installed."""
        if SKIP_EMULATION_TESTS:
            pytest.skip("Emulation tests skipped (SKIP_EMULATION_TESTS=1)")

        # Try to setup QEMU
        qemu_available = check_qemu_support()

        if not qemu_available:
            pytest.skip("QEMU emulation not available - skipping multi-arch tests")

        assert qemu_available, "QEMU emulation should be available"

    def test_buildx_available(self):
        """Test that docker buildx is available."""
        result = subprocess.run(
            ["docker", "buildx", "version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, "docker buildx should be available"
        assert "github.com/docker/buildx" in result.stdout, "buildx version output should be valid"

    def test_buildx_builder_exists(self):
        """Test that a buildx builder instance is available."""
        # List builders
        result = subprocess.run(
            ["docker", "buildx", "ls"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0, "docker buildx ls should succeed"
        # Should have at least the default builder
        assert "default" in result.stdout or "desktop-linux" in result.stdout, "At least one builder should exist"


class TestMultiArchBuildSuccess:
    """Test that optimized Dockerfiles build successfully for both amd64 and arm64."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_single_platform_build_amd64(self, variant):
        """Test building for amd64 platform only."""
        # Skip if testing specific variant and this is not it
        if CURRENT_VARIANT and variant != CURRENT_VARIANT:
            pytest.skip(f"Only testing variant: {CURRENT_VARIANT}")

        result = build_multiarch_image(variant, ["linux/amd64"], use_cache=True)

        assert result["success"], f"Build should succeed for {variant} on amd64. Error: {result.get('stderr', '')}"
        assert result["build_time"] < 600, f"Build should complete within 10 minutes, took {result['build_time']:.1f}s"

        print(f"✅ {variant} built successfully for amd64 in {result['build_time']:.1f}s")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_single_platform_build_arm64(self, variant):
        """Test building for arm64 platform (may use emulation)."""
        # Skip if testing specific variant and this is not it
        if CURRENT_VARIANT and variant != CURRENT_VARIANT:
            pytest.skip(f"Only testing variant: {CURRENT_VARIANT}")

        if SKIP_EMULATION_TESTS and get_host_architecture() != "arm64":
            pytest.skip("Emulation tests skipped (SKIP_EMULATION_TESTS=1)")

        # Setup QEMU if needed
        if get_host_architecture() != "arm64":
            qemu_available = check_qemu_support()
            if not qemu_available:
                pytest.skip("QEMU emulation not available")

        result = build_multiarch_image(variant, ["linux/arm64"], use_cache=True)

        assert result["success"], f"Build should succeed for {variant} on arm64. Error: {result.get('stderr', '')}"
        assert result["build_time"] < 600, f"Build should complete within 10 minutes, took {result['build_time']:.1f}s"

        print(f"✅ {variant} built successfully for arm64 in {result['build_time']:.1f}s")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_multi_platform_build_both(self, variant):
        """Test building for both amd64 and arm64 simultaneously."""
        # Skip if testing specific variant and this is not it
        if CURRENT_VARIANT and variant != CURRENT_VARIANT:
            pytest.skip(f"Only testing variant: {CURRENT_VARIANT}")

        if SKIP_EMULATION_TESTS and get_host_architecture() != "arm64":
            pytest.skip("Emulation tests skipped (SKIP_EMULATION_TESTS=1)")

        # Setup QEMU if needed
        if get_host_architecture() != "arm64":
            qemu_available = check_qemu_support()
            if not qemu_available:
                pytest.skip("QEMU emulation not available")

        result = build_multiarch_image(variant, PLATFORMS, use_cache=True)

        assert result["success"], f"Multi-platform build should succeed for {variant}. Error: {result.get('stderr', '')}"
        assert result["build_time"] < 900, f"Multi-platform build should complete within 15 minutes, took {result['build_time']:.1f}s"

        print(f"✅ {variant} built successfully for both platforms in {result['build_time']:.1f}s")


class TestBuildKitCacheMultiArch:
    """Test that BuildKit cache works correctly for multi-architecture builds."""

    def test_cache_effectiveness_multiarch(self):
        """Test that cache improves build time for multi-arch builds."""
        if CURRENT_VARIANT:
            variant = CURRENT_VARIANT
        else:
            # Use python3.11 as default test variant
            variant = "python3.11"

        if SKIP_EMULATION_TESTS and get_host_architecture() != "arm64":
            pytest.skip("Emulation tests skipped (SKIP_EMULATION_TESTS=1)")

        # Setup QEMU if needed
        if get_host_architecture() != "arm64":
            qemu_available = check_qemu_support()
            if not qemu_available:
                pytest.skip("QEMU emulation not available")

        # Build without cache (cold build)
        cold_result = build_multiarch_image(variant, PLATFORMS, use_cache=False)
        assert cold_result["success"], f"Cold build should succeed. Error: {cold_result.get('stderr', '')}"

        # Build with cache (warm build)
        warm_result = build_multiarch_image(variant, PLATFORMS, use_cache=True)
        assert warm_result["success"], f"Warm build should succeed. Error: {warm_result.get('stderr', '')}"

        # Calculate cache effectiveness
        cold_time = cold_result["build_time"]
        warm_time = warm_result["build_time"]
        effectiveness = ((cold_time - warm_time) / cold_time) * 100 if cold_time > 0 else 0

        print(f"\n🧊 Cold build (no cache): {cold_time:.1f}s")
        print(f"🔥 Warm build (with cache): {warm_time:.1f}s")
        print(f"⚡ Cache effectiveness: {effectiveness:.1f}%")

        # Cache should provide at least 30% improvement for multi-arch builds
        # (lower threshold than single-arch due to emulation overhead)
        assert effectiveness >= 30, f"Cache should provide at least 30% improvement, got {effectiveness:.1f}%"


class TestImageFunctionality:
    """Test that images function correctly on both architectures."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_image_runs_on_amd64(self, variant):
        """Test that image runs successfully on amd64."""
        # Skip if testing specific variant and this is not it
        if CURRENT_VARIANT and variant != CURRENT_VARIANT:
            pytest.skip(f"Only testing variant: {CURRENT_VARIANT}")

        # First build the image for amd64 only
        build_result = build_multiarch_image(variant, ["linux/amd64"], use_cache=True)
        if not build_result["success"]:
            pytest.skip(f"Image build failed for {variant}")

        # Test the image
        test_result = test_image_on_platform(variant, "linux/amd64")

        assert test_result["success"], f"Image should run on amd64. Error: {test_result.get('error', '')}"
        assert "Uvicorn running" in test_result["logs"] or "Started server process" in test_result["logs"], \
            "Container logs should show Uvicorn started"

        print(f"✅ {variant} runs successfully on amd64")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_image_runs_on_arm64(self, variant):
        """Test that image runs successfully on arm64 (may use emulation)."""
        # Skip if testing specific variant and this is not it
        if CURRENT_VARIANT and variant != CURRENT_VARIANT:
            pytest.skip(f"Only testing variant: {CURRENT_VARIANT}")

        if SKIP_EMULATION_TESTS and get_host_architecture() != "arm64":
            pytest.skip("Emulation tests skipped (SKIP_EMULATION_TESTS=1)")

        # Setup QEMU if needed
        if get_host_architecture() != "arm64":
            qemu_available = check_qemu_support()
            if not qemu_available:
                pytest.skip("QEMU emulation not available")

        # First build the image for arm64 only
        build_result = build_multiarch_image(variant, ["linux/arm64"], use_cache=True)
        if not build_result["success"]:
            pytest.skip(f"Image build failed for {variant}")

        # Test the image
        test_result = test_image_on_platform(variant, "linux/arm64")

        assert test_result["success"], f"Image should run on arm64. Error: {test_result.get('error', '')}"
        assert "Uvicorn running" in test_result["logs"] or "Started server process" in test_result["logs"], \
            "Container logs should show Uvicorn started"

        print(f"✅ {variant} runs successfully on arm64")


class TestGitHubActionsCompatibility:
    """Test GitHub Actions workflow compatibility with optimized Dockerfiles."""

    def test_workflow_file_exists(self):
        """Test that the deploy workflow file exists."""
        workflow_path = Path("/code/.github/workflows/deploy.yml")
        assert workflow_path.exists(), "Deploy workflow file should exist"

    def test_workflow_has_multiarch_platforms(self):
        """Test that workflow includes multi-arch platform configuration."""
        workflow_path = Path("/code/.github/workflows/deploy.yml")

        with open(workflow_path, "r") as f:
            content = f.read()

        # Check for multi-platform configuration
        assert "platforms:" in content, "Workflow should have platforms configuration"
        assert "linux/amd64" in content, "Workflow should include amd64 platform"
        assert "linux/arm64" in content, "Workflow should include arm64 platform"

    def test_workflow_has_buildx_setup(self):
        """Test that workflow sets up Docker Buildx for multi-platform builds."""
        workflow_path = Path("/code/.github/workflows/deploy.yml")

        with open(workflow_path, "r") as f:
            content = f.read()

        # Check for buildx setup
        assert "setup-buildx-action" in content, "Workflow should setup Docker Buildx"

    def test_workflow_matrix_includes_all_variants(self):
        """Test that workflow matrix includes all image variants."""
        workflow_path = Path("/code/.github/workflows/deploy.yml")

        with open(workflow_path, "r") as f:
            content = f.read()

        # Check that all variants are in the matrix
        for variant in IMAGE_VARIANTS:
            # Handle latest tag (which is python3.11)
            if variant == "python3.11":
                assert "latest" in content or variant in content, f"Workflow should include {variant}"
            else:
                assert variant in content, f"Workflow should include {variant}"

    def test_workflow_uses_correct_context(self):
        """Test that workflow uses docker-images directory as context."""
        workflow_path = Path("/code/.github/workflows/deploy.yml")

        with open(workflow_path, "r") as f:
            content = f.read()

        # Check for correct context
        assert "./docker-images" in content or "docker-images" in content, \
            "Workflow should use docker-images directory as build context"

    def test_dockerfile_syntax_compatible_with_buildx(self):
        """Test that Dockerfiles use syntax compatible with buildx multi-platform builds."""
        for variant in IMAGE_VARIANTS:
            dockerfile_path = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"

            with open(dockerfile_path, "r") as f:
                content = f.read()

            # Check for multi-platform compatible instructions
            # Should not have architecture-specific commands that would break multi-platform builds
            assert "uname -m" not in content or "# multiarch-compatible" in content, \
                f"{variant}.dockerfile should not have arch-specific commands"

            # Should use standard base images (not arch-specific)
            lines = content.split("\n")
            from_lines = [l for l in lines if l.strip().startswith("FROM")]
            for from_line in from_lines:
                assert "amd64/" not in from_line and "arm64/" not in from_line, \
                    f"{variant}.dockerfile should use multi-arch base images, not arch-specific ones"


class TestMultiArchPerformance:
    """Test performance characteristics of multi-architecture builds."""

    def test_multiarch_build_time_reasonable(self):
        """Test that multi-arch builds complete in reasonable time."""
        if CURRENT_VARIANT:
            variant = CURRENT_VARIANT
        else:
            variant = "python3.11-slim"  # Use slim for faster test

        if SKIP_EMULATION_TESTS and get_host_architecture() != "arm64":
            pytest.skip("Emulation tests skipped (SKIP_EMULATION_TESTS=1)")

        # Setup QEMU if needed
        if get_host_architecture() != "arm64":
            qemu_available = check_qemu_support()
            if not qemu_available:
                pytest.skip("QEMU emulation not available")

        result = build_multiarch_image(variant, PLATFORMS, use_cache=True)

        assert result["success"], f"Build should succeed"

        # Multi-arch builds with emulation can be slower, allow up to 15 minutes
        assert result["build_time"] < 900, \
            f"Multi-arch build should complete within 15 minutes, took {result['build_time']:.1f}s"

        # Categorize performance
        if result["build_time"] < 120:
            performance = "Excellent"
        elif result["build_time"] < 300:
            performance = "Good"
        elif result["build_time"] < 600:
            performance = "Fair"
        else:
            performance = "Slow"

        print(f"\n⏱️  Multi-arch build time: {result['build_time']:.1f}s ({performance})")


class TestDockerfileOptimizationPreservation:
    """Test that multi-arch builds preserve all Dockerfile optimizations."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_layer_ordering_preserved_multiarch(self, variant):
        """Test that layer ordering is preserved in multi-arch builds."""
        if CURRENT_VARIANT and variant != CURRENT_VARIANT:
            pytest.skip(f"Only testing variant: {CURRENT_VARIANT}")

        dockerfile_path = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"

        with open(dockerfile_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip() and not l.strip().startswith("#")]

        # Find key instruction indices
        from_idx = next((i for i, l in enumerate(lines) if l.startswith("FROM")), -1)
        copy_req_idx = next((i for i, l in enumerate(lines) if "requirements.txt" in l), -1)
        pip_idx = next((i for i, l in enumerate(lines) if l.startswith("RUN") and "pip install" in l), -1)
        copy_app_idx = next((i for i, l in enumerate(lines) if "COPY ./app" in l), -1)

        # Verify ordering
        assert from_idx >= 0, f"{variant}: Should have FROM instruction"
        assert copy_req_idx >= 0, f"{variant}: Should copy requirements.txt"
        assert pip_idx >= 0, f"{variant}: Should have pip install"
        assert copy_app_idx >= 0, f"{variant}: Should copy app"

        # Verify optimal order for caching
        assert from_idx < copy_req_idx < pip_idx < copy_app_idx, \
            f"{variant}: Layer ordering should be optimal for caching (FROM -> COPY requirements -> RUN pip -> COPY app)"

        print(f"✅ {variant} maintains optimal layer ordering for multi-arch builds")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
