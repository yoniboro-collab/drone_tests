import pytest
import time
from dronekit import VehicleMode

TAKEOFF_ALT = 10  # metres — change this to test different altitudes


# ─── Helper ───────────────────────────────────────────────────────────────────

def arm_and_takeoff(vehicle, target_alt):
    """
    Switch to GUIDED mode, arm, and climb to target_alt.
    Blocks until altitude is reached (or pytest-timeout kills it).
    """

    # Step 1: GUIDED is required before arming in ArduPilot.
    # In any other mode (STABILIZE, LOITER, etc.) arming via MAVLink is rejected.
    vehicle.mode = VehicleMode("GUIDED")

    # Step 2: Wait until pre-arm checks pass.
    # is_armable = True once EKF is healthy + GPS lock (SITL gives this quickly).
    while not vehicle.is_armable:
        time.sleep(1)

    # Step 3: Arm. Setting .armed = True sends a MAVLink ARM command.
    vehicle.armed = True

    # Step 4: Confirm arm. The FC echoes back the arm state — don't skip this wait
    # or the next command may be sent before arming completes.
    while not vehicle.armed:
        time.sleep(1)

    # Step 5: Climb. simple_takeoff() sends a MAV_CMD_NAV_TAKEOFF command.
    vehicle.simple_takeoff(target_alt)

    # Step 6: Poll altitude. global_relative_frame.alt is AGL (above ground level).
    # We accept 95% of target to account for minor SITL oscillation.
    while True:
        alt = vehicle.location.global_relative_frame.alt
        if alt >= target_alt * 0.95:
            break
        time.sleep(0.5)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestArmTakeoff:

    @pytest.mark.timeout(180)
    def test_vehicle_connects(self, vehicle):
        """
        Smoke test: did we get a vehicle object back from conftest?
        Runs before anything that needs a healthy connection.
        """
        assert vehicle is not None

    @pytest.mark.timeout(120)   # arm + climb can be slow on first SITL boot
    def test_arm_and_reach_altitude(self, vehicle):
        """
        Full arm-and-takeoff sequence. Fails if altitude isn't reached
        within the timeout (120s is generous for SITL, tighten for CI).
        """
        arm_and_takeoff(vehicle, TAKEOFF_ALT)

        alt = vehicle.location.global_relative_frame.alt
        assert alt >= TAKEOFF_ALT * 0.95, \
            f"Expected ~{TAKEOFF_ALT}m, got {alt:.1f}m"

    @pytest.mark.timeout(30)
    def test_mode_is_guided_after_takeoff(self, vehicle):
        """
        Sanity check: mode must still be GUIDED after takeoff.
        If something reset it (RC override, fence breach, etc.) this catches it.
        """
        assert vehicle.mode.name == "GUIDED"