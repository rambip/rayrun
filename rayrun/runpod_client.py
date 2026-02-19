"""RunPod API client for RayRun."""

import os
import time
import requests
from typing import Optional

BASE_URL = "https://rest.runpod.io/v1"

GPU_TYPES = {
    "gpu.a100": "NVIDIA A100 80GB PCIe",
    "gpu.a100-80gb-sxm": "NVIDIA A100 80GB SXM",
    "gpu.a100-40gb": "NVIDIA A100 40GB PCIe",
    "gpu.a6000": "NVIDIA RTX A6000",
    "gpu.v100": "NVIDIA V100",
    "gpu.h100": "NVIDIA H100 80GB SXM",
    "gpu.h100-pcie": "NVIDIA H100 80GB PCIe",
    "gpu.rtx4090": "NVIDIA RTX 4090",
    "gpu.rtx3090": "NVIDIA RTX 3090",
    "gpu.l40s": "NVIDIA L40S",
}

CPU_FLAVORS = {
    "cpu1c": "1 vCPU, 2GB RAM",
    "cpu2c": "2 vCPU, 4GB RAM",
    "cpu3c": "2 vCPU, 6GB RAM",
    "cpu4c": "4 vCPU, 8GB RAM",
    "cpu6c": "6 vCPU, 12GB RAM",
    "cpu8c": "8 vCPU, 16GB RAM",
    "cpu12c": "12 vCPU, 24GB RAM",
    "cpu16c": "16 vCPU, 32GB RAM",
    "cpu24c": "24 vCPU, 48GB RAM",
}


class RunPodClient:
    """Client for RunPod API."""

    def __init__(self, api_key: str):
        """Initialize the client.

        Args:
            api_key: RunPod API key
        """
        self.api_key = api_key
        self.base_url = BASE_URL
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def create_pod(
        self,
        name: str,
        image: str,
        gpu_type_ids: Optional[list] = None,
        cpu_flavor_ids: Optional[list] = None,
        env_vars: Optional[dict] = None,
        ports: Optional[list] = None,
        cloud_type: str = "COMMUNITY",
        container_disk_in_gb: int = 20,
        volume_in_gb: int = 20,
        volume_mount_path: str = "/workspace",
    ) -> dict:
        """Create a new pod.

        Args:
            name: Name for the pod
            image: Docker image name
            gpu_type_ids: List of GPU types to request
            cpu_flavor_ids: List of CPU flavors to request
            env_vars: Environment variables dict
            ports: List of port mappings like ["10001/tcp", "8265/http"]
            cloud_type: "COMMUNITY" or "SECURE"
            container_disk_in_gb: Container disk size in GB
            volume_in_gb: Volume size in GB
            volume_mount_path: Path to mount volume

        Returns:
            Pod data with id, publicIp, desiredStatus

        Raises:
            RuntimeError: If creation fails
        """
        payload = {
            "name": name,
            "imageName": image,
            "cloudType": cloud_type,
            "containerDiskInGb": container_disk_in_gb,
            "volumeInGb": volume_in_gb,
            "volumeMountPath": volume_mount_path,
        }

        if gpu_type_ids:
            payload["computeType"] = "GPU"
            payload["gpuTypeIds"] = gpu_type_ids
        elif cpu_flavor_ids:
            payload["computeType"] = "CPU"
            payload["cpuFlavorIds"] = cpu_flavor_ids
        else:
            raise ValueError("Must specify either gpu_type_ids or cpu_flavor_ids")

        if env_vars:
            payload["env"] = env_vars

        if ports:
            payload["ports"] = ports

        response = requests.post(
            f"{self.base_url}/pods",
            headers=self.headers,
            json=payload,
        )

        if response.status_code == 201:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to create pod: {response.status_code} - {response.text}"
            )

    def get_pod(self, pod_id: str) -> dict:
        """Get pod status.

        Args:
            pod_id: Pod ID

        Returns:
            Pod data with id, publicIp, desiredStatus, etc.

        Raises:
            RuntimeError: If request fails
        """
        response = requests.get(
            f"{self.base_url}/pods/{pod_id}",
            headers=self.headers,
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to get pod: {response.status_code} - {response.text}"
            )

    def delete_pod(self, pod_id: str) -> bool:
        """Delete a pod.

        Args:
            pod_id: Pod ID

        Returns:
            True if successful

        Raises:
            RuntimeError: If deletion fails
        """
        response = requests.delete(
            f"{self.base_url}/pods/{pod_id}",
            headers=self.headers,
        )

        if response.status_code == 204:
            return True
        else:
            raise RuntimeError(
                f"Failed to delete pod: {response.status_code} - {response.text}"
            )

    def wait_for_ready(
        self, pod_id: str, timeout: int = 300, interval: int = 5
    ) -> dict:
        """Poll until pod is running and has an IP address.

        Args:
            pod_id: Pod ID
            timeout: Maximum time to wait in seconds
            interval: Polling interval in seconds

        Returns:
            Pod data when ready

        Raises:
            TimeoutError: If pod doesn't become ready in time
            RuntimeError: If API request fails
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                pod = self.get_pod(pod_id)

                # Check if pod is running and has an IP
                if pod.get("desiredStatus") == "RUNNING":
                    # Check if it has a public IP
                    public_ip = pod.get("publicIp")
                    if public_ip:
                        return pod

                time.sleep(interval)
            except Exception:
                # Pod might not exist yet, keep polling
                time.sleep(interval)

        raise TimeoutError(
            f"Pod {pod_id} did not become ready within {timeout} seconds"
        )

    def list_pods(self) -> list:
        """List all pods.

        Returns:
            List of pod data

        Raises:
            RuntimeError: If request fails
        """
        response = requests.get(
            f"{self.base_url}/pods",
            headers=self.headers,
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to list pods: {response.status_code} - {response.text}"
            )
