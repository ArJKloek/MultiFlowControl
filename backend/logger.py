import csv
import time
from datetime import datetime
from pathlib import Path


class SessionLogger:
    """Writes instrument events to a CSV file.

    Output format matches log_CO2.csv:
        ts, iso, port, address, kind, name, value, unit, extra, usertag
    """

    COLUMNS = ["ts", "iso", "port", "address", "kind", "name", "value", "unit", "extra", "usertag"]

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
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
        self._file.flush()

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
        measure_flow: float,
        measure_percent: float,
        unit: str = "",
        sample_count: int = 0,
        usertag: str = "",
    ) -> None:
        """Log a periodic measurement summary (two rows: flow average and raw percent average)."""
        extra = f"{sample_count} samples" if sample_count > 0 else ""
        self._write_row(port, address, "measure", "fMeasure", measure_flow, unit=unit, extra=extra, usertag=usertag)
        self._write_row(port, address, "measure", "fMeasure_raw", measure_percent, extra=extra, usertag=usertag)

    def close(self) -> None:
        if self._file and not self._file.closed:
            self._file.close()
