import pytest
import time
from dronekit import VehicleMode
from pymavlink import mavutil

FENCE_RADIUS = 50       # meters
FENCE_ACTION = 2        # 2 = Land
FLY_DISTANCE = 100      # meters north — will breach the 50m fence


def set_geofence(vehicle, radius=FENCE_RADIUS, action=FENCE_ACTION):
    """Enable a circular geofence around home."""
    master = vehicle._master
    for param, value in [
        ('FENCE_ENABLE', 1),
        ('FENCE_TYPE',   2),       # 2 = circle
        ('FENCE_RADIUS', radius),
        ('FENCE_ACTION', action),
        ('FENCE_MARGIN', 2),       # 2m margin before action triggers
    ]:
        master.mav.param_set_send(
            master.target_system,
            master.target_component,
            param.encode(),
            float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        time.sleep(0.2)
    print(f"[fence] Geofence enabled: {radius}m radius, action={action}")


def disable_geofence(vehicle):
    """Disable geofence after test."""
    master = vehicle._master
    master.mav.param_set_send(
        master.target_system,
        master.target_component,
        b'FENCE_ENABLE',
        0.0,
        mavutil.mavlink.MAV_PARAM_TYPE_REAL32
    )
    time.sleep(0.2)
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


def fly_north(vehicle, distance_m=FLY_DISTANCE):
    """Fly north by sending a velocity command."""
    from pymavlink import mavutil
    master = vehicle._master

    # Convert distance to approx degrees latitude
    # 1 degree lat ≈ 111,111m
    target_lat = vehicle.location.global_relative_frame.lat + (distance_m / 111111)
    target_lon = vehicle.location.global_relative_frame.lon
    target_alt = vehicle.location.global_relative_frame.alt
    print(target_lat, target_lon, target_alt)

    print(f"[fence] Flying north toward ({target_lat:.6f}, {target_lon:.6f})")
    vehicle.simple_goto(
        vehicle.location.global_relative_frame.__class__(
            target_lat, target_lon, target_alt
        )
    )


class TestGeofence:

    @pytest.mark.timeout(120)
    def test_geofence_triggers_land(self, vehicle_reset):
        """
        Set a 50m circular fence, fly past it, assert drone lands.
        """
        set_geofence(vehicle_reset, radius=FENCE_RADIUS, action=FENCE_ACTION)
        arm_and_takeoff(vehicle_reset, target_alt=20)
        vehicle_reset.mode = VehicleMode("AUTO")
        # Fly north — will breach the 50m fence
        fly_north(vehicle_reset, distance_m=FLY_DISTANCE)

        # Wait for fence breach and landing
        deadline = time.time() + 90
        landed = False
        while time.time() < deadline:
            alt = vehicle_reset.location.global_relative_frame.alt
            mode = vehicle_reset.mode.name
            print(f"[fence] alt={alt:.1f}m mode={mode}")

            if mode == "LAND" or (alt < 1.0 and not vehicle_reset.armed):
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

        master = vehicle_reset._master

        # Request and verify each param
        for param, expected in [
            ('FENCE_ENABLE', 1),
            ('FENCE_RADIUS', FENCE_RADIUS),
            ('FENCE_ACTION', FENCE_ACTION),
        ]:
            master.mav.param_request_read_send(
                master.target_system,
                master.target_component,
                param.encode(),
                -1
            )
            msg = master.recv_match(
                type='PARAM_VALUE',
                blocking=True,
                timeout=5
            )
            if msg:
                print(f"[fence] {param}={msg.param_value} (expected {expected})")
                assert msg.param_value == float(expected), \
                    f"{param}: expected {expected}, got {msg.param_value}"

        disable_geofence(vehicle_reset)

    @pytest.mark.timeout(60)
    def test_geofence_disabled_by_default(self, vehicle_reset):
        """
        DEMO FAILING TEST — asserts fence is enabled by default,
        but it's actually disabled. Shows what a failure looks like.
        """
        master = vehicle_reset._master
        master.mav.param_request_read_send(
            master.target_system,
            master.target_component,
            b'FENCE_ENABLE',
            -1
        )
        msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=5)
        assert msg is not None, "No response for FENCE_ENABLE param"
        assert msg.param_value == 1.0, (
            f"Expected FENCE_ENABLE=1 (enabled by default), "
            f"got {msg.param_value}. Geofence is not enabled!"
        )