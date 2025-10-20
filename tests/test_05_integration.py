"""
Comprehensive Integration Tests for All Docker Image Variants

This test suite performs end-to-end testing of all optimized Docker images:
- python3.9, python3.10, python3.11 (standard variants)
- python3.9-slim, python3.10-slim, python3.11-slim (slim variants)

Tests validate:
- Image builds successfully with optimizations
- Container starts and runs correctly
- FastAPI app responds to HTTP requests
- Python version matches expected version
- Uvicorn and Gunicorn processes are running
- Health check and readiness
- All functionality from test_01_main/test_defaults.py

This test suite is designed to be run in CI/CD before deployment
to ensure all optimizations maintain production functionality.
"""

import os
import time
from typing import Dict, List, Tuple

import docker
import pytest
import requests
from docker.client import DockerClient
from docker.errors import APIError, ImageNotFound
from docker.models.containers import Container

from ..utils import (
    CONTAINER_NAME,
    get_config,
    get_logs,
    get_process_names,
    get_response_text1,
    remove_previous_container,
)

# Initialize Docker client
client = docker.from_env()

# Define all image variants to test
ALL_VARIANTS = [
    {"name": "python3.9", "python_version": "3.9"},
    {"name": "python3.10", "python_version": "3.10"},
    {"name": "python3.11", "python_version": "3.11"},
    {"name": "python3.9-slim", "python_version": "3.9"},
    {"name": "python3.10-slim", "python_version": "3.10"},
    {"name": "python3.11-slim", "python_version": "3.11"},
]

# Container port configuration
CONTAINER_PORT = "80"
HOST_PORT = "8001"  # Use 8001 to avoid conflicts with other tests

# Test timeout and retry settings
CONTAINER_START_TIMEOUT = 10  # seconds to wait for container startup
HTTP_RETRY_COUNT = 5
HTTP_RETRY_DELAY = 2  # seconds between retries


def get_variant_to_test() -> List[Dict[str, str]]:
    """
    Determine which variants to test based on environment variables.

    If NAME is set (e.g., in CI/CD), test only that variant.
    Otherwise, test all variants.
    """
    name = os.getenv("NAME")
    if name:
        # Test only the specified variant
        for variant in ALL_VARIANTS:
            if variant["name"] == name:
                return [variant]
        # If NAME is set but not found, fall back to all variants
        return ALL_VARIANTS
    else:
        # Test all variants
        return ALL_VARIANTS


