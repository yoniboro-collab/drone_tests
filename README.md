Welcome back! Here's a full summary of everything we built:



🚁 Drone Test Suite — Project Summary

What we built:

A complete pytest framework for testing ArduPilot SITL (Software In The Loop) using DroneKit on Windows with WSL2.

Project structure:

C:\\drone\_tests\\

├── .github\\workflows\\drone\_tests.yml  ← CI pipeline

├── tests\\

│   ├── test\_arm\_takeoff.py            ← arm \& takeoff tests

│   └── test\_waypoint\_mission.py       ← waypoint mission tests

├── conftest.py                        ← shared fixtures

├── pytest.ini                         ← pytest config

├── requirements.txt                   ← dependencies

├── sitl\_params.parm                   ← SITL battery/failsafe params

└── start\_sitl.sh                      ← auto-start script (in WSL)



Stack:



SITL: ArduPilot ArduCopter running in WSL2 Ubuntu

MAVProxy: bridges SITL TCP→UDP

DroneKit: Python library connecting to SITL

pytest: test runner

QGC / Mission Planner: visual monitoring (optional)

GitHub Actions: CI pipeline

Self-hosted runner: your Windows machine (YONI)





Key fixes we solved:

ProblemFixpytest not found on WindowsUse python -m pytestDroneKit DeprecationWarningSilence via pytest.ini filterwarningsPytestUnknownMarkWarningpip install pytest-timeouttest\_mission\_upload failingBypass DroneKit uploader, use MISSION\_ITEM\_INT directly + MISSION\_COUNT checkBattery draining between runsDisable failsafes via MAVLink params + sitl\_params.parmSITL clock drift (time moved backwards)sudo ntpdate pool.ntp.org + wsl --shutdownSecond run fails (dirty SITL state)vehicle\_reset fixture clears mission + disarmsCI WSL2 not visible to runner serviceRun run.cmd interactively as your userCI wrong Python (3.14)Created \~/drone\_venv\_38 with Python 3.8 in WSL2CI platform win32 instead of linuxRun pytest via wsl bash -c using Linux PythonMAVProxy IP issuesUse 127.0.0.1 for everything inside WSL2



Tests passing locally (7/7):



test\_vehicle\_connects ✅

test\_arm\_and\_reach\_altitude ✅

test\_mode\_is\_guided\_after\_takeoff ✅

test\_mission\_upload ✅

test\_vehicle\_visits\_all\_waypoints ✅

test\_mode\_is\_auto\_during\_mission ✅

test\_vehicle\_returns\_home ✅





CI status — in progress 🔄

The CI pipeline works up to connecting to SITL but MAVProxy dies after start\_sitl.sh exits.

Where we left off:

The core problem is that start\_sitl.sh starts MAVProxy as a background process (\&) but it dies when the script exits in the CI environment. We were about to investigate using nohup properly or switching to a different CI approach.

Two options to continue:



Fix current approach — make MAVProxy survive after script exits using nohup + verify with a debug step

Switch to ubuntu-latest + Docker SITL — cleaner, no WSL2 issues, fully cloud-based



My recommendation: Option 2 — ubuntu-latest with ArduPilot's pre-built SITL Docker image. It's more reliable and scales better. But requires SITL to run in Docker which needs some setup.



How to start SITL manually (your current workflow):

WSL Terminal 1:

bashcd /mnt/c/ardu/ardupilot

python3 Tools/autotest/sim\_vehicle.py -v ArduCopter --no-rebuild --no-rc --no-mavproxy -w --add-param-file=/mnt/c/drone\_tests/sitl\_params.parm

WSL Terminal 2:

bashmavproxy.py --master=tcp:127.0.0.1:5760 --out=udp:172.17.192.1:14550 --out=udp:172.17.192.1:14551

Windows CMD:

cmdcd C:\\drone\_tests

.venv\_38\\Scripts\\activate

python -m pytest tests/ -v --html=report.html --self-contained-html



When you start a new conversation, share this summary and pick up from the CI MAVProxy issue. Good luck! 🚁

