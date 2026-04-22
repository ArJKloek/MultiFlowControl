import csv
import re
import time
from datetime import datetime
from pathlib import Path


class SessionLogger:
    """Writes instrument events to a CSV file.

    Output format matches log_CO2.csv:
        ts, iso, port, address, kind, name, value, unit, extra, usertag
    """

    COLUMNS = ["ts", "iso", "port", "address", "kind", "name", "value", "unit", "extra", "usertag"]

    def __init__(self, path: Path, flush_interval_s: float = 1.0):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._flush_interval_s = max(0.0, float(flush_interval_s))
        self._last_flush_ts = time.monotonic()
        file_exists = path.exists()
        self._file = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        if not file_exists or path.stat().st_size == 0:
            self._writer.writerow(self.COLUMNS)
        self._file.flush()

    @property
    def path(self) -> Path:
        return self._path

    def _write_row(
        self,
        port: str,
        address: int,
        kind: str,
        name: str,
        value: float,
        unit: str = "",
        extra: str = "",
        usertag: str = "",
    ) -> None:
        now = time.time()
        iso = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        self._writer.writerow([f"{now:.3f}", iso, port, address, kind, name, value, unit, extra, usertag])
        if self._flush_interval_s == 0.0:
            self._file.flush()
            self._last_flush_ts = time.monotonic()
            return

        t_now = time.monotonic()
        if (t_now - self._last_flush_ts) >= self._flush_interval_s:
            self._file.flush()
            self._last_flush_ts = t_now

    def log_setpoint(
        self,
        port: str,
        address: int,
        setpoint_flow: float,
        setpoint_percent: float,
        unit: str = "",
        usertag: str = "",
    ) -> None:
        """Log a setpoint change (two rows: flow value and raw percent)."""
        self._write_row(port, address, "setpoint", "fSetpoint", setpoint_flow, unit=unit, usertag=usertag)
        self._write_row(port, address, "setpoint", "fSetpoint_raw", setpoint_percent, usertag=usertag)

    def log_measure(
        self,
        port: str,
        address: int,
        compensated_flow: float,
        raw_flow: float,
        unit: str = "",
        sample_count: int = 0,
        gasfactor: float = 1.0,
        usertag: str = "",
    ) -> None:
        """Log a periodic measurement summary.

        fMeasure is gasfactor-compensated flow, fMeasure_raw is original measured flow.
        """
        extra_parts = []
        if sample_count > 0:
            extra_parts.append(f"{sample_count} samples")
        if abs(gasfactor - 1.0) > 1e-9:
            extra_parts.append(f"gasfactor={gasfactor:.6f}")
        extra = "; ".join(extra_parts)
        self._write_row(port, address, "measure", "fMeasure", compensated_flow, unit=unit, extra=extra, usertag=usertag)
        self._write_row(port, address, "measure", "fMeasure_raw", raw_flow, unit=unit, extra=extra, usertag=usertag)

    def log_gasfactor(
        self,
        port: str,
        address: int,
        gasfactor: float,
        usertag: str = "",
        extra: str = "",
    ) -> None:
        """Log an explicit gasfactor event."""
        self._write_row(port, address, "config", "gasfactor", gasfactor, extra=extra, usertag=usertag)

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()


def make_log_path(log_dir: Path, usertag: str, port: str, address: int) -> Path:
    """Return a per-channel log file path.

    Filename pattern: log_{usertag}.csv
    Falls back to log_{port_slug}_addr{address}.csv when usertag is empty.
    """
    slug = re.sub(r"[^\w\-]", "_", usertag.strip()) if usertag.strip() else ""
    if not slug:
        slug = re.sub(r"[^\w\-]", "_", port) + f"_addr{address}"
    return log_dir / f"log_{slug}.csv"
