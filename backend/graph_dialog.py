from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

from .constants import UI_DIR


class GraphDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "graph.ui"), self)
        self.pb_close.clicked.connect(self.close)
        self.le_status.setText("Graph UI loaded")
