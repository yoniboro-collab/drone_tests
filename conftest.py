import pytest
import time
from dronekit import connect, VehicleMode
from pymavlink import mavutil
from telemetry_logger import TelemetryLogger
import os

SITL_MODE = os.environ.get("SITL_MODE", "local")

if SITL_MODE == "docker":
    SITL_CONNECTION = "tcp:localhost:5760"
else:
    SITL_CONNECTION = "udp:127.0.0.1:14551"

CONNECTION_TIMEOUT = 120
HOME_ALT           = 0


def wait_for(condition_fn, timeout=30, interval=0.5, label="condition"):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition_fn():
            return
        time.sleep(interval)
    raise TimeoutError(f"Timed out waiting for: {label}")


def land_and_disarm(vehicle, timeout=60):
    if vehicle.armed:
        vehicle.mode = VehicleMode("LAND")
        wait_for(lambda: not vehicle.armed, timeout=timeout, label="disarm after land")


def reset_battery(vehicle):
    master = vehicle._master
    for param, value in [
        ('BATT_LOW_VOLT',  0.0),   # 0 = disable low voltage warning
        ('BATT_CRT_VOLT',  0.0),   # 0 = disable critical voltage cutoff
        ('BATT_LOW_MAH',   0),     # 0 = disable mAh warning
        ('BATT_CRT_MAH',   0),     # 0 = disable mAh cutoff
        ('BATT_FS_LOW_ACT',0),     # no action on low
        ('BATT_FS_CRT_ACT',0),     # no action on critical
    ]:
        master.mav.param_set_send(
            master.target_system,
            master.target_component,
            param.encode(),
            float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        time.sleep(0.2)
    print("[conftest] Battery failsafes disabled — battery drain won't affect tests")


def log_battery(vehicle, label=""):
    try:
        voltage = vehicle.battery.voltage
        level   = vehicle.battery.level
        print(f"[battery] {label} — {voltage:.2f}V / {level}%")
    except Exception:
        print(f"[battery] {label} — unavailable")


@pytest.fixture(scope="session")
def vehicle():
    print(f"\n[conftest] Connecting to SITL at {SITL_CONNECTION} ...")
    v = connect(
        SITL_CONNECTION,
        wait_ready=True,
        timeout=CONNECTION_TIMEOUT,
        heartbeat_timeout=60,
        source_system=255,
    )
    print(f"[conftest] Connected. Firmware: {v.version}")
    print(f"[conftest] Home: {v.home_location}")

    # ── Session-level SITL configuration ──────────────────────────────────
    master = v._master
    for param, value in [
        ('BATT_FS_LOW_ACT', 0),
        ('BATT_FS_CRT_ACT', 0),
        ('SIM_BATT_VOLTAGE', 12.59),
        ('SIM_BATT_CAP_AH', 10.0),
    ]:
        master.mav.param_set_send(
            master.target_system,
            master.target_component,
            param.encode(),
            float(value),
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        time.sleep(0.2)
    print("[conftest] Battery failsafe disabled, battery set to full")

    yield v

    print("\n[conftest] Teardown: landing and disarming...")
    try:
        land_and_disarm(v)
    except Exception as e:
        print(f"[conftest] Teardown warning: {e}")
    finally:
        v.close()
        print("[conftest] Connection closed.")

@pytest.fixture(scope="session")
def telemetry(vehicle):
    """Session-scoped telemetry logger — logs all tests to one combined CSV."""
    logger = TelemetryLogger(vehicle)
    logger.start_run()
    yield logger
    logger.stop_run()
    print("[telemetry] Run logging complete.")


@pytest.fixture(scope="function", autouse=True)
def log_telemetry(request, telemetry):
    """
    Function-scoped fixture that auto-attaches to every test.
    autouse=True means you don't need to add it to each test manually.
    """
    telemetry.start_test(request.node.nodeid)
    yield
    telemetry.stop_test()

@pytest.fixture(scope="function")
def vehicle_reset(vehicle):
    print("\n[conftest] Resetting vehicle state before test...")
    log_battery(vehicle, label="before reset")

    land_and_disarm(vehicle, timeout=60)
    wait_for(lambda: not vehicle.armed, timeout=15, label="pre-test disarm confirm")

    # Refill battery
    reset_battery(vehicle)

    # Clear leftover mission from previous test
    vehicle._master.mav.mission_clear_all_send(
        vehicle._master.target_system,
        vehicle._master.target_component
    )
    time.sleep(0.5)

    log_battery(vehicle, label="after reset")
    yield vehicle


def pytest_generate_tests(metafunc):
    if "target_alt" in metafunc.fixturenames:
        altitudes = metafunc.config.getoption("--altitudes", default=None)
        values = [int(a) for a in altitudes.split(",")] if altitudes else [5, 10, 20]
        metafunc.parametrize("target_alt", values)


def pytest_addoption(parser):
    parser.addoption(
        "--altitudes",
        action="store",
        default=None,
        help="Comma-separated takeoff altitudes e.g. 5,15,30"
    )