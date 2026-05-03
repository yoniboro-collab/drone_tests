import pytest
import time
import math
from dronekit import VehicleMode
from pymavlink import mavutil

WAYPOINTS = [
    (-35.3620, 149.1651, 20),
    (-35.3615, 149.1660, 20),
    (-35.3608, 149.1655, 20),
]
ACCEPTANCE_RADIUS = 2


def upload_mission(vehicle, waypoints):
    print("[mission] Using MISSION_ITEM_INT uploader")
    master = vehicle._master
    all_cmds = []

    home = vehicle.location.global_relative_frame
    all_cmds.append({
        "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        "command": mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        "x": int(home.lat * 1e7), "y": int(home.lon * 1e7),
        "z": float(waypoints[0][2]),
        "p1": 0, "p2": 0, "p3": 0, "p4": 0,
    })

    for lat, lon, alt in waypoints:
        all_cmds.append({
            "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
            "command": mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            "x": int(lat * 1e7), "y": int(lon * 1e7), "z": float(alt),
            "p1": 0, "p2": float(ACCEPTANCE_RADIUS), "p3": 0, "p4": 0,
        })

    all_cmds.append({
        "frame": mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        "command": mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        "x": 0, "y": 0, "z": 0,
        "p1": 0, "p2": 0, "p3": 0, "p4": 0,
    })

    master.mav.mission_count_send(master.target_system, master.target_component, len(all_cmds))
    time.sleep(0.1)

    for i, cmd in enumerate(all_cmds):
        master.mav.mission_item_int_send(
            master.target_system, master.target_component,
            i, cmd["frame"], cmd["command"],
            0, 1,
            cmd["p1"], cmd["p2"], cmd["p3"], cmd["p4"],
            cmd["x"], cmd["y"], cmd["z"],
        )
        time.sleep(0.05)

    print(f"[mission] Uploaded {len(all_cmds)} commands via MISSION_ITEM_INT")
    return len(all_cmds)


def arm_and_start_mission(vehicle, timeout=90):
    vehicle.mode = VehicleMode("GUIDED")
    deadline = time.time() + timeout
    while not vehicle.is_armable:
        if time.time() > deadline:
            raise TimeoutError("Vehicle never became armable")
        time.sleep(1)
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(1)
    target_alt = WAYPOINTS[0][2]
    vehicle.simple_takeoff(target_alt)
    while vehicle.location.global_relative_frame.alt < target_alt * 0.90:
        time.sleep(0.5)
    vehicle.mode = VehicleMode("AUTO")
    print("[mission] AUTO mode engaged")


def distance_to(vehicle, lat, lon):
    vlat = vehicle.location.global_relative_frame.lat
    vlon = vehicle.location.global_relative_frame.lon
    dlat = math.radians(lat - vlat)
    dlon = math.radians(lon - vlon)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(vlat))
         * math.cos(math.radians(lat))
         * math.sin(dlon / 2) ** 2)
    return 6371000 * 2 * math.asin(math.sqrt(a))


class TestWaypointMission:

    @pytest.mark.timeout(60)
    def test_mission_upload(self, vehicle_reset):
        expected_count = upload_mission(vehicle_reset, WAYPOINTS)

        master = vehicle_reset._master

        # Retry loop — Docker SITL is slower to confirm mission upload
        actual = 0
        for attempt in range(5):
            master.mav.mission_request_list_send(
                master.target_system,
                master.target_component
            )
            msg = master.recv_match(type="MISSION_COUNT", blocking=True, timeout=10)
            if msg and msg.count == expected_count:
                actual = msg.count
                break
            print(f"[mission] Attempt {attempt + 1}: got {msg.count if msg else 0}, retrying...")
            time.sleep(2)

        assert actual == expected_count, (
            f"Expected {expected_count} commands, got {actual}"
        )
        print(f"[mission] ArduPilot confirmed {actual} commands stored")

    @pytest.mark.timeout(300)
    def test_vehicle_visits_all_waypoints(self, vehicle_reset):
        upload_mission(vehicle_reset, WAYPOINTS)
        arm_and_start_mission(vehicle_reset)
        visited = [False] * len(WAYPOINTS)
        deadline = time.time() + 280
        while not all(visited):
            if time.time() > deadline:
                missing = [i + 1 for i, v in enumerate(visited) if not v]
                raise AssertionError(f"Never reached waypoints: {missing}")
            for i, (lat, lon, _) in enumerate(WAYPOINTS):
                if not visited[i]:
                    d = distance_to(vehicle_reset, lat, lon)
                    if d <= ACCEPTANCE_RADIUS * 3:
                        visited[i] = True
                        print(f"[mission] Waypoint {i+1} reached ({d:.1f}m)")
            time.sleep(0.5)
        print("[mission] All waypoints visited!")

    @pytest.mark.timeout(120)
    def test_mode_is_auto_during_mission(self, vehicle_reset):
        upload_mission(vehicle_reset, WAYPOINTS)
        arm_and_start_mission(vehicle_reset)
        deadline = time.time() + 10
        mode = vehicle_reset.mode.name
        while mode != "AUTO" and time.time() < deadline:
            time.sleep(0.2)
            mode = vehicle_reset.mode.name
        assert mode == "AUTO", f"Expected AUTO, got {mode}"

    @pytest.mark.timeout(180)
    def test_vehicle_returns_home(self, vehicle_reset):
        upload_mission(vehicle_reset, WAYPOINTS)
        arm_and_start_mission(vehicle_reset)
        home = vehicle_reset.home_location
        assert home is not None, "No home location set"
        deadline = time.time() + 160
        while True:
            if time.time() > deadline:
                raise AssertionError("Vehicle never returned home")
            d = distance_to(vehicle_reset, home.lat, home.lon)
            alt = vehicle_reset.location.global_relative_frame.alt
            if d < 10 and alt < 2:
                print(f"[mission] Home reached ({d:.1f}m, {alt:.1f}m AGL)")
                break
            time.sleep(1)