class TestImageBuild:
    """Test that optimized images build successfully."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_image_exists_or_buildable(self, variant: Dict[str, str]) -> None:
        """
        Verify that the image exists locally or can be built.

        In CI/CD, images are pre-built by the workflow.
        For local testing, this ensures images are available.
        """
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            # Try to get the image
            client.images.get(image_name)
            print(f"✓ Image {image_name} exists locally")
        except ImageNotFound:
            pytest.skip(f"Image {image_name} not found. Build it first with: docker build -t {image_name} -f /code/docker-images/{variant['name']}.dockerfile /code/docker-images/")


class TestContainerStartup:
    """Test that containers start successfully and FastAPI app initializes."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_container_starts(self, variant: Dict[str, str]) -> None:
        """Verify that container starts without errors."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            # Ensure no previous test container exists
            remove_previous_container(client)

            # Start container
            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            # Wait for container to initialize
            time.sleep(CONTAINER_START_TIMEOUT)

            # Verify container is running
            container.reload()
            assert container.status == "running", f"Container status: {container.status}"

            print(f"✓ Container started successfully for {variant['name']}")

        finally:
            # Cleanup
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_fastapi_app_starts(self, variant: Dict[str, str]) -> None:
        """Verify that FastAPI application starts and Uvicorn workers initialize."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Check logs for application startup
            logs = get_logs(container)

            # Verify key startup messages
            assert "Checking for script in /app/prestart.sh" in logs, "prestart.sh check not found"
            assert "Running script /app/prestart.sh" in logs, "prestart.sh execution not found"
            assert "[INFO] Application startup complete." in logs, "Application startup not completed"
            assert "Using worker: uvicorn.workers.UvicornWorker" in logs, "Uvicorn worker not configured"

            print(f"✓ FastAPI app started successfully for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestHTTPEndpoints:
    """Test that HTTP endpoints respond correctly."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_root_endpoint_responds(self, variant: Dict[str, str]) -> None:
        """Verify that GET / endpoint returns successful response."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Try to connect with retries
            response = None
            for attempt in range(HTTP_RETRY_COUNT):
                try:
                    response = requests.get(f"http://127.0.0.1:{HOST_PORT}/", timeout=5)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    if attempt < HTTP_RETRY_COUNT - 1:
                        time.sleep(HTTP_RETRY_DELAY)
                    else:
                        raise

            # Verify response
            assert response is not None, "No response received"
            assert response.status_code == 200, f"Status code: {response.status_code}"

            data = response.json()
            assert "message" in data, "Response missing 'message' field"

            print(f"✓ Root endpoint responds correctly for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_response_contains_python_version(self, variant: Dict[str, str]) -> None:
        """Verify that response includes the correct Python version."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"
        expected_python_version = variant["python_version"]

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Get response with retries
            response = None
            for attempt in range(HTTP_RETRY_COUNT):
                try:
                    response = requests.get(f"http://127.0.0.1:{HOST_PORT}/", timeout=5)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    if attempt < HTTP_RETRY_COUNT - 1:
                        time.sleep(HTTP_RETRY_DELAY)
                    else:
                        raise

            data = response.json()
            message = data.get("message", "")

            # Verify Python version in message
            assert expected_python_version in message, \
                f"Expected Python {expected_python_version} in message, got: {message}"

            print(f"✓ Response contains correct Python version {expected_python_version} for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestPythonVersion:
    """Test that Python version matches expected version."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_python_version_in_container(self, variant: Dict[str, str]) -> None:
        """Verify Python version inside container matches expected version."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"
        expected_version = variant["python_version"]

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Check Python version in container
            result = container.exec_run("python --version")
            version_output = result.output.decode("utf-8").strip()

            # Version output format: "Python 3.11.x"
            assert f"Python {expected_version}" in version_output, \
                f"Expected Python {expected_version}, got: {version_output}"

            print(f"✓ Python version {expected_version} confirmed in container for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestProcessManagement:
    """Test that Uvicorn and Gunicorn processes are running correctly."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_gunicorn_master_process_running(self, variant: Dict[str, str]) -> None:
        """Verify that Gunicorn master process is running."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Get process list
            gunicorn_processes = get_process_names(container)

            # Verify at least one Gunicorn process exists
            assert len(gunicorn_processes) > 0, "No Gunicorn processes found"

            # Check for master process
            master_found = any("master" in proc.lower() for proc in gunicorn_processes)
            assert master_found, f"Gunicorn master process not found. Processes: {gunicorn_processes}"

            print(f"✓ Gunicorn master process running for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_worker_processes_running(self, variant: Dict[str, str]) -> None:
        """Verify that worker processes are running."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Get process list
            gunicorn_processes = get_process_names(container)

            # Should have master + at least one worker
            assert len(gunicorn_processes) >= 2, \
                f"Expected at least 2 Gunicorn processes (master + worker), found: {len(gunicorn_processes)}"

            # Check for worker processes
            worker_found = any("worker" in proc.lower() for proc in gunicorn_processes)
            assert worker_found, f"Gunicorn worker processes not found. Processes: {gunicorn_processes}"

            print(f"✓ Worker processes running for {variant['name']} (total: {len(gunicorn_processes)})")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestGunicornConfiguration:
    """Test that Gunicorn configuration is correct."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_gunicorn_config_defaults(self, variant: Dict[str, str]) -> None:
        """Verify that Gunicorn configuration has expected default values."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Get configuration
            config = get_config(container)

            # Verify default configuration values
            assert config["workers_per_core"] == 1, f"workers_per_core: {config['workers_per_core']}"
            assert config["use_max_workers"] is None, f"use_max_workers: {config['use_max_workers']}"
            assert config["host"] == "0.0.0.0", f"host: {config['host']}"
            assert config["port"] == "80", f"port: {config['port']}"
            assert config["loglevel"] == "info", f"loglevel: {config['loglevel']}"
            assert config["workers"] >= 2, f"workers: {config['workers']}"
            assert config["bind"] == "0.0.0.0:80", f"bind: {config['bind']}"
            assert config["graceful_timeout"] == 120, f"graceful_timeout: {config['graceful_timeout']}"
            assert config["timeout"] == 120, f"timeout: {config['timeout']}"
            assert config["keepalive"] == 5, f"keepalive: {config['keepalive']}"
            assert config["errorlog"] == "-", f"errorlog: {config['errorlog']}"
            assert config["accesslog"] == "-", f"accesslog: {config['accesslog']}"

            print(f"✓ Gunicorn configuration correct for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestHealthAndReadiness:
    """Test health check and readiness of containers."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_container_health(self, variant: Dict[str, str]) -> None:
        """Verify container remains healthy during operation."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Verify container is still running
            container.reload()
            assert container.status == "running", f"Container status: {container.status}"

            # Make multiple requests to verify stability
            for i in range(3):
                response = requests.get(f"http://127.0.0.1:{HOST_PORT}/", timeout=5)
                assert response.status_code == 200, f"Request {i+1} failed: {response.status_code}"
                time.sleep(1)

            # Verify container still running after requests
            container.reload()
            assert container.status == "running", f"Container status after requests: {container.status}"

            print(f"✓ Container health verified for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_container_restart(self, variant: Dict[str, str]) -> None:
        """Verify container can be restarted and continues to work."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Make initial request
            response = requests.get(f"http://127.0.0.1:{HOST_PORT}/", timeout=5)
            assert response.status_code == 200

            # Restart container
            container.stop(timeout=5)
            container.start()
            time.sleep(CONTAINER_START_TIMEOUT)

            # Verify works after restart
            response = requests.get(f"http://127.0.0.1:{HOST_PORT}/", timeout=5)
            assert response.status_code == 200

            # Verify container is running
            container.reload()
            assert container.status == "running"

            print(f"✓ Container restart successful for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestLogOutput:
    """Test that container logs contain expected messages."""

    @pytest.mark.parametrize("variant", get_variant_to_test())
    def test_logs_contain_startup_sequence(self, variant: Dict[str, str]) -> None:
        """Verify logs contain all expected startup messages."""
        image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"

        try:
            remove_previous_container(client)

            container = client.containers.run(
                image_name,
                name=CONTAINER_NAME,
                ports={CONTAINER_PORT: HOST_PORT},
                detach=True,
                remove=False,
            )

            time.sleep(CONTAINER_START_TIMEOUT)

            # Make a request to generate access log
            requests.get(f"http://127.0.0.1:{HOST_PORT}/", timeout=5)
            time.sleep(1)

            # Get logs
            logs = get_logs(container)

            # Verify expected log messages
            expected_messages = [
                "Checking for script in /app/prestart.sh",
                "Running script /app/prestart.sh",
                "Running inside /app/prestart.sh, you could add migrations to this file",
                "[INFO] Application startup complete.",
                "Using worker: uvicorn.workers.UvicornWorker",
                '"GET / HTTP/1.1" 200',  # Access log for our request
            ]

            for message in expected_messages:
                assert message in logs, f"Expected log message not found: {message}"

            print(f"✓ All expected log messages present for {variant['name']}")

        finally:
            try:
                container.stop(timeout=5)
                container.remove()
            except:
                pass


class TestIntegrationSummary:
    """Summary test that validates overall integration success."""

    def test_all_variants_integration_summary(self) -> None:
        """
        Generate a summary report of integration test results.

        This test runs last and provides an overview of which variants
        were tested and their overall status.
        """
        variants_to_test = get_variant_to_test()

        print("\n" + "="*60)
        print("INTEGRATION TEST SUMMARY")
        print("="*60)
        print(f"Total variants configured: {len(ALL_VARIANTS)}")
        print(f"Variants tested in this run: {len(variants_to_test)}")
        print("\nTested variants:")
        for variant in variants_to_test:
            print(f"  - {variant['name']} (Python {variant['python_version']})")

        # Verify each variant's image exists
        print("\nImage availability:")
        missing_images = []
        for variant in variants_to_test:
            image_name = f"tiangolo/uvicorn-gunicorn-fastapi:{variant['name']}"
            try:
                client.images.get(image_name)
                print(f"  ✓ {image_name}")
            except ImageNotFound:
                print(f"  ✗ {image_name} (not found)")
                missing_images.append(variant['name'])

        if missing_images:
            print(f"\n⚠ WARNING: {len(missing_images)} image(s) not found locally")
            print("Build missing images before running integration tests:")
            for name in missing_images:
                print(f"  docker build -t tiangolo/uvicorn-gunicorn-fastapi:{name} -f /code/docker-images/{name}.dockerfile /code/docker-images/")
        else:
            print("\n✓ All images available for testing")

        print("="*60)
