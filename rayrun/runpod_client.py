"""Async RunPod API client for RayRun using aiohttp."""

import asyncio
from typing import Optional

import aiohttp

BASE_URL = "https://rest.runpod.io/v1"


class RunPodClient:
    """Async client for RunPod API."""

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

    async def create_pod(
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

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(
                f"{self.base_url}/pods",
                json=payload,
            ) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed to create pod: {response.status} - {text}"
                    )

    async def get_pod(self, pod_id: str) -> dict:
        """Get pod status.

        Args:
            pod_id: Pod ID

        Returns:
            Pod data with id, publicIp, desiredStatus, etc.

        Raises:
            RuntimeError: If request fails
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"{self.base_url}/pods/{pod_id}") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise RuntimeError(f"Failed to get pod: {response.status} - {text}")

    async def delete_pod(self, pod_id: str) -> bool:
        """Delete a pod.

        Args:
            pod_id: Pod ID

        Returns:
            True if successful

        Raises:
            RuntimeError: If deletion fails
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.delete(f"{self.base_url}/pods/{pod_id}") as response:
                if response.status == 204:
                    return True
                else:
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed to delete pod: {response.status} - {text}"
                    )

    async def list_pods(self) -> list:
        """List all pods.

        Returns:
            List of pod data

        Raises:
            RuntimeError: If request fails
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(f"{self.base_url}/pods") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed to list pods: {response.status} - {text}"
                    )

    async def start_pod(self, pod_id: str) -> dict:
        """Start a stopped pod.

        Args:
            pod_id: Pod ID

        Returns:
            Pod data with updated status

        Raises:
            RuntimeError: If start fails
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(f"{self.base_url}/pods/{pod_id}/start") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed to start pod: {response.status} - {text}"
                    )

    async def stop_pod(self, pod_id: str) -> dict:
        """Stop a started pod

        Args:
            pod_id: Pod ID

        Returns:
            Pod data with updated status

        Raises:
            RuntimeError: If stop fails
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.post(f"{self.base_url}/pods/{pod_id}/stop") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise RuntimeError(
                        f"Failed to stop pod: {response.status} - {text}"
                    )
