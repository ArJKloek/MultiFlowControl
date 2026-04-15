from typing import Dict, List

import propar
from PyQt5 import uic
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QDialog

from .constants import UI_DIR
from .models import NodeInfo
from .utils import discover_serial_ports


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
        self.append_log("Press 'Scan' to search for instruments.")

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
