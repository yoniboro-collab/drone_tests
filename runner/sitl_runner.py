import subprocess
import time
import collections
collections.MutableMapping = collections.abc.MutableMapping
from dronekit import connect, VehicleMode
import sys


def start_sitl():
    # We use a single string to avoid join errors
    # Note: Ensure the path to test.parm matches your actual folder
    "   "
    inner_cmd = (
        "cd /mnt/c/ardu/ardupilot && "
        "python3 Tools/autotest/sim_vehicle.py "
        "-v ArduCopter "
        "--no-rebuild "
        "--no-rc "
        "--no-mavproxy "
        "--out=udp:172.17.192.1:14551 "
        "--out=udp:172.17.192.1:14552 "# We only need one reliable stream
        "--add-param-file=/mnt/c/drone_api_tests/test.parm"
    )
    full_command = f'wsl -d Ubuntu bash -l -c "{inner_cmd}"'
    print(f"Starting SITL with: {full_command}")
    subprocess.Popen(full_command, shell=True)

    time.sleep(5)
    mavproxy_cmd = (
        "cd /mnt/c/ardu/ardupilot && "
        "mavproxy.py "
        "--master=tcp:127.0.0.1:5760 "
        "--out=udp:172.17.192.1:14550 "
        "--out=udp:172.17.192.1:14551"
    )
    mavproxy_command = f'wsl -d Ubuntu bash -l -c "{mavproxy_cmd}"'

    print(f"Starting SITL with: {mavproxy_command}")
    return subprocess.Popen(mavproxy_command, shell=True)

    # Note the '-l' flag added here
    full_command = f'wsl -d Ubuntu bash -l -c "{inner_cmd}"'

    print(f"Executing: {full_command}")
    return subprocess.Popen(full_command, shell=True)

# def wait_for_sitl():
#     print("Waiting for SITL to start...")
#     time.sleep(10)
#
# def wait_until_armable(vehicle):
#     print("Waiting for vehicle to become armable...")
#     while not vehicle.is_armable:
#         print(f" Armable: {vehicle.is_armable} | GPS: {vehicle.gps_0.fix_type}")
#         time.sleep(1)
#     print("Vehicle armed")
#
# def run_test():
#     vehicle = connect('tcp:127.0.0.1:5760', wait_ready=True, timeout=60)
#
#     wait_until_armable(vehicle)
#
#     print("Setting GUIDED mode...")
#     vehicle.mode = VehicleMode("GUIDED")
#
#     while vehicle.mode.name != "GUIDED":
#         time.sleep(1)
#
#     print("Arming...")
#     vehicle.armed = True
#
#     while not vehicle.armed:
#         time.sleep(1)
#
#     print("Taking off...")
#     vehicle.simple_takeoff(10)
#
#     # wait until altitude reached
#     while True:
#         alt = vehicle.location.global_relative_frame.alt
#         print(f"Altitude: {alt}")
#         if alt >= 9:
#             print("Reached target altitude")
#             break
#         time.sleep(1)
#
#     time.sleep(3)
#
#     print("Landing...")
#     vehicle.mode = VehicleMode("LAND")
#
#     vehicle.close()

def stop_sitl(proc):
    proc.terminate()
    proc.wait()

# sitl = start_sitl()
# wait_for_sitl()
#
# try:
#     run_test()
# finally:
#     stop_process(sitl)

