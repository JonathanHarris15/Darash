from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, 
    QPushButton, QLabel, QFrame, QCheckBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon

class TranslationSelector(QFrame):
    """
    Dropdown-style panel for selecting primary and interlinear translations.
    Supports drag-and-drop reordering and visibility toggling.
    """
    settingsChanged = Signal()

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setFrameShape(QFrame.StyledPanel)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedWidth(250)
        self.setStyleSheet("""
            TranslationSelector {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 4px;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #3d3d3d;
            }
            QLabel {
                color: #ddd;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout(self)
        
        header = QLabel("Translations")
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.model().rowsMoved.connect(self._on_reorder)
        layout.addWidget(self.list_widget)

        # Bottom info
        info = QLabel("Drag to reorder. Top is Primary.")
        info.setStyleSheet("font-size: 10px; font-weight: normal; color: #888;")
        layout.addWidget(info)

        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        
        primary = self.scene.primary_translation
        interlinear = self.scene.enabled_interlinear # This is an ordered list
        
        # Get actual available translations from filesystem via loader
        available = self.scene.loader.get_available_translations()
        
        # Order: Primary first, then Interlinear, then the rest
        ordered = [primary] + [t for t in interlinear if t != primary]
        for t in available:
            if t not in ordered:
                ordered.append(t)

        for i, trans_id in enumerate(ordered):
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.UserRole, trans_id) # Store ID in item data for robust reordering
            
            widget = QWidget()
            item_layout = QHBoxLayout(widget)
            item_layout.setContentsMargins(5, 2, 5, 2)
            
            check = QCheckBox(trans_id)
            is_checked = (trans_id == primary or trans_id in interlinear)
            check.setChecked(is_checked)
            
            # Primary is always "enabled" visually and can't be unchecked
            if trans_id == primary:
                check.setEnabled(False)
                check.setStyleSheet("color: #64c8ff;") # Highlight primary
            
            check.blockSignals(True)
            check.stateChanged.connect(lambda state, t=trans_id: self._on_toggle(t, state))
            check.blockSignals(False)
            
            item_layout.addWidget(check)
            item_layout.addStretch()
            
            handle = QLabel("☰")
            handle.setStyleSheet("color: #555;")
            item_layout.addWidget(handle)
            
            widget.setLayout(item_layout)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _on_toggle(self, trans_id, state):
        self._update_settings_from_ui()

    def _on_reorder(self, *args):
        self._update_settings_from_ui()
        # Delay refresh slightly to allow QListWidget to finish its internal move
        from PySide6.QtCore import QTimer
        QTimer.singleShot(10, self._refresh_list)

    def _update_settings_from_ui(self):
        """Re-derives all translation settings from the current list widget state."""
        new_order = []
        enabled_list = []
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            trans_id = item.data(Qt.UserRole)
            if not trans_id: continue
            
            new_order.append(trans_id)
            
            # Check if it's enabled via the widget (if it still exists)
            widget = self.list_widget.itemWidget(item)
            if widget:
                check = widget.findChild(QCheckBox)
                if check and check.isChecked():
                    enabled_list.append(trans_id)
            else:
                # Fallback: if widget is gone during reorder, 
                # keep its enabled status from existing scene settings
                if trans_id == self.scene.primary_translation or trans_id in self.scene.enabled_interlinear:
                    enabled_list.append(trans_id)

        if not new_order: return

        # Top item is always the primary
        new_primary = new_order[0]
        
        # New enabled interlinear follows the list order, excluding primary
        new_interlinear = [t for t in enabled_list if t != new_primary]
        
        # Update target settings in scene
        self.scene.target_primary_translation = new_primary
        self.scene.target_enabled_interlinear = new_interlinear
        self.settingsChanged.emit()
