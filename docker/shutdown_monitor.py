"""Monitor Ray activity and shutdown pod when idle."""

import logging
import os
import time
from datetime import datetime, timezone

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("shutdown_monitor")

# Configuration
IDLE_TIMEOUT_MINUTES = int(os.getenv("IDLE_TIMEOUT_MINUTES", 30))
MAX_RUNTIME_HOURS = int(os.getenv("MAX_RUNTIME_HOURS", 6))
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
POD_ID = os.getenv("RUNPOD_POD_ID")
RAY_DASHBOARD_URL = os.getenv("RAY_DASHBOARD_URL", "http://0.0.0.0:8265")
CHECK_INTERVAL_SECONDS = 60  # Check every minute


def check_ray_activity():
    """Check if Ray has any active jobs or recent activity.

    Returns:
        tuple: (is_active, message) where is_active is True if there are active jobs
    """
    try:
        # Try to get jobs from Ray dashboard
        resp = requests.get(f"{RAY_DASHBOARD_URL}/api/jobs", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get("jobs", [])

            if not jobs:
                return False, "No jobs found"

            # Check for running or pending jobs
            for job in jobs:
                status = job.get("status")
                if status in ["RUNNING", "PENDING"]:
                    return True, f"Active job: {job.get('job_id')} ({status})"

            # Check for recently finished jobs
            now = time.time()
            idle_timeout_seconds = IDLE_TIMEOUT_MINUTES * 60

            for job in jobs:
                status = job.get("status")
                end_time = job.get("end_time")
                if status in ["SUCCEEDED", "FAILED"] and end_time:
                    # end_time might be in milliseconds or seconds
                    if end_time > 1e12:  # milliseconds
                        end_time = end_time / 1000

                    time_since_end = now - end_time
                    if time_since_end < idle_timeout_seconds:
                        return (
                            True,
                            f"Recent job finished {time_since_end / 60:.1f}m ago",
                        )

            return False, "No active or recent jobs"
        else:
            logger.warning(f"Ray dashboard returned status {resp.status_code}")
            return None, f"Ray dashboard unavailable: {resp.status_code}"
    except requests.exceptions.ConnectionError:
        logger.warning("Cannot connect to Ray dashboard")
        return None, "Ray dashboard not ready"
    except Exception as e:
        logger.error(f"Error checking Ray activity: {e}")
        return None, f"Error: {e}"


def shutdown_pod():
    """Shutdown the pod via RunPod API."""
    if not RUNPOD_API_KEY or not POD_ID:
        logger.error("Missing RUNPOD_API_KEY or POD_ID environment variables")
        return False

    try:
        logger.info(f"Shutting down pod {POD_ID} via RunPod API")
        resp = requests.delete(
            f"https://rest.runpod.io/v1/pods/{POD_ID}",
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            timeout=30,
        )

        if resp.status_code == 204:
            logger.info("Pod shutdown successful")
            return True
        else:
            logger.error(f"Failed to shutdown pod: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error shutting down pod: {e}")
        return False


def main():
    """Main monitoring loop."""
    logger.info("=" * 60)
    logger.info("RayRun Shutdown Monitor Started")
    logger.info("=" * 60)
    logger.info(f"Pod ID: {POD_ID}")
    logger.info(f"Idle timeout: {IDLE_TIMEOUT_MINUTES} minutes")
    logger.info(f"Max runtime: {MAX_RUNTIME_HOURS} hours")
    logger.info(f"Check interval: {CHECK_INTERVAL_SECONDS} seconds")
    logger.info("=" * 60)

    if not RUNPOD_API_KEY or not POD_ID:
        logger.error("Missing required environment variables. Exiting.")
        return 1

    start_time = time.time()
    last_activity_time = start_time
    max_runtime_seconds = MAX_RUNTIME_HOURS * 3600

    # Wait a bit for Ray to fully start
    logger.info("Waiting 30 seconds for Ray to initialize...")
    time.sleep(30)

    logger.info("Starting monitoring loop...")

    while True:
        try:
            current_time = time.time()
            runtime_seconds = current_time - start_time

            # Check max runtime
            if runtime_seconds >= max_runtime_seconds:
                logger.info(
                    f"Maximum runtime of {MAX_RUNTIME_HOURS} hours reached. Shutting down..."
                )
                shutdown_pod()
                break

            # Check Ray activity
            is_active, message = check_ray_activity()

            if is_active is True:
                logger.info(f"Activity detected: {message}")
                last_activity_time = current_time
            elif is_active is False:
                idle_seconds = current_time - last_activity_time
                idle_minutes = idle_seconds / 60

                logger.info(
                    f"No activity: {message} (idle for {idle_minutes:.1f} minutes)"
                )

                if idle_seconds >= (IDLE_TIMEOUT_MINUTES * 60):
                    logger.info(
                        f"Idle timeout of {IDLE_TIMEOUT_MINUTES} minutes reached. Shutting down..."
                    )
                    shutdown_pod()
                    break
            else:
                # is_active is None - dashboard not ready or error
                logger.warning(f"Cannot determine activity: {message}")

                # If dashboard has been unavailable for too long, shutdown anyway
                idle_seconds = current_time - last_activity_time
                if idle_seconds >= (
                    IDLE_TIMEOUT_MINUTES * 60 * 2
                ):  # Double the timeout
                    logger.warning(
                        "Dashboard unavailable for too long. Shutting down..."
                    )
                    shutdown_pod()
                    break

            # Sleep until next check
            time.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("Shutdown monitor interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in monitoring loop: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)

    logger.info("Shutdown monitor exiting")
    return 0


if __name__ == "__main__":
    exit(main())
