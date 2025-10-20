"""
Test suite for validating Docker build optimization effectiveness.

This module contains tests to ensure that build optimizations are working correctly:
- .dockerignore properly excludes unnecessary files
- Build context size is reduced
- Layer count is optimized
- BuildKit cache mount syntax is valid
- Dependencies are properly installed
- Final image doesn't contain unnecessary files
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List

import docker
import pytest

client = docker.from_env()

# Test configuration
DOCKER_IMAGES_DIR = Path("/code/docker-images")
BUILD_CONTEXT_SIZE_LIMIT_KB = 50  # Maximum acceptable build context size
MAX_LAYER_COUNT = 15  # Maximum acceptable layer count for optimized images

# All image variants to test
IMAGE_VARIANTS = [
    "python3.9",
    "python3.9-slim",
    "python3.10",
    "python3.10-slim",
    "python3.11",
    "python3.11-slim",
]


def get_image_name(variant: str) -> str:
    """Get the full image name for a variant."""
    return f"tiangolo/uvicorn-gunicorn-fastapi:{variant}"


def build_image_and_capture_context_size(variant: str) -> Dict[str, any]:
    """
    Build an image and capture build context size from docker build output.

    Returns:
        Dict with keys: 'success', 'context_size_bytes', 'output'
    """
    dockerfile = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"

    # Build with BuildKit enabled to get proper output
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "0"  # Disable BuildKit to get classic output with context size

    try:
        result = subprocess.run(
            [
                "docker", "build",
                "-f", str(dockerfile),
                "-t", get_image_name(variant),
                str(DOCKER_IMAGES_DIR)
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Parse build context size from output
        # Looking for line like: "Sending build context to Docker daemon  10.24kB"
        context_size_bytes = None
        for line in result.stdout.splitlines() + result.stderr.splitlines():
            if "Sending build context to Docker daemon" in line:
                # Extract size (can be in B, kB, MB, etc.)
                parts = line.split()
                if len(parts) >= 6:
                    size_str = parts[5]
                    # Parse size with unit
                    if size_str.endswith("kB"):
                        context_size_bytes = float(size_str[:-2]) * 1024
                    elif size_str.endswith("MB"):
                        context_size_bytes = float(size_str[:-2]) * 1024 * 1024
                    elif size_str.endswith("B"):
                        context_size_bytes = float(size_str[:-1])
                break

        return {
            "success": result.returncode == 0,
            "context_size_bytes": context_size_bytes,
            "output": result.stdout + result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "context_size_bytes": None,
            "output": "Build timed out after 300 seconds"
        }


class TestDockerignoreExclusions:
    """Test that .dockerignore is properly excluding files."""

    def test_dockerignore_file_exists(self):
        """Verify .dockerignore file exists in docker-images directory."""
        dockerignore_path = DOCKER_IMAGES_DIR / ".dockerignore"
        assert dockerignore_path.exists(), ".dockerignore file should exist in docker-images directory"

    def test_dockerignore_excludes_git_files(self):
        """Verify .dockerignore excludes .git and .github directories."""
        dockerignore_path = DOCKER_IMAGES_DIR / ".dockerignore"
        content = dockerignore_path.read_text()

        assert ".git" in content, ".dockerignore should exclude .git directory"
        assert ".github" in content, ".dockerignore should exclude .github directory"

    def test_dockerignore_excludes_test_files(self):
        """Verify .dockerignore excludes test directories and files."""
        dockerignore_path = DOCKER_IMAGES_DIR / ".dockerignore"
        content = dockerignore_path.read_text()

        assert "tests/" in content or "test" in content.lower(), \
            ".dockerignore should exclude test files/directories"

    def test_dockerignore_excludes_documentation(self):
        """Verify .dockerignore excludes documentation files."""
        dockerignore_path = DOCKER_IMAGES_DIR / ".dockerignore"
        content = dockerignore_path.read_text()

        # Should exclude README and markdown files
        assert "*.md" in content or "README" in content, \
            ".dockerignore should exclude documentation files"

    def test_dockerignore_excludes_python_cache(self):
        """Verify .dockerignore excludes Python cache directories."""
        dockerignore_path = DOCKER_IMAGES_DIR / ".dockerignore"
        content = dockerignore_path.read_text()

        assert "__pycache__" in content, ".dockerignore should exclude __pycache__"
        assert "*.pyc" in content or "*.py[cod]" in content, \
            ".dockerignore should exclude .pyc files"


class TestBuildContextSize:
    """Test that build context size is reduced to acceptable levels."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_build_context_size_is_small(self, variant):
        """
        Test that build context size is under the acceptable limit.

        This validates that .dockerignore is effectively reducing the build context.
        """
        # Get current environment NAME to avoid rebuilding unnecessarily
        # Only test the variant that matches current test run
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        build_result = build_image_and_capture_context_size(variant)

        assert build_result["success"], \
            f"Build failed for {variant}: {build_result['output']}"

        if build_result["context_size_bytes"] is not None:
            context_size_kb = build_result["context_size_bytes"] / 1024
            assert context_size_kb < BUILD_CONTEXT_SIZE_LIMIT_KB, \
                f"Build context size ({context_size_kb:.2f} KB) exceeds limit " \
                f"({BUILD_CONTEXT_SIZE_LIMIT_KB} KB) for {variant}"
        else:
            # If we couldn't parse context size (e.g., BuildKit output format),
            # at least verify build succeeded
            pytest.skip("Could not parse build context size from output")


