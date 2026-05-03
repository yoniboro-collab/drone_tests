import pytest
import time
from dronekit import VehicleMode


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
    print(f"[mode] Reached {target_alt}m")


def switch_mode_and_verify(vehicle, mode_name, timeout=15):
    """Switch mode and wait until confirmed."""
    vehicle.mode = VehicleMode(mode_name)
    deadline = time.time() + timeout
    while vehicle.mode.name != mode_name:
        if time.time() > deadline:
            raise TimeoutError(
                f"Mode never switched to {mode_name}, stuck at {vehicle.mode.name}"
            )
        time.sleep(0.5)
    print(f"[mode] Confirmed mode: {mode_name}")


class TestModeSwitching:

    @pytest.mark.timeout(120)
    def test_guided_to_loiter(self, vehicle_reset):
        """Switch from GUIDED to LOITER during flight."""
        arm_and_takeoff(vehicle_reset)
        switch_mode_and_verify(vehicle_reset, "LOITER")
        assert vehicle_reset.mode.name == "LOITER"

    @pytest.mark.timeout(120)
    def test_loiter_back_to_guided(self, vehicle_reset):
        """Switch from LOITER back to GUIDED during flight."""
        arm_and_takeoff(vehicle_reset)
        switch_mode_and_verify(vehicle_reset, "LOITER")
        switch_mode_and_verify(vehicle_reset, "GUIDED")
        assert vehicle_reset.mode.name == "GUIDED"

    @pytest.mark.timeout(180)
    def test_guided_loiter_guided_rtl(self, vehicle_reset):
        """Full sequence: GUIDED → LOITER → GUIDED → RTL."""
        arm_and_takeoff(vehicle_reset)

        switch_mode_and_verify(vehicle_reset, "LOITER")
        time.sleep(3)  # hover in LOITER briefly

        switch_mode_and_verify(vehicle_reset, "GUIDED")
        time.sleep(3)  # hover in GUIDED briefly

        switch_mode_and_verify(vehicle_reset, "RTL")

        # Wait for drone to land
        deadline = time.time() + 120
        while vehicle_reset.location.global_relative_frame.alt > 1.0:
            if time.time() > deadline:
                raise TimeoutError("Drone never landed after RTL")
            time.sleep(1)
        print("[mode] Drone landed after RTL ✅")

    @pytest.mark.timeout(60)
    def test_mode_is_guided_at_cruise_altitude(self, vehicle_reset):
        """
        DEMO FAILING TEST — asserts drone is in AUTO after takeoff,
        but it's actually in GUIDED. Shows what a failure looks like.
        """
        arm_and_takeoff(vehicle_reset, target_alt=10)
        mode = vehicle_reset.mode.name
        assert mode == "AUTO", (
            f"Expected AUTO at cruise altitude, got {mode}. "
            f"Did you forget to start the mission?"
        )