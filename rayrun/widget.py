"""AnyWidget implementation for RayRun with async support."""

import asyncio
import logging
import os
import secrets
import time
from typing import Optional

import anywidget
import traitlets

from .runpod_client import RunPodClient

logger = logging.getLogger(__name__)

# Path to static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


GPU_TIERS = {
    "cheap": [
        "NVIDIA GeForce RTX 4090",
        "NVIDIA GeForce RTX 3090",
        "NVIDIA GeForce RTX 3080 Ti",
        "NVIDIA GeForce RTX 3080",
        "NVIDIA GeForce RTX 3070",
        "NVIDIA GeForce RTX 3090 Ti",
        "NVIDIA GeForce RTX 4070 Ti",
        "NVIDIA GeForce RTX 4080",
        "NVIDIA GeForce RTX 4080 SUPER",
        "NVIDIA GeForce RTX 5090",
        "NVIDIA GeForce RTX 5080",
        "NVIDIA RTX A2000",
        "NVIDIA RTX A4000",
        "NVIDIA RTX A4500",
        "NVIDIA A30",
        "NVIDIA L4",
        "Tesla T4",
        "Tesla V100-PCIE-16GB",
        "Tesla V100-SXM2-32GB",
        "Tesla V100-FHHL-16GB",
        "Tesla V100-PCIE-32GB",
        "Tesla V100-SXM2-16GB",
        "NVIDIA A40",
    ],
    "medium": [
        "NVIDIA RTX A5000",
        "NVIDIA A40",
        "NVIDIA RTX A6000",
        "NVIDIA L40S",
        "NVIDIA L40",
        "NVIDIA RTX 5000 Ada Generation",
        "NVIDIA RTX 4000 Ada Generation",
        "NVIDIA RTX 6000 Ada Generation",
        "NVIDIA RTX 2000 Ada Generation",
        "NVIDIA RTX 4000 SFF Ada Generation",
    ],
    "costly": [
        "NVIDIA H100 80GB HBM3",
        "NVIDIA H200",
        "NVIDIA H200 NVL",
        "NVIDIA H100 PCIe",
        "NVIDIA H100 NVL",
        "NVIDIA A100-SXM4-80GB",
        "NVIDIA A100 80GB PCIe",
        "NVIDIA B200",
        "AMD Instinct MI300X OAM",
        "NVIDIA RTX PRO 6000 Blackwell Server Edition",
        "NVIDIA RTX PRO 6000 Blackwell Workstation Edition",
        "NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition",
    ],
}


