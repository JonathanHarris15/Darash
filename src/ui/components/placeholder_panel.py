from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class PlaceholderPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PlaceholderPanel")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)
        
        # Placeholder for future logo
        self.logo_label = QLabel("Jehu Reader")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("font-size: 48px; font-weight: bold; color: palette(placeholder-text);")
        
        self.desc_label = QLabel("Open a Bible study or reading view from the Activity Bar")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setStyleSheet("font-size: 16px; color: palette(placeholder-text);")
        
        layout.addWidget(self.logo_label)
        layout.addWidget(self.desc_label)