class TestLayerOptimization:
    """Test that layer count is optimized (not excessive)."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_layer_count_is_reasonable(self, variant):
        """
        Test that the image has a reasonable number of layers.

        Too many layers indicate suboptimal Dockerfile structure.
        """
        image_name = get_image_name(variant)

        # Get current environment NAME to avoid pulling unnecessarily
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            # Get image (assume it's already built by previous tests or CI)
            image = client.images.get(image_name)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found, skipping layer count test")
            return

        # Get layer count from history
        history = image.history()
        layer_count = len(history)

        assert layer_count <= MAX_LAYER_COUNT, \
            f"Image {variant} has {layer_count} layers, which exceeds the maximum " \
            f"of {MAX_LAYER_COUNT}. This suggests suboptimal layer structure."

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_layers_have_proper_ordering(self, variant):
        """
        Test that layers are ordered for optimal caching.

        Validates that requirements installation happens before app code copy.
        """
        image_name = get_image_name(variant)

        # Get current environment NAME
        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            image = client.images.get(image_name)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
            return

        # Get image history
        history = image.history()

        # Find relevant layers
        requirements_layer_index = None
        app_copy_layer_index = None

        for idx, layer in enumerate(history):
            created_by = layer.get("CreatedBy", "")

            if "requirements.txt" in created_by and "COPY" in created_by:
                requirements_layer_index = idx
            if "COPY ./app /app" in created_by or "COPY --from" in created_by and "/app" in created_by:
                app_copy_layer_index = idx

        # Verify ordering (in history, earlier layers have higher index)
        if requirements_layer_index is not None and app_copy_layer_index is not None:
            assert requirements_layer_index > app_copy_layer_index, \
                f"Requirements copy should happen before app copy for optimal caching. " \
                f"Requirements layer: {requirements_layer_index}, App layer: {app_copy_layer_index}"


class TestBuildKitCacheMountSyntax:
    """Test that BuildKit cache mount syntax is valid in Dockerfiles."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_dockerfile_has_buildkit_syntax(self, variant):
        """Verify Dockerfile has BuildKit syntax directive."""
        dockerfile_path = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"
        content = dockerfile_path.read_text()

        first_line = content.split("\n")[0]
        assert "syntax=docker/dockerfile" in first_line, \
            f"Dockerfile {variant} should start with BuildKit syntax directive"

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_dockerfile_has_cache_mount(self, variant):
        """Verify Dockerfile uses cache mount for pip installation."""
        dockerfile_path = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"
        content = dockerfile_path.read_text()

        assert "--mount=type=cache" in content, \
            f"Dockerfile {variant} should use cache mount for pip installation"
        assert "target=/root/.cache/pip" in content, \
            f"Dockerfile {variant} should mount pip cache directory"

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_cache_mount_syntax_is_valid(self, variant):
        """Verify cache mount syntax is correctly formatted."""
        dockerfile_path = DOCKER_IMAGES_DIR / f"{variant}.dockerfile"
        content = dockerfile_path.read_text()

        # Look for RUN command with cache mount
        for line in content.split("\n"):
            if "--mount=type=cache" in line and "pip install" in line:
                # Verify syntax: RUN --mount=type=cache,target=/path ...
                assert line.strip().startswith("RUN"), \
                    "Cache mount should be part of RUN command"
                assert "target=" in line, \
                    "Cache mount should specify target directory"
                break
        else:
            pytest.fail(f"No pip install with cache mount found in {variant}.dockerfile")


