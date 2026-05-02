#!/bin/bash

echo "[docker-sitl] Starting ArduPilot SITL container..."

# Go to project root (where docker-compose.yml lives)
cd /mnt/c/drone_tests

# Pull latest image if needed
docker compose pull

# Start container in background
docker compose up -d

# Wait for SITL to be ready on port 5760
echo "[docker-sitl] Waiting for SITL to be ready on port 5760..."
for i in $(seq 1 30); do
    if nc -z localhost 5760 2>/dev/null; then
        echo "[docker-sitl] SITL is ready! (took ${i}s)"
        exit 0
    fi
    echo "[docker-sitl] Waiting... ${i}/30"
    sleep 1
done

echo "[docker-sitl] ERROR: SITL did not start within 30 seconds"
docker compose logs
exit 1