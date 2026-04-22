import time
from pathlib import Path
from typing import Optional

import propar
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog

from .constants import ICON_DIR, LOG_INTERVAL_MS, POLL_INTERVAL_MS, UI_DIR
from .logger import SessionLogger, make_log_path
from .models import NodeInfo
from .utils import safe_float


class FlowChannelDialog(QDialog):
    def __init__(self, node: NodeInfo, channel: int, parent=None):
        super().__init__(parent)
        self.node = node
        self.channel = channel
        self._loading_fluids = False

        self.logger: Optional[SessionLogger] = None
        self._measure_acc_flow: list = []
        self._measure_acc_percent: list = []
        self._last_flush_ts: float = 0.0

        node_type = (self.node.type_name or "").upper()
        self.is_dmfm = "DMFM" in node_type
        ui_file = "flowchannel_meter.ui" if self.is_dmfm else "flowchannel.ui"
        uic.loadUi(str(UI_DIR / ui_file), self)

        self.capacity_value: Optional[float] = None
        self.last_status = ""

        self.instrument = propar.instrument(self.node.port, address=self.node.address, channel=self.channel)
        self._setup_icon()

        if hasattr(self, "advancedFrame"):
            self.advancedFrame.setVisible(False)

        if hasattr(self, "ds_setpoint_percent"):
            self.ds_setpoint_percent.setRange(0.0, 100.0)
        if hasattr(self, "ds_measure_percent"):
            self.ds_measure_percent.setRange(0.0, 100.0)
        if hasattr(self, "ds_setpoint_flow"):
            self.ds_setpoint_flow.setDecimals(4)
        self.ds_measure_flow.setDecimals(4)

        if hasattr(self, "vs_setpoint"):
            self.vs_setpoint.setRange(0, 100)
        if hasattr(self, "vs_measure"):
            self.vs_measure.setRange(0, 100)

        self.le_number.setReadOnly(True)
        self.le_number.setText(f"{self.node.address}-ch{self.channel}")
        self.le_type.setText(self.node.type_name)
        self.le_serial.setText(self.node.serial)

        self.btnAdvanced.clicked.connect(self.toggle_advanced)
        self.pb_reload.clicked.connect(self.reload_all)
        self.le_usertag.editingFinished.connect(self.update_usertag)
        if hasattr(self, "cb_fluids"):
            self.cb_fluids.currentIndexChanged.connect(self.on_fluid_selection_changed)

        if hasattr(self, "vs_setpoint"):
            self.vs_setpoint.valueChanged.connect(self.on_setpoint_slider_changed)
            self.vs_setpoint.sliderReleased.connect(self.commit_setpoint_from_percent)
        if hasattr(self, "ds_setpoint_percent"):
            self.ds_setpoint_percent.valueChanged.connect(self.on_setpoint_percent_changed)
            self.ds_setpoint_percent.editingFinished.connect(self.commit_setpoint_from_percent)
        if hasattr(self, "ds_setpoint_flow"):
            self.ds_setpoint_flow.valueChanged.connect(self.on_setpoint_flow_changed)
            self.ds_setpoint_flow.editingFinished.connect(self.commit_setpoint_from_flow)

        self.timer = QTimer(self)
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self.refresh_live_values)

        self.reload_all()
        self.load_available_fluids()
        self.timer.start()

    def _setup_icon(self):
        if not hasattr(self, "lb_icon"):
            return

        node_type = (self.node.type_name or "").upper()
        icon_file = None
        if "DMFC" in node_type:
            icon_file = ICON_DIR / "massflow.png"
        elif "DMFM" in node_type:
            icon_file = ICON_DIR / "massview.png"

        if icon_file is None or not icon_file.exists():
            return

        pixmap = QPixmap(str(icon_file))
        if pixmap.isNull():
            return

        self.lb_icon.setScaledContents(False)
        scaled = pixmap.scaled(
            60,
            60,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.lb_icon.setPixmap(scaled)

    def set_status(self, text: str):
        self.last_status = text
        self.le_status.setText(text)

    def safe_read(self, dde_number: int):
        try:
            return self.instrument.readParameter(dde_number)
        except Exception as exc:
            self.set_status(f"Read p{dde_number} failed: {exc}")
            return None

    def safe_write(self, dde_number: int, value) -> bool:
        try:
            ok = self.instrument.writeParameter(dde_number, value)
            if ok:
                self.set_status(f"Wrote p{dde_number}={value}")
            else:
                self.set_status(f"Write p{dde_number} failed")
            return bool(ok)
        except Exception as exc:
            self.set_status(f"Write p{dde_number} failed: {exc}")
            return False

    def reload_all(self):
        current_fluid_index = self.safe_read(24)
        usertag = self.safe_read(115)
        model = self.safe_read(91)
        fluid = self.safe_read(25)
        unit = self.safe_read(129)
        capacity = self.safe_read(21)

        if usertag is not None:
            self.le_usertag.setText(str(usertag))
        if model is not None:
            self.le_model.setText(str(model))
        if fluid is not None:
            self.le_fluid.setText(str(fluid))
        if current_fluid_index is not None:
            self._set_fluid_combo_selection(int(current_fluid_index))

        if unit is not None:
            if hasattr(self, "lb_unit1"):
                self.lb_unit1.setText(str(unit))
            if hasattr(self, "lb_unit2"):
                self.lb_unit2.setText(str(unit))
            if hasattr(self, "lb_unit"):
                self.lb_unit.setText(str(unit))

        capacity_float = safe_float(capacity)
        self.capacity_value = capacity_float
        if capacity_float is not None:
            self.le_capacity.setText(f"{capacity_float:.4f}")
            if hasattr(self, "ds_setpoint_flow"):
                self.ds_setpoint_flow.setMaximum(max(capacity_float * 1.2, 1.0))
            self.ds_measure_flow.setMaximum(max(capacity_float * 1.2, 1.0))
        elif capacity is not None:
            self.le_capacity.setText(str(capacity))

        self.refresh_live_values()
        if not self.last_status:
            self.set_status("Ready")

    def _set_fluid_combo_selection(self, fluid_index: int):
        if not hasattr(self, "cb_fluids") or self.cb_fluids.count() == 0:
            return

        for combo_index in range(self.cb_fluids.count()):
            item_data = self.cb_fluids.itemData(combo_index)
            if item_data == fluid_index:
                self.cb_fluids.blockSignals(True)
                self.cb_fluids.setCurrentIndex(combo_index)
                self.cb_fluids.blockSignals(False)
                return

    def load_available_fluids(self):
        if not hasattr(self, "cb_fluids"):
            return

        original_index = self.safe_read(24)
        if original_index is None:
            return

        self._loading_fluids = True
        self.cb_fluids.blockSignals(True)
        self.cb_fluids.clear()

        try:
            for fluid_index in range(0, 9):
                if not self.safe_write(24, fluid_index):
                    continue

                fluid_name = self.safe_read(25)
                fluid_props = self.safe_read(238)
                if fluid_name is None:
                    continue

                props_value = int(fluid_props) if fluid_props is not None else 0
                if not (props_value & 0x01):
                    continue

                display_name = str(fluid_name).strip() or f"Fluid {fluid_index}"
                self.cb_fluids.addItem(f"{fluid_index}: {display_name}", fluid_index)
        finally:
            self.safe_write(24, original_index)
            self.cb_fluids.blockSignals(False)
            self._loading_fluids = False

        self._set_fluid_combo_selection(int(original_index))

    def on_fluid_selection_changed(self, combo_index: int):
        if self._loading_fluids or not hasattr(self, "cb_fluids"):
            return

        fluid_index = self.cb_fluids.itemData(combo_index)
        if fluid_index is None:
            return

        if self.safe_write(24, int(fluid_index)):
            self.reload_all()

    def toggle_advanced(self):
        if hasattr(self, "advancedFrame"):
            self.advancedFrame.setVisible(not self.advancedFrame.isVisible())

    def update_usertag(self):
        text = self.le_usertag.text().strip()
        if text:
            self.safe_write(115, text)

    def on_setpoint_slider_changed(self, value: int):
        if not hasattr(self, "ds_setpoint_percent"):
            return
        percent = float(value)
        if abs(self.ds_setpoint_percent.value() - percent) > 0.01:
            self.ds_setpoint_percent.blockSignals(True)
            self.ds_setpoint_percent.setValue(percent)
            self.ds_setpoint_percent.blockSignals(False)

    def on_setpoint_percent_changed(self, percent: float):
        if not hasattr(self, "vs_setpoint"):
            return
        slider_value = int(round(percent))
        if self.vs_setpoint.value() != slider_value:
            self.vs_setpoint.blockSignals(True)
            self.vs_setpoint.setValue(slider_value)
            self.vs_setpoint.blockSignals(False)

        if self.capacity_value and hasattr(self, "ds_setpoint_flow"):
            flow_value = (percent / 100.0) * self.capacity_value
            if abs(self.ds_setpoint_flow.value() - flow_value) > 1e-6:
                self.ds_setpoint_flow.blockSignals(True)
                self.ds_setpoint_flow.setValue(flow_value)
                self.ds_setpoint_flow.blockSignals(False)

    def on_setpoint_flow_changed(self, value: float):
        if self.capacity_value and self.capacity_value > 0 and hasattr(self, "ds_setpoint_percent"):
            percent = max(0.0, min(100.0, (value / self.capacity_value) * 100.0))
            if abs(self.ds_setpoint_percent.value() - percent) > 1e-6:
                self.ds_setpoint_percent.blockSignals(True)
                self.ds_setpoint_percent.setValue(percent)
                self.ds_setpoint_percent.blockSignals(False)

    def commit_setpoint_from_percent(self):
        if not hasattr(self, "ds_setpoint_percent"):
            return
        self.apply_setpoint_percent(float(self.ds_setpoint_percent.value()))

    def commit_setpoint_from_flow(self):
        if not hasattr(self, "ds_setpoint_flow") or not self.capacity_value or self.capacity_value <= 0:
            return
        percent = max(0.0, min(100.0, (self.ds_setpoint_flow.value() / self.capacity_value) * 100.0))
        self.apply_setpoint_percent(percent)

    def _is_user_editing_setpoint(self) -> bool:
        if hasattr(self, "vs_setpoint") and self.vs_setpoint.isSliderDown():
            return True
        if hasattr(self, "ds_setpoint_percent") and self.ds_setpoint_percent.hasFocus():
            return True
        if hasattr(self, "ds_setpoint_flow") and self.ds_setpoint_flow.hasFocus():
            return True
        return False

    def apply_setpoint_percent(self, percent: float):
        if self.is_dmfm:
            return
        raw_setpoint = int(max(0, min(32000, round((percent / 100.0) * 32000))))
        if self.safe_write(9, raw_setpoint) and self.logger is not None:
            flow = (percent / 100.0) * self.capacity_value if self.capacity_value else 0.0
            self.logger.log_setpoint(
                port=self.node.port,
                address=self.node.address,
                setpoint_flow=flow,
                setpoint_percent=percent,
                unit=self._current_unit(),
                usertag=self.le_usertag.text().strip(),
            )

    def refresh_live_values(self):
        measure_raw = self.safe_read(8)
        measure_flow = self.safe_read(205)
        setpoint_raw = self.safe_read(9) if not self.is_dmfm else None

        _log_measure_percent: Optional[float] = None
        _log_flow_float: Optional[float] = None

        if measure_raw is not None:
            measure_percent = max(0.0, min(100.0, (float(measure_raw) / 32000.0) * 100.0))
            _log_measure_percent = measure_percent
            if hasattr(self, "ds_measure_percent"):
                self.ds_measure_percent.setValue(measure_percent)
            if hasattr(self, "vs_measure"):
                self.vs_measure.setValue(int(round(measure_percent)))
            if hasattr(self, "pb_flow"):
                self.pb_flow.setValue(int(round(measure_percent)))

            if measure_flow is None and self.capacity_value:
                measure_flow = (measure_percent / 100.0) * self.capacity_value

        if measure_flow is not None:
            flow_float = safe_float(measure_flow)
            if flow_float is not None:
                self.ds_measure_flow.setValue(flow_float)
                _log_flow_float = flow_float

        if self.logger is not None and _log_measure_percent is not None and _log_flow_float is not None:
            self._measure_acc_flow.append(_log_flow_float)
            self._measure_acc_percent.append(_log_measure_percent)
            if (time.monotonic() - self._last_flush_ts) * 1000 >= LOG_INTERVAL_MS:
                n = len(self._measure_acc_flow)
                self.logger.log_measure(
                    port=self.node.port,
                    address=self.node.address,
                    measure_flow=sum(self._measure_acc_flow) / n,
                    measure_percent=sum(self._measure_acc_percent) / n,
                    unit=self._current_unit(),
                    sample_count=n,
                    usertag=self.le_usertag.text().strip(),
                )
                self._measure_acc_flow.clear()
                self._measure_acc_percent.clear()
                self._last_flush_ts = time.monotonic()

        if setpoint_raw is not None:
            setpoint_percent = max(0.0, min(100.0, (float(setpoint_raw) / 32000.0) * 100.0))
            if self._is_user_editing_setpoint():
                return

            if hasattr(self, "ds_setpoint_percent") and abs(self.ds_setpoint_percent.value() - setpoint_percent) > 0.5:
                self.ds_setpoint_percent.blockSignals(True)
                self.ds_setpoint_percent.setValue(setpoint_percent)
                self.ds_setpoint_percent.blockSignals(False)
            if hasattr(self, "vs_setpoint") and self.vs_setpoint.value() != int(round(setpoint_percent)):
                self.vs_setpoint.blockSignals(True)
                self.vs_setpoint.setValue(int(round(setpoint_percent)))
                self.vs_setpoint.blockSignals(False)

            if self.capacity_value and hasattr(self, "ds_setpoint_flow"):
                setpoint_flow = (setpoint_percent / 100.0) * self.capacity_value
                if abs(self.ds_setpoint_flow.value() - setpoint_flow) > 1e-6:
                    self.ds_setpoint_flow.blockSignals(True)
                    self.ds_setpoint_flow.setValue(setpoint_flow)
                    self.ds_setpoint_flow.blockSignals(False)

    def start_logging(self, log_dir: Path) -> None:
        """Create a per-channel log file named after the usertag (or port/address fallback)."""
        if self.logger is not None:
            return
        path = make_log_path(log_dir, self.le_usertag.text(), self.node.port, self.node.address)
        self.logger = SessionLogger(path)
        self._measure_acc_flow.clear()
        self._measure_acc_percent.clear()
        self._last_flush_ts = time.monotonic()
        self.set_status(f"Logging to {path.name}")

    def stop_logging(self) -> None:
        """Flush and close the per-channel log file."""
        if self.logger is not None:
            self.logger.close()
            self.logger = None
        self._measure_acc_flow.clear()
        self._measure_acc_percent.clear()

    def set_logger(self, logger: Optional[SessionLogger]) -> None:
        """Attach or detach a SessionLogger. Clears any accumulated samples."""
        self.logger = logger
        self._measure_acc_flow.clear()
        self._measure_acc_percent.clear()
        self._last_flush_ts = time.monotonic()

    def _current_unit(self) -> str:
        """Return the unit string currently shown in the dialog, or empty string."""
        for attr in ("lb_unit", "lb_unit1", "lb_unit2"):
            widget = getattr(self, attr, None)
            if widget is not None:
                return widget.text().strip()
        return ""

    def closeEvent(self, event):
        self.timer.stop()
        self.stop_logging()
        super().closeEvent(event)
