from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QDialogButtonBox, QComboBox, QFormLayout, QTextEdit
)
from PySide6.QtCore import Qt
from src.ui.components.spellcheck_title_edit import SpellcheckTitleEdit

class OutlineDialog(QDialog):
    """
    Dialog for creating or editing an outline/section.
    """
    def __init__(self, parent=None, title="Book Outline", start_ref="", end_ref=""):
        super().__init__(parent)
        self.setWindowTitle("Create Outline")
        self.setModal(True)
        self.resize(400, 180)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("Enter outline title...")
        form_layout.addRow("Title:", self.title_edit)
        
        self.start_ref_edit = QLineEdit(start_ref)
        self.start_ref_edit.setPlaceholderText("e.g. Genesis 1:1")
        form_layout.addRow("Start Ref:", self.start_ref_edit)
        
        self.end_ref_edit = QLineEdit(end_ref)
        self.end_ref_edit.setPlaceholderText("e.g. Genesis 1:31")
        form_layout.addRow("End Ref:", self.end_ref_edit)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_data(self):
        return {
            "title": self.title_edit.text(),
            "start_ref": self.start_ref_edit.text(),
            "end_ref": self.end_ref_edit.text()
        }
