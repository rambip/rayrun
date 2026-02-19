#!/bin/bash
set -e

echo "========================================"
echo "RayRun Container Starting"
echo "========================================"

# Generate a random password for Ray authentication if not provided
if [ -z "$RAY_PASSWORD" ]; then
    RAY_PASSWORD=$(openssl rand -base64 32)
    echo "Generated Ray password: $RAY_PASSWORD"
fi

export RAY_PASSWORD

# Start Ray head node
echo "Starting Ray head node..."
ray start --head \
    --port=6379 \
    --dashboard-host=0.0.0.0 \
    --dashboard-port=8265 \
    --ray-client-server-port=10001

# Wait for Ray to be ready
echo "Waiting for Ray to be ready..."
sleep 5

# Check if Ray is running
if ! ray status > /dev/null 2>&1; then
    echo "ERROR: Ray failed to start"
    exit 1
fi

echo "Ray is running!"
echo "Dashboard: http://<pod-ip>:8265"
echo "Client: ray://<pod-ip>:10001"

# Start shutdown monitor in background
echo "Starting shutdown monitor..."
export RAY_DASHBOARD_URL="http://localhost:8265"
python /app/shutdown_monitor.py &
SHUTDOWN_PID=$!

# Keep container running
echo "Container is now running. Press Ctrl+C to stop."
trap "echo 'Stopping...'; kill $SHUTDOWN_PID 2>/dev/null; ray stop; exit 0" SIGTERM SIGINT
wait $SHUTDOWN_PID
