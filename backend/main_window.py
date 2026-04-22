from datetime import datetime
from typing import List, Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QMainWindow

from .constants import LOG_DIR, UI_DIR
from .flow_channel import FlowChannelDialog
from .graph_dialog import GraphDialog
from .logger import SessionLogger
from .node_viewer import NodeViewerDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(str(UI_DIR / "main.ui"), self)

        self.channel_windows: List[FlowChannelDialog] = []
        self._logger: Optional[SessionLogger] = None

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
            if self._logger is not None:
                window.set_logger(self._logger)
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
        if self._logger is not None:
            return
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        filename = LOG_DIR / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self._logger = SessionLogger(filename)
        for window in self.channel_windows:
            window.set_logger(self._logger)
        self.actionStart_logging.setEnabled(False)
        self.actionStop_logging.setEnabled(True)
        self.statusbar.showMessage(f"Logging to {filename.name}")

    def stop_logging(self):
        for window in self.channel_windows:
            window.set_logger(None)
        if self._logger is not None:
            self._logger.close()
            self._logger = None
        self.actionStart_logging.setEnabled(True)
        self.actionStop_logging.setEnabled(False)
        self.statusbar.showMessage("Logging stopped")
