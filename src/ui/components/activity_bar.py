from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QPainter

class ActivityBarButton(QPushButton):
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedSize(50, 50)
        
        # We could use QIcon here if we had SVGs. Using text abbreviation for now.
        font = QFont("Consolas", 14, QFont.Bold)
        self.setFont(font)
        
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #858585;
                border: none;
                border-left: 2px solid transparent; /* Highlight indicator */
            }
            QPushButton:hover {
                color: #e8e8e8;
            }
            QPushButton:checked {
                color: #ffffff;
                border-left: 2px solid #007acc; /* VS-Code blue */
            }
        """)

class ActivityBar(QWidget):
    """
    Vertical bar on the far left, containing toggle buttons for side docks and center panels.
    """
    toggleBibleDir = Signal(bool)
    toggleStudyOverview = Signal(bool)
    
    openReadingView = Signal()
    openNotesPanel = Signal()
    openOutlinePanel = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(50)
        self.setStyleSheet("background-color: #333333;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # 1. Dock Toggles
        self.btn_bible = ActivityBarButton("B")
        self.btn_bible.setToolTip("Bible Directory")
        self.btn_bible.setChecked(True) # Assume open by default
        self.btn_bible.toggled.connect(self.toggleBibleDir.emit)
        
        self.btn_study = ActivityBarButton("S")
        self.btn_study.setToolTip("Study Overview")
        self.btn_study.setChecked(True)
        self.btn_study.toggled.connect(self.toggleStudyOverview.emit)
        
        # 2. Main View Launchers
        self.btn_read = ActivityBarButton("R")
        self.btn_read.setCheckable(False)
        self.btn_read.setToolTip("Reading View")
        self.btn_read.clicked.connect(lambda: self.openReadingView.emit())
        
        self.btn_notes = ActivityBarButton("N")
        self.btn_notes.setCheckable(False)
        self.btn_notes.setToolTip("Notes Panel")
        self.btn_notes.clicked.connect(lambda: self.openNotesPanel.emit())
        
        self.btn_outline = ActivityBarButton("O")
        self.btn_outline.setCheckable(False)
        self.btn_outline.setToolTip("Outline Panel")
        self.btn_outline.clicked.connect(lambda: self.openOutlinePanel.emit())

        layout.addWidget(self.btn_bible)
        layout.addWidget(self.btn_study)
        
        # Spacer between side docks and center panels
        layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        layout.addWidget(self.btn_read)
        layout.addWidget(self.btn_notes)
        layout.addWidget(self.btn_outline)
        
        # Ensure it doesn't try to stretch horizontally
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
