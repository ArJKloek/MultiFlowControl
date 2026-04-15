from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import propar
from serial.tools import list_ports
from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow


BASE_DIR = Path(__file__).resolve().parents[1]
UI_DIR = BASE_DIR / "ui"


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


@dataclass
class NodeInfo:
    port: str
    address: int
    type_name: str
    serial: str
    channels: int
    node_id: str


class NodeViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "nodeviewer.ui"), self)

        self.selected_nodes: List[NodeInfo] = []
        self._nodes_by_row: Dict[int, NodeInfo] = {}

        self.model = QStandardItemModel(self)
        self.model.setHorizontalHeaderLabels(["Port", "Address", "Type", "Serial", "Channels", "Id"])
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.ExtendedSelection)

        self.btnScan.clicked.connect(self.scan_nodes)
        self.btnConnect.clicked.connect(self.connect_selected)
        self.log.setReadOnly(True)

        self.scan_nodes()

    def append_log(self, text: str):
        self.log.append(text)

    def scan_nodes(self):
        self.model.removeRows(0, self.model.rowCount())
        self._nodes_by_row.clear()
        self.btnConnect.setEnabled(False)
        self.selected_nodes = []

        ports = discover_serial_ports()
        self.append_log(f"Scanning ports: {', '.join(ports)}")

        row = 0
        for port in ports:
            try:
                local = propar.instrument(port)
                nodes = local.master.get_nodes()
            except Exception as exc:
                self.append_log(f"{port}: scan failed ({exc})")
                continue

            if not nodes:
                self.append_log(f"{port}: no nodes found")
                continue

            self.append_log(f"{port}: found {len(nodes)} node(s)")
            for node in nodes:
                node_info = NodeInfo(
                    port=port,
                    address=int(node.get("address", 0)),
                    type_name=str(node.get("type", "Unknown")),
                    serial=str(node.get("serial", "Unknown")),
                    channels=int(node.get("channels", 1) or 1),
                    node_id=str(node.get("id", "")),
                )

                values = [
                    node_info.port,
                    str(node_info.address),
                    node_info.type_name,
                    node_info.serial,
                    str(node_info.channels),
                    node_info.node_id,
                ]
                self.model.appendRow([QStandardItem(v) for v in values])
                self._nodes_by_row[row] = node_info
                row += 1

        self.btnConnect.setEnabled(self.model.rowCount() > 0)
        if self.model.rowCount() == 0:
            self.append_log("No instruments found.")

        self.table.resizeColumnsToContents()

    def connect_selected(self):
        selected_rows = [index.row() for index in self.table.selectionModel().selectedRows()]
        if not selected_rows:
            selected_rows = list(range(self.model.rowCount()))

        self.selected_nodes = [self._nodes_by_row[row] for row in sorted(set(selected_rows)) if row in self._nodes_by_row]
        if not self.selected_nodes:
            self.append_log("No nodes selected.")
            return

        self.accept()


