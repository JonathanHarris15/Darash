from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, 
    QLabel, QFileDialog, QSlider, QTreeWidgetItem, QGridLayout,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
import os

class SymbolDialog(QDialog):
    symbolsChanged = Signal()

    def __init__(self, symbol_manager, parent=None):
        super().__init__(parent)
        self.manager = symbol_manager
        self.setWindowTitle("Symbols Library & Bindings")
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # --- Top Section: Opacity ---
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Global Symbol Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(int(self.manager.get_opacity() * 100))
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        self.opacity_val_label = QLabel(f"{self.opacity_slider.value()}%")
        opacity_layout.addWidget(self.opacity_val_label)
        layout.addLayout(opacity_layout)
        
        # --- Middle Section: Library and Bindings ---
        middle_layout = QHBoxLayout()
        
        # Library Tree
        lib_layout = QVBoxLayout()
        lib_layout.addWidget(QLabel("Library (Grouped by Type):"))
        self.lib_tree = QTreeWidget()
        self.lib_tree.setHeaderHidden(True)
        self.lib_tree.setIconSize(QPixmap(32, 32).size())
        lib_layout.addWidget(self.lib_tree)
        
        add_btn = QPushButton("Add to Library...")
        add_btn.clicked.connect(self._add_to_library)
        lib_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove from Library")
        remove_btn.clicked.connect(self._remove_from_library)
        lib_layout.addWidget(remove_btn)
        
        middle_layout.addLayout(lib_layout, 2)
        
        # Bindings Grid
        bind_layout = QVBoxLayout()
        bind_layout.addWidget(QLabel("Number Bindings (1-9):"))
        self.grid = QGridLayout()
        self.binding_labels = {} # number: label
        
        for i in range(1, 10):
            num_str = str(i)
            self.grid.addWidget(QLabel(f"{num_str}:"), i-1, 0)
            
            label = QLabel("None")
            label.setStyleSheet("border: 1px solid #555; padding: 2px;")
            self.binding_labels[num_str] = label
            self.grid.addWidget(label, i-1, 1)
            
            bind_btn = QPushButton("Set")
            bind_btn.setFixedWidth(40)
            bind_btn.clicked.connect(lambda checked=False, n=num_str: self._bind_selected(n))
            self.grid.addWidget(bind_btn, i-1, 2)
            
            clear_btn = QPushButton("X")
            clear_btn.setFixedWidth(30)
            clear_btn.clicked.connect(lambda checked=False, n=num_str: self._clear_binding(n))
            self.grid.addWidget(clear_btn, i-1, 3)
            
        bind_layout.addLayout(self.grid)
        bind_layout.addStretch()
        middle_layout.addLayout(bind_layout, 3)
        
        layout.addLayout(middle_layout)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self._refresh_library()
        self._refresh_bindings()

    def _refresh_library(self):
        self.lib_tree.clear()
        symbols = self.manager.list_symbols()
        
        for s_file in sorted(symbols):
            # Skip if it's not an image file
            if not s_file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                continue
            
            # Use the manager to get the display name
            display_name = self.manager.get_symbol_name(s_file)
            
            # Migration logic (if name is missing, use the old 'group type' logic)
            if s_file not in self.manager.config.get("names", {}):
                parts = s_file.replace('_', '-').split('-')
                if len(parts) > 1:
                    display_name = parts[0].title()
                else:
                    display_name = os.path.splitext(s_file)[0]
                # Store the migrated name
                self.manager.config["names"][s_file] = display_name
                self.manager.save_config()

            item = QTreeWidgetItem(self.lib_tree, [display_name])
            path = self.manager.get_symbol_path(s_file)
            item.setIcon(0, QIcon(path))
            item.setData(0, Qt.UserRole, s_file)

    def _refresh_bindings(self):
        for n, label in self.binding_labels.items():
            bound = self.manager.get_binding(n)
            if bound:
                # Show the display name from the manager
                label.setText(self.manager.get_symbol_name(bound))
            else:
                label.setText("None")

    def _add_to_library(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            from PySide6.QtWidgets import QInputDialog
            default_name = os.path.splitext(os.path.basename(path))[0]
            name, ok = QInputDialog.getText(self, "Symbol Name", "Enter a name for this symbol:", text=default_name)
            if ok and name:
                self.manager.add_symbol_to_library(path, name)
                self._refresh_library()

    def _remove_from_library(self):
        current = self.lib_tree.currentItem()
        if not current or current.childCount() > 0: # Don't delete groups
            return
            
        symbol_file = current.data(0, Qt.UserRole)
        display_name = current.text(0)
        
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                     f"Are you sure you want to delete '{display_name}' from the library?\n"
                                     "This will also clear any number bindings for this symbol.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.manager.remove_symbol_from_library(symbol_file)
            self._refresh_library()
            self._refresh_bindings()
            self.symbolsChanged.emit()

    def _bind_selected(self, number):
        current = self.lib_tree.currentItem()
        if current and current.childCount() == 0:
            symbol_file = current.data(0, Qt.UserRole)
            self.manager.bind_symbol(number, symbol_file)
            self._refresh_bindings()
            self.symbolsChanged.emit()

    def _clear_binding(self, number):
        self.manager.bind_symbol(number, None)
        self._refresh_bindings()
        self.symbolsChanged.emit()

    def _on_opacity_changed(self, val):
        opacity = val / 100.0
        self.manager.set_opacity(opacity)
        self.opacity_val_label.setText(f"{val}%")
        self.symbolsChanged.emit()
