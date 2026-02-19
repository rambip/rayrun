"""AnyWidget implementation for RayRun."""

import os
import json
import time
import secrets
from datetime import datetime, timezone
from typing import Optional, Callable
import logging

import anywidget
import traitlets
import ray

from .runpod_client import RunPodClient, GPU_TYPES, CPU_FLAVORS

logger = logging.getLogger(__name__)

# Path to static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


class RayRun(anywidget.AnyWidget):
    """Jupyter widget for managing RunPod Ray compute."""

    # Traitlets for state management
    status = traitlets.Unicode("stopped").tag(sync=True)
    pod_id = traitlets.Unicode("").tag(sync=True)
    ip_address = traitlets.Unicode("").tag(sync=True)
    ray_url = traitlets.Unicode("").tag(sync=True)
    dashboard_url = traitlets.Unicode("").tag(sync=True)
    started_at = traitlets.Float(0).tag(sync=True)
    elapsed_seconds = traitlets.Float(0).tag(sync=True)
    error_message = traitlets.Unicode("").tag(sync=True)
    selected_gpu = traitlets.Unicode("gpu.a100").tag(sync=True)
    idle_timeout_minutes = traitlets.Int(30).tag(sync=True)

    # Static configuration (not synced to frontend)
    _esm = os.path.join(STATIC_DIR, "widget.js")
    _css = os.path.join(STATIC_DIR, "widget.css")

    def __init__(
        self,
        instance_type: str = "gpu.a100",
        idle_timeout_minutes: int = 30,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the RayRun widget.

        Args:
            instance_type: GPU type identifier (e.g., "gpu.a100", "cpu.4c")
            idle_timeout_minutes: Minutes of inactivity before auto-shutdown
            api_key: RunPod API key (or from RUNPOD_API_KEY env var)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)

        # Get API key
        self.api_key = api_key or os.getenv("RUNPOD_API_KEY")
        if not self.api_key:
            self.error_message = "RUNPOD_API_KEY not set"
            self.status = "error"
            logger.error(self.error_message)
            return

        # Initialize RunPod client
        self._client = RunPodClient(self.api_key)
        self._ray_context = None

        # Parse instance type
        if instance_type.startswith("gpu."):
            self.selected_gpu = instance_type
            self._is_gpu = True
        elif instance_type.startswith("cpu."):
            self._is_gpu = False
            self._cpu_flavor = instance_type.split(".")[1]
        else:
            # Default to GPU A100
            self.selected_gpu = "gpu.a100"
            self._is_gpu = True

        self.idle_timeout_minutes = idle_timeout_minutes

        # Start elapsed time update loop
        self._start_elapsed_timer()

        # Listen for messages from frontend
        self.on_msg(self._handle_frontend_message)

    def _start_elapsed_timer(self):
        """Start a timer to update elapsed time."""
        import threading

        def update_elapsed():
            while True:
                if self.status == "running" and self.started_at > 0:
                    self.elapsed_seconds = time.time() - self.started_at
                time.sleep(1)

        timer_thread = threading.Thread(target=update_elapsed, daemon=True)
        timer_thread.start()

    def _handle_frontend_message(self, widget, content, buffers):
        """Handle messages from the frontend."""
        action = content.get("action")

        if action == "start":
            self._start_pod()
        elif action == "stop":
            self._stop_pod()
        elif action == "get_status":
            self._update_status()

    def _generate_ray_password(self) -> str:
        """Generate a secure random password for Ray authentication."""
        return secrets.token_urlsafe(32)

    def _get_gpu_type_id(self, gpu_type: str) -> str:
        """Map GPU type to RunPod GPU type ID."""
        gpu_map = {
            "gpu.a100": "NVIDIA A100 80GB PCIe",
            "gpu.a100-80gb-sxm": "NVIDIA A100 80GB SXM",
            "gpu.a100-40gb": "NVIDIA A100 40GB PCIe",
            "gpu.a6000": "NVIDIA RTX A6000",
            "gpu.v100": "NVIDIA V100",
            "gpu.h100": "NVIDIA H100 80GB SXM",
            "gpu.h100-pcie": "NVIDIA H100 80GB PCIe",
            "gpu.rtx4090": "NVIDIA GeForce RTX 4090",
            "gpu.rtx3090": "NVIDIA GeForce RTX 3090",
            "gpu.l40s": "NVIDIA L40S",
        }
        return gpu_map.get(gpu_type, "NVIDIA A100 80GB PCIe")

    def _start_pod(self):
        """Start the RunPod instance."""
        try:
            self.status = "starting"
            self.error_message = ""

            # Generate Ray authentication password
            ray_password = self._generate_ray_password()

            # Build environment variables
            env_vars = {
                "RUNPOD_API_KEY": self.api_key,
                "RUNPOD_POD_ID": "{{podId}}",  # Will be replaced by RunPod
                "IDLE_TIMEOUT_MINUTES": str(self.idle_timeout_minutes),
                "MAX_RUNTIME_HOURS": "6",
                "RAY_PASSWORD": ray_password,
            }

            # Create pod
            if self._is_gpu:
                gpu_type_id = self._get_gpu_type_id(self.selected_gpu)
                pod_data = self._client.create_pod(
                    name=f"rayrun-{int(time.time())}",
                    image="ghcr.io/rambip/rayrun:latest",
                    gpu_type_ids=[gpu_type_id],
                    env_vars=env_vars,
                    ports=["10001/tcp", "8265/http"],
                    cloud_type="COMMUNITY",
                    container_disk_in_gb=50,
                    volume_in_gb=20,
                )
            else:
                cpu_flavor = f"cpu{self._cpu_flavor}"
                pod_data = self._client.create_pod(
                    name=f"rayrun-{int(time.time())}",
                    image="ghcr.io/rambip/rayrun:latest",
                    cpu_flavor_ids=[cpu_flavor],
                    env_vars=env_vars,
                    ports=["10001/tcp", "8265/http"],
                    cloud_type="COMMUNITY",
                    container_disk_in_gb=50,
                    volume_in_gb=20,
                )

            self.pod_id = pod_data.get("id", "")

            # Wait for pod to be ready
            self.status = "starting"
            ready_pod = self._client.wait_for_ready(self.pod_id, timeout=300)

            # Update connection info
            self.ip_address = ready_pod.get("publicIp", "")
            self.ray_url = f"ray://{self.ip_address}:10001"
            self.dashboard_url = f"http://{self.ip_address}:8265"
            self.started_at = time.time()
            self.status = "running"

            logger.info(f"Pod started: {self.pod_id} at {self.ip_address}")

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            logger.error(f"Failed to start pod: {e}")

    def _stop_pod(self):
        """Stop the RunPod instance."""
        try:
            if not self.pod_id:
                self.status = "stopped"
                return

            self.status = "stopping"

            # Disconnect Ray if connected
            if self._ray_context is not None:
                ray.shutdown()
                self._ray_context = None

            # Delete pod
            self._client.delete_pod(self.pod_id)

            # Reset state
            self.pod_id = ""
            self.ip_address = ""
            self.ray_url = ""
            self.dashboard_url = ""
            self.started_at = 0
            self.elapsed_seconds = 0
            self.status = "stopped"

            logger.info("Pod stopped successfully")

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            logger.error(f"Failed to stop pod: {e}")

    def _update_status(self):
        """Update widget status from RunPod API."""
        try:
            if not self.pod_id:
                self.status = "stopped"
                return

            pod_data = self._client.get_pod(self.pod_id)
            desired_status = pod_data.get("desiredStatus")

            if desired_status == "RUNNING":
                self.status = "running"
                # Update IP in case it changed
                self.ip_address = pod_data.get("publicIp", self.ip_address)
                self.ray_url = f"ray://{self.ip_address}:10001"
                self.dashboard_url = f"http://{self.ip_address}:8265"
            elif desired_status in ["EXITED", "TERMINATED"]:
                self.status = "stopped"
                self.pod_id = ""
            else:
                self.status = "starting"

        except Exception as e:
            logger.warning(f"Failed to update status: {e}")
            # Pod might have been deleted
            self.status = "stopped"
            self.pod_id = ""

    def connect(self):
        """Connect to Ray cluster.

        Returns:
            bool: True if connected successfully
        """
        if self.status != "running":
            raise RuntimeError("Pod is not running. Start the VM first.")

        try:
            if self._ray_context is not None:
                logger.info("Already connected to Ray")
                return True

            # Connect to Ray
            ray.init(address=self.ray_url)
            self._ray_context = True

            logger.info(f"Connected to Ray at {self.ray_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Ray: {e}")
            raise RuntimeError(f"Failed to connect to Ray: {e}")

    def disconnect(self):
        """Disconnect from Ray cluster."""
        if self._ray_context is not None:
            ray.shutdown()
            self._ray_context = None
            logger.info("Disconnected from Ray")

    def __del__(self):
        """Cleanup when widget is destroyed."""
        try:
            self.disconnect()
        except:
            pass