class FlowChannelDialog(QDialog):
    def __init__(self, node: NodeInfo, channel: int, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "flowchannel.ui"), self)

        self.node = node
        self.channel = channel
        self.capacity_value: Optional[float] = None
        self.last_status = ""

        self.instrument = propar.instrument(self.node.port, address=self.node.address, channel=self.channel)

        self.advancedFrame.setVisible(False)

        self.ds_setpoint_percent.setRange(0.0, 100.0)
        self.ds_measure_percent.setRange(0.0, 100.0)
        self.ds_setpoint_flow.setDecimals(4)
        self.ds_measure_flow.setDecimals(4)

        self.vs_setpoint.setRange(0, 100)
        self.vs_measure.setRange(0, 100)

        self.le_number.setReadOnly(True)
        self.le_number.setText(f"{self.node.address}-ch{self.channel}")
        self.le_type.setText(self.node.type_name)
        self.le_serial.setText(self.node.serial)

        self.btnAdvanced.clicked.connect(self.toggle_advanced)
        self.pb_reload.clicked.connect(self.reload_all)
        self.le_usertag.editingFinished.connect(self.update_usertag)

        self.vs_setpoint.valueChanged.connect(self.on_setpoint_slider_changed)
        self.ds_setpoint_percent.valueChanged.connect(self.on_setpoint_percent_changed)
        self.ds_setpoint_flow.valueChanged.connect(self.on_setpoint_flow_changed)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh_live_values)

        self.reload_all()
        self.timer.start()

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

        if unit is not None:
            self.lb_unit1.setText(str(unit))
            self.lb_unit2.setText(str(unit))

        capacity_float = safe_float(capacity)
        self.capacity_value = capacity_float
        if capacity_float is not None:
            self.le_capacity.setText(f"{capacity_float:.4f}")
            self.ds_setpoint_flow.setMaximum(max(capacity_float * 1.2, 1.0))
            self.ds_measure_flow.setMaximum(max(capacity_float * 1.2, 1.0))
        elif capacity is not None:
            self.le_capacity.setText(str(capacity))

        self.refresh_live_values()
        if not self.last_status:
            self.set_status("Ready")

    def toggle_advanced(self):
        self.advancedFrame.setVisible(not self.advancedFrame.isVisible())

    def update_usertag(self):
        text = self.le_usertag.text().strip()
        if text:
            self.safe_write(115, text)

    def on_setpoint_slider_changed(self, value: int):
        percent = float(value)
        if abs(self.ds_setpoint_percent.value() - percent) > 0.01:
            self.ds_setpoint_percent.blockSignals(True)
            self.ds_setpoint_percent.setValue(percent)
            self.ds_setpoint_percent.blockSignals(False)
        self.apply_setpoint_percent(percent)

    def on_setpoint_percent_changed(self, percent: float):
        slider_value = int(round(percent))
        if self.vs_setpoint.value() != slider_value:
            self.vs_setpoint.blockSignals(True)
            self.vs_setpoint.setValue(slider_value)
            self.vs_setpoint.blockSignals(False)

        self.apply_setpoint_percent(percent)

        if self.capacity_value:
            flow_value = (percent / 100.0) * self.capacity_value
            if abs(self.ds_setpoint_flow.value() - flow_value) > 1e-6:
                self.ds_setpoint_flow.blockSignals(True)
                self.ds_setpoint_flow.setValue(flow_value)
                self.ds_setpoint_flow.blockSignals(False)

    def on_setpoint_flow_changed(self, value: float):
        if self.capacity_value and self.capacity_value > 0:
            percent = max(0.0, min(100.0, (value / self.capacity_value) * 100.0))
            if abs(self.ds_setpoint_percent.value() - percent) > 1e-6:
                self.ds_setpoint_percent.blockSignals(True)
                self.ds_setpoint_percent.setValue(percent)
                self.ds_setpoint_percent.blockSignals(False)
                self.apply_setpoint_percent(percent)

    def apply_setpoint_percent(self, percent: float):
        raw_setpoint = int(max(0, min(32000, round((percent / 100.0) * 32000))))
        self.safe_write(9, raw_setpoint)

    def refresh_live_values(self):
        measure_raw = self.safe_read(8)
        measure_flow = self.safe_read(205)
        setpoint_raw = self.safe_read(9)

        if measure_raw is not None:
            measure_percent = max(0.0, min(100.0, (float(measure_raw) / 32000.0) * 100.0))
            self.ds_measure_percent.setValue(measure_percent)
            self.vs_measure.setValue(int(round(measure_percent)))

            if measure_flow is None and self.capacity_value:
                measure_flow = (measure_percent / 100.0) * self.capacity_value

        if measure_flow is not None:
            flow_float = safe_float(measure_flow)
            if flow_float is not None:
                self.ds_measure_flow.setValue(flow_float)

        if setpoint_raw is not None:
            setpoint_percent = max(0.0, min(100.0, (float(setpoint_raw) / 32000.0) * 100.0))
            if abs(self.ds_setpoint_percent.value() - setpoint_percent) > 0.5:
                self.ds_setpoint_percent.blockSignals(True)
                self.ds_setpoint_percent.setValue(setpoint_percent)
                self.ds_setpoint_percent.blockSignals(False)
            if self.vs_setpoint.value() != int(round(setpoint_percent)):
                self.vs_setpoint.blockSignals(True)
                self.vs_setpoint.setValue(int(round(setpoint_percent)))
                self.vs_setpoint.blockSignals(False)

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


class GraphDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "graph.ui"), self)
        self.pb_close.clicked.connect(self.close)
        self.le_status.setText("Graph UI loaded")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(str(UI_DIR / "main.ui"), self)

        self.channel_windows: List[FlowChannelDialog] = []

        self.actionOpen_scanner.triggered.connect(self.open_node_scanner)
        self.actionShow_graph.triggered.connect(self.show_graph)

        self.actionStart_logging.triggered.connect(self.start_logging)
        self.actionStop_logging.triggered.connect(self.stop_logging)

        self.statusbar.showMessage("Ready")

    def open_node_scanner(self):
        dialog = NodeViewerDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        created = 0
        for node in dialog.selected_nodes:
            window = FlowChannelDialog(node=node, channel=1, parent=self)
            window.setAttribute(Qt.WA_DeleteOnClose, True)
            window.show()
            window.destroyed.connect(lambda _, w=window: self._remove_channel_window(w))
            self.channel_windows.append(window)
            created += 1

        self.statusbar.showMessage(f"Connected {created} instrument window(s)")

    def _remove_channel_window(self, window):
        if window in self.channel_windows:
            self.channel_windows.remove(window)

    def show_graph(self):
        graph = GraphDialog(self)
        graph.exec_()

    def start_logging(self):
        self.actionStart_logging.setEnabled(False)
        self.actionStop_logging.setEnabled(True)
        self.statusbar.showMessage("Logging started")

    def stop_logging(self):
        self.actionStart_logging.setEnabled(True)
        self.actionStop_logging.setEnabled(False)
        self.statusbar.showMessage("Logging stopped")


def run():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(run())
