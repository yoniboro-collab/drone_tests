#!/bin/bash
echo "[SITL] Killing existing processes..."
pkill -f arducopter 2>/dev/null || true
pkill -f sim_vehicle 2>/dev/null || true
pkill -f mavproxy 2>/dev/null || true

# Wait until all old processes are fully dead
sleep 5

echo "[SITL] Starting SITL..."
cd /mnt/c/ardu/ardupilot
nohup python3 Tools/autotest/sim_vehicle.py -v ArduCopter --no-rebuild --no-rc --no-mavproxy -w --add-param-file=/mnt/c/drone_tests/sitl_params.parm > /tmp/sitl.log 2>&1 &

echo "[SITL] Waiting for port 5760..."
DEADLINE=$(($(date +%s) + 60))
while ! nc -z 127.0.0.1 5760 2>/dev/null; do
  [ $(date +%s) -gt $DEADLINE ] && echo "SITL timeout!" && exit 1
  sleep 2
done
echo "[SITL] SITL ready!"

echo "[SITL] Starting MAVProxy..."
nohup mavproxy.py --master=tcp:127.0.0.1:5760 \
  --out=udp:127.0.0.1:14550 \
  --out=udp:127.0.0.1:14551 \
  --non-interactive > /tmp/mavproxy.log 2>&1 &

echo "[SITL] Waiting 45s for MAVProxy to initialize..."
sleep 45
echo "[SITL] All systems ready!"
