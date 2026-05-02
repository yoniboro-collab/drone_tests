🚁 Drone Test Suite — Full Project Summary

What we built:
A complete pytest CI pipeline for testing ArduPilot SITL using DroneKit, running automatically on every git push via GitHub Actions.

Project structure:
C:\drone_tests\
├── .github\
│   └── workflows\
│       └── drone_tests.yml    ← CI pipeline
├── tests\
│   ├── test_arm_takeoff.py    ← arm & takeoff tests
│   └── test_waypoint_mission.py ← waypoint mission tests
├── conftest.py                ← shared fixtures & battery reset
├── pytest.ini                 ← pytest config & warning filters
├── requirements.txt           ← Python dependencies
├── sitl_params.parm           ← SITL battery/failsafe params
├── .gitignore                 ← excludes venv, report, cache
├── .gitattributes             ← enforces LF line endings
└── README.md                  ← project documentation
WSL2 files:
~/drone_venv_38/               ← Linux Python 3.8 venv for CI
/mnt/c/drone_tests/start_sitl.sh ← auto-start SITL + MAVProxy
~/sitl_params.parm             ← SITL battery params

Full stack:

SITL: ArduPilot ArduCopter in WSL2 Ubuntu
MAVProxy: bridges SITL TCP 5760 → UDP ports
DroneKit: Python MAVLink library
pytest: test runner with timeout, html report
QGC / Mission Planner: visual monitoring on Windows
GitHub Actions: CI on every push
Self-hosted runner: your Windows machine (YONI) running run.cmd


UDP port layout:
MAVProxy forwards to:
├── udp:127.0.0.1:14550  → QGC inside WSL (unused)
├── udp:127.0.0.1:14551  → pytest/DroneKit inside WSL2
└── udp:172.17.192.1:14552 → QGC/Mission Planner on Windows

Tests — all 7 passing ✅:

test_vehicle_connects
test_arm_and_reach_altitude
test_mode_is_guided_after_takeoff
test_mission_upload
test_vehicle_visits_all_waypoints
test_mode_is_auto_during_mission
test_vehicle_returns_home


CI workflow steps:

Checkout code
Start SITL in WSL2 (start_sitl.sh)
Debug — verify SITL alive
Install dependencies (~/drone_venv_38)
Run drone tests (Linux Python 3.8 inside WSL2)
Stop SITL
Upload HTML report as artifact


Key fixes solved:
ProblemFixpytest not foundpython -m pytestDroneKit DeprecationWarningfilterwarnings in pytest.initest_mission_upload failingUse MISSION_ITEM_INT + MISSION_COUNT checkBattery drainingDisable failsafes via sitl_params.parmSITL clock driftntpdate + wsl --shutdownCI WSL2 not visibleRun run.cmd interactively as your userCI wrong Python (3.12)Created ~/drone_venv_38 with Python 3.8CI platform win32Run pytest via wsl bash -c with Linux PythonMAVProxy dying after scriptUse nohup, remove --daemon flagQGC/MP can't connect during CIAdd --out=udp:${WIN_IP}:14552 to MAVProxy.venv_38 committed to git.gitignore + git rm --cachedShell script CRLF issues.gitattributes enforcing LF

How to start everything manually:
WSL Terminal 1 — start everything:
bash/mnt/c/drone_tests/start_sitl.sh
Windows CMD — run tests:
cmdcd C:\drone_tests
.venv_38\Scripts\activate
python -m pytest tests/ -v --html=report.html --self-contained-html
QGC — connects automatically on UDP 14552
Mission Planner — set UDP port 14552, click Connect

How to trigger CI:
cmdcd C:\drone_tests
git add .
git commit -m "your message"
git push
GitHub Actions runs automatically → results at:
https://github.com/yoniboro-collab/drone_tests/actions

Runner setup (if restarting machine):
powershellcd C:\actions-runner
.\run.cmd
Keep this window open — runner must be running for CI to work.

Next things to consider:

Make runner start automatically on Windows login (Task Scheduler)
Add Slack/email notifications on test failure
Add telemetry CSV logging per test run
Add geofence breach tests
Add mode switching tests


Good luck! 🚁