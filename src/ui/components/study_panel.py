from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStyle, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from src.ui.components.outline_dialog import OutlineDialog
from src.ui.components.study_tree import StudyTreeWidget
from src.ui.theme import Theme

class StudyPanel(QWidget):
    jumpRequested = Signal(str, str, str) # book, chap, verse
    noteOpenRequested = Signal(str, str) # note_key, ref
    outlineOpenRequested = Signal(str) # node_id
    outlineDeleted = Signal(str) # node_id
    activeOutlineChanged = Signal(str) # Signal when entering/exiting outline mode
    dataChanged = Signal() # Signal to refresh view after edits

    def __init__(self, study_manager, symbol_manager, parent=None):
        super().__init__(parent)
        self.study_manager = study_manager
        self.symbol_manager = symbol_manager
        self.active_outline_id = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.tree = StudyTreeWidget(study_manager, symbol_manager)
        self.tree.jumpRequested.connect(self.jumpRequested.emit)
        self.tree.noteOpenRequested.connect(self.noteOpenRequested.emit)
        self.tree.outlineOpenRequested.connect(self._on_outline_open_requested)
        self.tree.outlineDeleted.connect(self.outlineDeleted.emit)
        self.tree.dataChanged.connect(self.dataChanged.emit)
        layout.addWidget(self.tree)

        # --- Active Outline Status Bar ---
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet(f"""
            QFrame {{ background-color: {Theme.BG_TERTIARY}; border: 1px solid {Theme.BORDER_DEFAULT}; border-radius: 4px; margin-top: 5px; }}
        """)
        self.status_layout = QHBoxLayout(self.status_bar)
        self.status_layout.setContentsMargins(8, 4, 8, 4)
        self.status_label = QLabel("Editing: Outline Name")
        self.status_label.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-weight: bold; font-size: 12px;")
        self.status_layout.addWidget(self.status_label)
        self.close_status_btn = QPushButton("✕")
        self.close_status_btn.setFixedSize(20, 20)
        self.close_status_btn.setStyleSheet(f"""
            QPushButton {{ background-color: {Theme.BG_TERTIARY}; color: {Theme.TEXT_PRIMARY}; border: 1px solid {Theme.BORDER_LIGHT}; border-radius: 10px; font-size: 10px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {Theme.BORDER_LIGHT}; }}
        """)
        self.close_status_btn.clicked.connect(lambda: self.set_active_outline(None))
        self.status_layout.addWidget(self.close_status_btn)
        self.status_bar.hide()
        layout.addWidget(self.status_bar)
        
        # Bottom Action Menu
        actions_layout = QHBoxLayout(); actions_layout.setContentsMargins(0, 5, 0, 0)
        self.add_note_btn = QPushButton()
        self.add_note_btn.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.add_note_btn.setToolTip("New Standalone Note")
        self.add_note_btn.clicked.connect(lambda: self.tree._add_standalone_note(""))
        self.add_outline_btn = QPushButton()
        self.add_outline_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.add_outline_btn.setToolTip("New Outline")
        self.add_outline_btn.clicked.connect(self._add_outline)
        
        btn_style = f"""
            QPushButton {{ background-color: {Theme.BG_TERTIARY}; border: 1px solid {Theme.BORDER_LIGHT}; border-radius: 4px; padding: 8px; }}
            QPushButton:hover {{ background-color: {Theme.BORDER_LIGHT}; border-color: {Theme.BORDER_DEFAULT}; }}
            QPushButton:pressed {{ background-color: {Theme.BG_PRIMARY}; }}
        """
        self.add_note_btn.setStyleSheet(btn_style); self.add_outline_btn.setStyleSheet(btn_style)
        actions_layout.addWidget(self.add_note_btn); actions_layout.addWidget(self.add_outline_btn)
        layout.addLayout(actions_layout)
        self.dataChanged.connect(self.refresh)
        self.refresh()

    def _add_outline(self):
        dialog = OutlineDialog(self, title="Book Outline")
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                node = self.study_manager.outline_manager.create_outline(data["start_ref"], data["end_ref"], data["title"])
                self.refresh(); self.dataChanged.emit(); self.set_active_outline(node["id"]); self.outlineOpenRequested.emit(node["id"])

    def _on_outline_open_requested(self, node_id):
        self.set_active_outline(node_id); self.outlineOpenRequested.emit(node_id)

    def refresh(self): self.tree.refresh()

    def set_active_outline(self, outline_id, emit_signal=True):
        self.active_outline_id = outline_id
        if outline_id:
            node = self.study_manager.outline_manager.get_node(outline_id)
            title = node.get("title", "Unknown") if node else "Unknown"
            self.status_label.setText(f"Editing: {title}"); self.status_bar.show()
        else: self.status_bar.hide()
        if emit_signal: self.activeOutlineChanged.emit(outline_id or "")