class RayRun(anywidget.AnyWidget):
    """Jupyter widget for managing RunPod Ray compute."""

    # Traitlets for state management
    status = traitlets.Unicode("fetching").tag(sync=True)
    pod_id = traitlets.Unicode("").tag(sync=True)
    ip_address = traitlets.Unicode("").tag(sync=True)
    ray_url = traitlets.Unicode("").tag(sync=True)
    dashboard_url = traitlets.Unicode("").tag(sync=True)
    started_at = traitlets.Float(0).tag(sync=True)
    elapsed_seconds = traitlets.Float(0).tag(sync=True)
    error_message = traitlets.Unicode("").tag(sync=True)
    current_operation = traitlets.Unicode("").tag(sync=True)
    selected_tier = traitlets.Unicode("cheap").tag(sync=True)
    idle_timeout_minutes = traitlets.Int(30).tag(sync=True)

    # Static configuration (not synced to frontend)
    _esm = os.path.join(STATIC_DIR, "widget.js")
    _css = os.path.join(STATIC_DIR, "widget.css")

    def __init__(
        self,
        tier: str = "cheap",
        idle_timeout_minutes: int = 30,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the RayRun widget.

        Args:
            tier: GPU tier ("cheap", "medium", "costly") or "cpu" for CPU-only
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

        # Parse tier
        if tier == "cpu":
            self._is_gpu = False
            self._cpu_flavor = "4c"  # Default CPU flavor
        elif tier in GPU_TIERS:
            self.selected_tier = tier
            self._is_gpu = True
        else:
            # Default to cheap tier
            self.selected_tier = "cheap"
            self._is_gpu = True

        self.idle_timeout_minutes = idle_timeout_minutes

        # Start elapsed time update loop
        self._start_elapsed_timer()

        # Listen for messages from frontend
        self.on_msg(self._handle_frontend_message)

        # Check for existing rayrun pods on init
        asyncio.create_task(self._check_existing_rayrun_pods())

    async def _check_existing_rayrun_pods(self):
        """Check for existing rayrun pods and connect if running."""
        try:
            all_pods = await self._client.list_pods()

            # Find pods with rayrun image
            rayrun_pods = [
                pod
                for pod in all_pods
                if pod.get("imageName") == "ghcr.io/rambip/rayrun:latest"
            ]

            if rayrun_pods:
                # Check if any is already running
                running_pod = next(
                    (
                        pod
                        for pod in rayrun_pods
                        if pod.get("desiredStatus") == "RUNNING"
                    ),
                    None,
                )

                if running_pod:
                    # Connect to existing running pod
                    self.pod_id = running_pod.get("id", "")
                    self.ip_address = running_pod.get("publicIp", "")
                    self.ray_url = f"ray://{self.ip_address}:10001"
                    self.dashboard_url = f"http://{self.ip_address}:8265"
                    self.started_at = time.time()
                    self.status = "running"
                    self.current_operation = "Connected to existing session"
                    logger.info(f"Connected to existing pod: {self.pod_id}")
                    return

                # Found stopped pods - set status to stopped so user can start them
                self.status = "stopped"
                self.current_operation = (
                    f"Found {len(rayrun_pods)} existing pod(s) - click Start to resume"
                )
                return

            # No existing pods found
            self.status = "stopped"

        except Exception as e:
            logger.warning(f"Failed to check existing pods: {e}")
            self.status = "stopped"

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
        """Handle messages from the frontend (synchronous wrapper)."""
        action = content.get("action")

        if action == "start":
            self.status = "starting"
            self.current_operation = "Starting pod..."
            self.error_message = ""
            asyncio.create_task(self._start_pod())
        elif action == "stop":
            self.current_operation = "Stopping pod..."
            self.error_message = ""
            asyncio.create_task(self._stop_pod())
        elif action == "get_status":
            self.current_operation = "Checking status..."
            asyncio.create_task(self._update_status())

    # GPU tiers organized by cost - list of exact RunPod GPU identifiers

    def _get_gpu_display_name(self, pod: dict) -> Optional[str]:
        """Extract GPU display name from pod data."""
        gpu = pod.get("gpu")
        if isinstance(gpu, dict):
            return gpu.get("displayName")
        return None

    def _pod_matches_tier(self, pod: dict, tier_gpu_types: list) -> bool:
        """Check if pod uses a GPU from the specified tier."""
        gpu_name = self._get_gpu_display_name(pod)
        if gpu_name and gpu_name in tier_gpu_types:
            return True
        return False

    async def _start_pod(self):
        """Start the RunPod instance asynchronously."""
        try:
            self.status = "starting"
            self.error_message = ""

            # List existing pods to check for reusable ones
            all_pods = await self._client.list_pods()
            tier_gpu_types = GPU_TIERS.get(self.selected_tier, [])

            # Find pods matching this tier
            matching_pods = [
                pod for pod in all_pods if self._pod_matches_tier(pod, tier_gpu_types)
            ]

            if matching_pods:
                # Check if any is already running
                running_pod = next(
                    (
                        pod
                        for pod in matching_pods
                        if pod.get("desiredStatus") == "RUNNING"
                    ),
                    None,
                )

                if running_pod:
                    # Reuse existing running pod
                    self.pod_id = running_pod.get("id", "")
                    self.ip_address = running_pod.get("publicIp", "")
                    self.ray_url = f"ray://{self.ip_address}:10001"
                    self.dashboard_url = f"http://{self.ip_address}:8265"
                    self.started_at = time.time()
                    self.status = "running"
                    self.current_operation = (
                        f"Connected to existing {self.selected_tier} pod"
                    )
                    logger.info(f"Reusing running pod: {self.pod_id}")
                    return

                # Check for stopped pod to start
                stopped_pod = next(
                    (
                        pod
                        for pod in matching_pods
                        if pod.get("desiredStatus") in ["STOPPED", "EXITED"]
                    ),
                    None,
                )

                if stopped_pod:
                    # Start the stopped pod
                    self.pod_id = stopped_pod.get("id", "")
                    self.current_operation = (
                        f"Starting existing {self.selected_tier} pod..."
                    )
                    await self._client.start_pod(self.pod_id)

                    # Wait for pod to be ready
                    await self._wait_for_ready(self.pod_id, timeout=300)

                    # Get final pod data
                    ready_pod = await self._client.get_pod(self.pod_id)

                    # Update connection info
                    self.ip_address = ready_pod.get("publicIp", "")
                    self.ray_url = f"ray://{self.ip_address}:10001"
                    self.dashboard_url = f"http://{self.ip_address}:8265"
                    self.started_at = time.time()
                    self.status = "running"
                    self.current_operation = (
                        f"Resumed existing {self.selected_tier} pod"
                    )
                    logger.info(f"Started existing pod: {self.pod_id}")
                    return

            # No matching pod found, create new one
            self.current_operation = f"Creating new {self.selected_tier} pod..."

            # Generate Ray authentication password
            # ray_password = self._generate_ray_password()
            ray_password = os.environ["RAY_PASSWORD"]

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
                # Get all GPU types for the selected tier
                gpu_type_ids = GPU_TIERS[self.selected_tier]
                pod_data = await self._client.create_pod(
                    name=f"rayrun-{int(time.time())}",
                    image="ghcr.io/rambip/rayrun:latest",
                    gpu_type_ids=gpu_type_ids,
                    env_vars=env_vars,
                    ports=["10001/tcp", "8265/http"],
                    cloud_type="COMMUNITY",
                    container_disk_in_gb=50,
                    volume_in_gb=20,
                )
            else:
                cpu_flavor = f"cpu{self._cpu_flavor}"
                pod_data = await self._client.create_pod(
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

            # Wait for pod to be ready (async polling)
            await self._wait_for_ready(self.pod_id, timeout=300)

            # Get final pod data
            ready_pod = await self._client.get_pod(self.pod_id)

            # Update connection info
            self.ip_address = ready_pod.get("publicIp", "")
            self.ray_url = f"ray://{self.ip_address}:10001"
            self.dashboard_url = f"http://{self.ip_address}:8265"
            self.started_at = time.time()
            self.status = "running"
            self.current_operation = f"Created new {self.selected_tier} pod"

            logger.info(f"Pod started: {self.pod_id} at {self.ip_address}")

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.current_operation = ""
            logger.error(f"Failed to start pod: {e}")

    async def _wait_for_ready(self, pod_id: str, timeout: int = 300, interval: int = 5):
        """Poll until pod is running and has an IP address.

        Args:
            pod_id: Pod ID
            timeout: Maximum time to wait in seconds
            interval: Polling interval in seconds

        Raises:
            TimeoutError: If pod doesn't become ready in time
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                pod = await self._client.get_pod(pod_id)

                # Check if pod is running and has an IP
                if pod.get("desiredStatus") == "RUNNING":
                    # Check if it has a public IP
                    public_ip = pod.get("publicIp")
                    if public_ip:
                        return

                await asyncio.sleep(interval)
            except Exception:
                # Pod might not exist yet, keep polling
                await asyncio.sleep(interval)

        raise TimeoutError(
            f"Pod {pod_id} did not become ready within {timeout} seconds"
        )

    async def _stop_pod(self):
        """Stop the RunPod instance asynchronously."""
        try:
            if not self.pod_id:
                self.status = "stopped"
                return

            self.status = "stopping"

            # Delete pod
            await self._client.stop_pod(self.pod_id)

            # Reset state
            self.pod_id = ""
            self.ip_address = ""
            self.ray_url = ""
            self.dashboard_url = ""
            self.started_at = 0
            self.elapsed_seconds = 0
            self.status = "stopped"
            self.current_operation = ""

            logger.info("Pod stopped successfully")

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            self.current_operation = ""
            logger.error(f"Failed to stop pod: {e}")

    async def _update_status(self):
        """Update widget status from RunPod API asynchronously."""
        try:
            if not self.pod_id:
                self.status = "stopped"
                return

            pod_data = await self._client.get_pod(self.pod_id)
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

            self.current_operation = ""

        except Exception as e:
            self.current_operation = ""
            logger.warning(f"Failed to update status: {e}")
            # Pod might have been deleted
            self.status = "stopped"
            self.pod_id = ""

    @property
    def address(self) -> str:
        """Get the Ray client address.

        Returns:
            Ray address URL (ray://ip:port)
        """
        if not self.ray_url:
            raise RuntimeError("Pod is not running. Start the VM first.")
        return self.ray_url
