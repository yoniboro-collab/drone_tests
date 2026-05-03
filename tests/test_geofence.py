import pytest
import time
from dronekit import VehicleMode, LocationGlobalRelative
from pymavlink import mavutil

FENCE_RADIUS = 50
FENCE_ACTION = 2        # 2 = Land
FLY_DISTANCE = 100      # meters north — will breach the 50m fence


def set_geofence(vehicle, radius=FENCE_RADIUS, action=FENCE_ACTION):
    """Enable a circular geofence around home."""
    vehicle.parameters['FENCE_ENABLE'] = 1
    time.sleep(0.3)
    vehicle.parameters['FENCE_TYPE'] = 2
    time.sleep(0.3)
    vehicle.parameters['FENCE_RADIUS'] = float(radius)
    time.sleep(0.3)
    vehicle.parameters['FENCE_ACTION'] = action
    time.sleep(0.3)
    vehicle.parameters['FENCE_MARGIN'] = 2
    time.sleep(0.3)
    print(f"[fence] Geofence enabled: {radius}m radius, action={action}")


def disable_geofence(vehicle):
    """Disable geofence after test."""
    vehicle.parameters['FENCE_ENABLE'] = 0
    time.sleep(0.3)
    print("[fence] Geofence disabled")


def arm_and_takeoff(vehicle, target_alt=20, timeout=90):
    vehicle.mode = VehicleMode("GUIDED")
    deadline = time.time() + timeout
    while not vehicle.is_armable:
        if time.time() > deadline:
            raise TimeoutError("Vehicle never became armable")
        time.sleep(1)
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(1)
    vehicle.simple_takeoff(target_alt)
    while vehicle.location.global_relative_frame.alt < target_alt * 0.90:
        if time.time() > deadline:
            raise TimeoutError("Never reached target altitude")
        time.sleep(0.5)
    print(f"[fence] Reached {target_alt}m")


def fly_north_velocity(vehicle, speed=3):
    """
    Push drone north using continuous velocity commands.
    Unlike simple_goto, velocity commands cannot be rejected
    by the fence — the fence triggers mid-flight instead.
    """
    master = vehicle._master
    print(f"[fence] Pushing north at {speed}m/s...")
    deadline = time.time() + 60  # max 60 seconds of pushing
    while time.time() < deadline:
        master.mav.set_position_target_local_ned_send(
            0,
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            0b0000111111000111,  # velocity only
            0, 0, 0,             # position (ignored)
            speed, 0, 0,         # vx=north, vy=0, vz=0
            0, 0, 0,             # acceleration (ignored)
            0, 0                 # yaw (ignored)
        )
        time.sleep(0.2)
        mode = vehicle.mode.name
        if mode != "GUIDED":
            print(f"[fence] Mode changed to {mode} — fence triggered!")
            break


class TestGeofence:

    @pytest.mark.timeout(180)
    def test_geofence_triggers_land(self, vehicle_reset):
        """
        Arm and takeoff, enable 50m fence, push north via
        velocity commands past fence boundary, assert drone lands.
        """
        # Arm and takeoff FIRST
        arm_and_takeoff(vehicle_reset, target_alt=20)

        # Enable fence AFTER arming
        set_geofence(vehicle_reset, radius=FENCE_RADIUS, action=FENCE_ACTION)
        time.sleep(2)

        # Push north with velocity commands — fence triggers mid-flight
        fly_north_velocity(vehicle_reset, speed=3)

        # Wait for fence breach and landing
        deadline = time.time() + 60
        landed = False
        breach_detected = False
        while time.time() < deadline:
            alt = vehicle_reset.location.global_relative_frame.alt
            mode = vehicle_reset.mode.name
            pos = vehicle_reset.location.global_relative_frame
            print(f"[fence] alt={alt:.1f}m mode={mode} lat={pos.lat:.6f}")

            if mode == "LAND":
                breach_detected = True
                print("[fence] LAND mode triggered — fence breached! ✅")

            if breach_detected and (alt < 1.0 or not vehicle_reset.armed):
                landed = True
                print("[fence] Drone landed after fence breach ✅")
                break
            time.sleep(1)

        disable_geofence(vehicle_reset)
        assert landed, "Drone did not land after breaching geofence"

    @pytest.mark.timeout(60)
    def test_geofence_enabled_params(self, vehicle_reset):
        """Verify geofence parameters are set correctly."""
        set_geofence(vehicle_reset, radius=FENCE_RADIUS, action=FENCE_ACTION)
        time.sleep(1)

        assert vehicle_reset.parameters['FENCE_ENABLE'] == 1, \
            f"FENCE_ENABLE: expected 1, got {vehicle_reset.parameters['FENCE_ENABLE']}"
        assert vehicle_reset.parameters['FENCE_RADIUS'] == float(FENCE_RADIUS), \
            f"FENCE_RADIUS: expected {FENCE_RADIUS}, got {vehicle_reset.parameters['FENCE_RADIUS']}"
        assert vehicle_reset.parameters['FENCE_ACTION'] == FENCE_ACTION, \
            f"FENCE_ACTION: expected {FENCE_ACTION}, got {vehicle_reset.parameters['FENCE_ACTION']}"

        print("[fence] All geofence params verified ✅")
        disable_geofence(vehicle_reset)

    @pytest.mark.timeout(30)
    def test_geofence_disabled_by_default(self, vehicle_reset):
        """
        DEMO FAILING TEST — asserts fence is enabled by default,
        but it's actually disabled. Shows what a failure looks like.
        """
        fence_enabled = vehicle_reset.parameters['FENCE_ENABLE']
        assert fence_enabled == 1.0, (
            f"Expected FENCE_ENABLE=1 (enabled by default), "
            f"got {fence_enabled}. Geofence is not enabled!"
        )