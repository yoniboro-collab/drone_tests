Summary

What we built

A complete drone test suite that runs on two environments — your local WSL2 SITL and a Docker SITL that anyone can use — automatically on every push to main.



Project structure \& file roles

C:\\drone\_tests\\

│

├── .github/workflows/

│   └── drone\_tests.yml      ← CI pipeline — defines two jobs:

│                               1. drone-tests (local WSL2, runs on every push)

│                               2. docker-sitl (Docker, runs on main/manual)

│

├── tests/

│   ├── test\_arm\_takeoff.py       ← Tests: connect, arm, takeoff, guided mode

│   └── test\_waypoint\_mission.py  ← Tests: mission upload, waypoints, AUTO mode, RTL

│

├── conftest.py              ← Shared fixtures:

│                               - vehicle: connects to SITL (local or docker via SITL\_MODE)

│                               - vehicle\_reset: lands/disarms/resets battery before each test

│                               - telemetry: session-wide CSV logger

│                               - log\_telemetry: auto-attaches telemetry to every test

│

├── telemetry\_logger.py      ← Background thread logging GPS, battery, 

│                               mode, speed to CSV at 2Hz

│                               (log dir configurable via TELEMETRY\_LOG\_DIR env var)

│

├── pytest.ini               ← pytest config: timeout=120s, warning filters

│

├── requirements.txt         ← Python dependencies (dronekit, pymavlink, pytest...)

│

├── docker-compose.yml       ← Defines ArduPilot SITL Docker container

│                               (radarku/ardupilot-sitl, port 5760)

│

├── start\_sitl.sh            ← Starts local ArduPilot SITL in WSL2 + MAVProxy

│

├── start\_sitl\_docker.sh     ← Starts Docker SITL locally, polls port 5760

│                               until ready

│

├── sitl\_params.parm         ← ArduPilot params: disables battery failsafes

│                               so tests don't get interrupted

│

└── .gitignore / .gitattributes  ← Excludes venv/cache, enforces LF line endings



Environment switching

SITL\_MODE=local   → connects to udp:127.0.0.1:14551 (your WSL2 SITL)

SITL\_MODE=docker  → connects to tcp:localhost:5760 (Docker container)



TELEMETRY\_LOG\_DIR=/mnt/c/drone\_tests/telemetry\_logs  ← local default

TELEMETRY\_LOG\_DIR=/tmp/telemetry\_logs                 ← docker CI



CI jobs

JobRuns onTriggerRunnerdrone-testsLocal WSL2 SITLEvery pushYour machine (YONI)docker-sitlDocker containerPush to main / manualGitHub ubuntu-latest



Tests — all 7 passing on both environments ✅

TestWhat it checkstest\_vehicle\_connectsDroneKit can connect to SITLtest\_arm\_and\_reach\_altitudeVehicle arms and reaches target altitudetest\_mode\_is\_guided\_after\_takeoffMode is GUIDED after takeofftest\_mission\_upload5 mission commands stored in ArduPilottest\_vehicle\_visits\_all\_waypointsDrone physically visits all 3 waypointstest\_mode\_is\_auto\_during\_missionMode switches to AUTO during missiontest\_vehicle\_returns\_homeDrone returns and lands at home point



Key fixes along the way

ProblemFixTelemetry dir not createdos.makedirs(os.path.dirname(path), exist\_ok=True)Telemetry path /mnt/c in DockerTELEMETRY\_LOG\_DIR env varDroneKit needs Python 3.8setup-python@v5 with python-version: "3.8"past module missingpip install future before dronekitMission upload got 0 commandsSwitch from raw MAVLink to DroneKit cmds.upload()MAVLink prefix errorsRemoved recv\_match — was racing with DroneKit's threadDocker image download slowDocker layer cache via actions/cache@v4pip reinstall every runpip cache via actions/cache@v4



What's next (from your original list)



Mode switching tests

Geofence breach tests

Task Scheduler for auto-starting runner on Windows login

Slack/email notifications on test failure



Want to start on any of these? 🚁

