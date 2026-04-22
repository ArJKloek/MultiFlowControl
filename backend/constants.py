from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
UI_DIR = BASE_DIR / "ui"
ICON_DIR = BASE_DIR / "icon"
LOG_DIR = BASE_DIR / "logs"
POLL_INTERVAL_MS = 100
LOG_INTERVAL_MS = 300_000  # 5 minutes between periodic measure log entries