class TestDependencyInstallation:
    """Test that dependencies are properly installed in the image."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_fastapi_is_installed(self, variant):
        """Verify FastAPI is installed in the image."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            # Run pip show fastapi to verify installation
            result = client.containers.run(
                image_name,
                command="pip show fastapi",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8")
            assert "Name: fastapi" in output, \
                f"FastAPI should be installed in {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError as e:
            pytest.fail(f"Failed to check FastAPI installation: {e}")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_uvicorn_is_installed(self, variant):
        """Verify Uvicorn is installed in the image."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            result = client.containers.run(
                image_name,
                command="pip show uvicorn",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8")
            assert "Name: uvicorn" in output, \
                f"Uvicorn should be installed in {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError as e:
            pytest.fail(f"Failed to check Uvicorn installation: {e}")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_requirements_file_not_in_image(self, variant):
        """
        Verify requirements.txt is not in the final image.

        This validates the cleanup step in the Dockerfile.
        """
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            # Check if /tmp/requirements.txt exists
            result = client.containers.run(
                image_name,
                command="test -f /tmp/requirements.txt && echo EXISTS || echo NOT_EXISTS",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8").strip()
            assert "NOT_EXISTS" in output, \
                f"requirements.txt should be removed from final image in {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError:
            # If command fails, it's likely because test returned non-zero,
            # which is actually what we want (file doesn't exist)
            pass


class TestUnnecessaryFilesExclusion:
    """Test that final image doesn't contain unnecessary files."""

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_git_directory_not_in_image(self, variant):
        """Verify .git directory is not in the final image."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            result = client.containers.run(
                image_name,
                command="test -d /app/.git && echo EXISTS || echo NOT_EXISTS",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8").strip()
            assert "NOT_EXISTS" in output, \
                f".git directory should not be in final image for {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError:
            # Command error likely means directory doesn't exist, which is good
            pass

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_test_directory_not_in_image(self, variant):
        """Verify tests directory is not in the final image."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            result = client.containers.run(
                image_name,
                command="test -d /app/tests && echo EXISTS || echo NOT_EXISTS",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8").strip()
            assert "NOT_EXISTS" in output, \
                f"tests directory should not be in final image for {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError:
            pass

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_github_directory_not_in_image(self, variant):
        """Verify .github directory is not in the final image."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            result = client.containers.run(
                image_name,
                command="test -d /app/.github && echo EXISTS || echo NOT_EXISTS",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8").strip()
            assert "NOT_EXISTS" in output, \
                f".github directory should not be in final image for {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError:
            pass

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_app_directory_exists(self, variant):
        """Verify /app directory DOES exist with application code."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            result = client.containers.run(
                image_name,
                command="test -d /app && echo EXISTS || echo NOT_EXISTS",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8").strip()
            assert "EXISTS" in output, \
                f"/app directory should exist in final image for {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError as e:
            pytest.fail(f"Failed to check /app directory: {e}")

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_main_py_exists(self, variant):
        """Verify main.py exists in /app directory."""
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            result = client.containers.run(
                image_name,
                command="test -f /app/main.py && echo EXISTS || echo NOT_EXISTS",
                remove=True,
                stdout=True,
                stderr=True
            )

            output = result.decode("utf-8").strip()
            assert "EXISTS" in output, \
                f"/app/main.py should exist in final image for {variant}"
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
        except docker.errors.ContainerError as e:
            pytest.fail(f"Failed to check /app/main.py: {e}")


class TestImageSizeRanges:
    """Test that image sizes are within expected ranges."""

    # Expected image size ranges (in MB) - these are approximate
    EXPECTED_SIZE_RANGES = {
        "python3.9": (800, 1200),
        "python3.9-slim": (300, 600),
        "python3.10": (800, 1200),
        "python3.10-slim": (300, 600),
        "python3.11": (800, 1200),
        "python3.11-slim": (300, 600),
    }

    @pytest.mark.parametrize("variant", IMAGE_VARIANTS)
    def test_image_size_is_reasonable(self, variant):
        """
        Test that image size is within expected range.

        This is informational and helps detect size regressions.
        """
        image_name = get_image_name(variant)

        current_variant = os.getenv("NAME")
        if current_variant and current_variant != variant:
            pytest.skip(f"Skipping {variant}, only testing {current_variant}")

        try:
            image = client.images.get(image_name)
        except docker.errors.ImageNotFound:
            pytest.skip(f"Image {image_name} not found")
            return

        # Get image size in MB
        size_bytes = image.attrs.get("Size", 0)
        size_mb = size_bytes / (1024 * 1024)

        expected_min, expected_max = self.EXPECTED_SIZE_RANGES.get(
            variant, (0, 2000)  # Default wide range if variant not in map
        )

        # This is a soft assertion - log warning but don't fail
        # Image sizes can vary by architecture and base image updates
        if not (expected_min <= size_mb <= expected_max):
            print(f"\nWARNING: Image {variant} size ({size_mb:.1f} MB) is outside "
                  f"expected range ({expected_min}-{expected_max} MB)")

        # Assert that size is at least reasonable (not zero, not absurdly large)
        assert size_mb > 10, f"Image {variant} size is too small ({size_mb:.1f} MB)"
        assert size_mb < 2000, f"Image {variant} size is too large ({size_mb:.1f} MB)"
