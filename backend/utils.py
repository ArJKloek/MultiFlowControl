from pathlib import Path
from typing import List, Optional

from serial.tools import list_ports


def safe_float(value) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def discover_serial_ports() -> List[str]:
    ports = [port.device for port in list_ports.comports()]
    if ports:
        return sorted(ports)

    linux_fallback = [
        p for p in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"] if Path(p).exists()
    ]
    if linux_fallback:
        return linux_fallback

    return ["COM1"]
