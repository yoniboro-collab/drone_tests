import csv
import threading
import time
import os
from datetime import datetime


class TelemetryLogger:
    """
    Logs drone telemetry to CSV in a background thread.
    Captures GPS, battery, velocity and heading at 2Hz.
    """

    FIELDS = [
        "timestamp",
        "test_name",
        "elapsed_s",
        "lat",
        "lon",
        "alt_m",
        "relative_alt_m",
        "vx_ms",
        "vy_ms",
        "vz_ms",
        "groundspeed_ms",
        "heading_deg",
        "battery_voltage",
        "battery_level_pct",
        "flight_mode",
        "armed",
    ]

    def __init__(self, vehicle, log_dir="/mnt/c/drone_tests/telemetry_logs"):
        self.vehicle = vehicle
        self.log_dir = log_dir
        self._thread = None
        self._stop_event = threading.Event()
        self._current_test = "unknown"
        self._per_test_writer = None
        self._per_test_file = None
        self._run_writer = None
        self._run_file = None
        os.makedirs(log_dir, exist_ok=True)

    def start_run(self, run_id=None):
        """Open the combined run-level CSV."""
        if run_id is None:
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._run_id = run_id
        run_path = os.path.join(self.log_dir, f"run_{run_id}.csv")
        os.makedirs(self.log_dir, exist_ok=True)
        self._run_file = open(run_path, "w", newline="")
        self._run_writer = csv.DictWriter(self._run_file, fieldnames=self.FIELDS)
        self._run_writer.writeheader()
        print(f"[telemetry] Run log: {run_path}")

    def start_test(self, test_name):
        """Open a per-test CSV and start the background logging thread."""
        self._current_test = test_name
        self._test_start = time.time()
        self._stop_event.clear()

        safe_name = test_name.replace("::", "__").replace(" ", "_").replace("/", "__")
        test_path = os.path.join(
            self.log_dir, f"run_{self._run_id}__{safe_name}.csv"
        )

        os.makedirs(os.path.dirname(test_path), exist_ok=True)

        self._per_test_file = open(test_path, "w", newline="")
        self._per_test_writer = csv.DictWriter(
            self._per_test_file, fieldnames=self.FIELDS
        )
        self._per_test_writer.writeheader()
        print(f"[telemetry] Test log: {test_path}")

        self._thread = threading.Thread(target=self._log_loop, daemon=True)
        self._thread.start()

    def stop_test(self):
        """Stop the logging thread and close the per-test CSV."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._per_test_file:
            self._per_test_file.flush()
            self._per_test_file.close()
            self._per_test_file = None

    def stop_run(self):
        """Close the run-level CSV."""
        if self._run_file:
            self._run_file.flush()
            self._run_file.close()
            self._run_file = None

    def _sample(self):
        """Read one telemetry snapshot from the vehicle."""
        try:
            loc = self.vehicle.location.global_frame
            rel = self.vehicle.location.global_relative_frame
            vel = self.vehicle.velocity
            return {
                "timestamp":        datetime.now().isoformat(),
                "test_name":        self._current_test,
                "elapsed_s":        round(time.time() - self._test_start, 2),
                "lat":              loc.lat,
                "lon":              loc.lon,
                "alt_m":            loc.alt,
                "relative_alt_m":   rel.alt,
                "vx_ms":            vel[0] if vel else None,
                "vy_ms":            vel[1] if vel else None,
                "vz_ms":            vel[2] if vel else None,
                "groundspeed_ms":   self.vehicle.groundspeed,
                "heading_deg":      self.vehicle.heading,
                "battery_voltage":  self.vehicle.battery.voltage,
                "battery_level_pct":self.vehicle.battery.level,
                "flight_mode":      self.vehicle.mode.name,
                "armed":            self.vehicle.armed,
            }
        except Exception as e:
            print(f"[telemetry] Sample error: {e}")
            return None

    def _log_loop(self):
        """Background thread — samples at 2Hz."""
        while not self._stop_event.is_set():
            row = self._sample()
            if row:
                if self._per_test_writer:
                    self._per_test_writer.writerow(row)
                if self._run_writer:
                    self._run_writer.writerow(row)
            time.sleep(0.5)