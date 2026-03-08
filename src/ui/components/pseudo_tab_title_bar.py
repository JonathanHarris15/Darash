from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class PseudoTabTitleBar(QWidget):
    def __init__(self, title, dock, main_window):
        super().__init__()
        self.dock = dock
        self.main_window = main_window
        self.is_pseudo_tab = True
        
        self.setFixedHeight(30)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.tab = QWidget()
        self.tab.setObjectName("PseudoTab")
        self.tab.setStyleSheet("""
            QWidget#PseudoTab {
                background-color: palette(window);
                border: 1px solid palette(dark);
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-top: 5px;
            }
        """)
        tab_layout = QHBoxLayout(self.tab)
        tab_layout.setContentsMargins(10, 2, 8, 2)
        tab_layout.setSpacing(8)
        
        self.label = QLabel(title)
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet("""
            QPushButton { 
                border: none; 
                font-weight: bold; 
                background: transparent; 
                border-radius: 8px;
            }
            QPushButton:hover { 
                background-color: #c42b1c; 
                color: white; 
            }
        """)
        self.close_btn.clicked.connect(dock.close)
        
        tab_layout.addWidget(self.label)
        tab_layout.addWidget(self.close_btn)
        
        layout.addWidget(self.tab)
        layout.addStretch()
