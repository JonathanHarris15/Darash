from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from src.outline_panel import OutlinePanel

class OutlineEditor(QDialog):
    """
    A standalone dialog for editing a specific outline tree.
    Wraps the OutlinePanel logic into a popup.
    """
    def __init__(self, outline_manager, root_node_id, parent=None):
        super().__init__(parent)
        self.root_node_id = root_node_id
        self.outline_manager = outline_manager
        
        node = outline_manager.get_node(root_node_id)
        title = node.get("title", "Outline Editor") if node else "Outline Editor"
        self.setWindowTitle(f"Outline Editor - {title}")
        self.resize(600, 700)
        
        # Set window flag to keep it on top or behavior like a separate editor
        self.setWindowFlags(self.windowFlags() | Qt.Window)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.panel = OutlinePanel(outline_manager, root_node_id=root_node_id, parent=self)
        layout.addWidget(self.panel)
        
        # We can connect internal signals to external ones if needed
        self.jumpRequested = self.panel.jumpRequested
        self.outlineChanged = self.panel.outlineChanged
        
        # Add a close button at the bottom
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                border-radius: 4px;
                padding: 6px 20px;
                margin: 10px;
            }
            QPushButton:hover { background-color: #555; }
        """)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)
