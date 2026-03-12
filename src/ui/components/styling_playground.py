from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, 
    QPushButton, QLineEdit, QTextEdit, QComboBox, QFrame, QGridLayout
)
from PySide6.QtCore import Qt
from src.core.theme import Theme

class StylingPlaygroundPanel(QWidget):
    """
    A panel that showcases all theme tokens and component styles for rapid UI iteration.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)

        # Scroll Area for the whole content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(25)

        # 1. Colors Section
        layout.addWidget(self._create_header("Color Palette"))
        layout.addLayout(self._create_color_grid())

        # 2. Semantic Colors Section
        layout.addWidget(self._create_header("Semantic Colors"))
        layout.addLayout(self._create_semantic_colors())

        # 3. Highlight Colors Section
        layout.addWidget(self._create_header("Highlight Colors"))
        layout.addLayout(self._create_highlight_grid())

        # 3.1 Logical Marks Section
        layout.addWidget(self._create_header("Logical Marks"))
        layout.addLayout(self._create_logical_marks_section())

        # 4. Typography Section
        layout.addWidget(self._create_header("Typography"))
        layout.addWidget(self._create_typography_samples())

        # 5. Component Samples Section
        layout.addWidget(self._create_header("Component Samples"))
        layout.addWidget(self._create_component_samples())

        # 6. Dictionary of Options (Quick Reference)
        layout.addWidget(self._create_header("Dictionary of Options"))
        layout.addWidget(self._create_dictionary_reference())

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_header(self, text):
        header = QLabel(text)
        header.setStyleSheet(f"font-size: {Theme.SIZE_CHAPTER}px; font-weight: bold; color: {Theme.ACCENT_PRIMARY}; border-bottom: 2px solid {Theme.BORDER_DEFAULT}; padding-bottom: 5px;")
        return header

    def _create_color_grid(self):
        grid = QGridLayout()
        colors = [
            ("BG_PRIMARY", Theme.BG_PRIMARY),
            ("BG_SECONDARY", Theme.BG_SECONDARY),
            ("BG_TERTIARY", Theme.BG_TERTIARY),
            ("TEXT_PRIMARY", Theme.TEXT_PRIMARY),
            ("TEXT_SECONDARY", Theme.TEXT_SECONDARY),
            ("TEXT_MUTED", Theme.TEXT_MUTED),
            ("ACCENT_PRIMARY", Theme.ACCENT_PRIMARY),
            ("ACCENT_HOVER", Theme.ACCENT_HOVER),
            ("ACCENT_GOLD", Theme.ACCENT_GOLD),
            ("BORDER_DEFAULT", Theme.BORDER_DEFAULT),
            ("BORDER_LIGHT", Theme.BORDER_LIGHT),
        ]
        
        col_count = 3
        for i, (name, val) in enumerate(colors):
            row = i // col_count
            col = i % col_count
            grid.addWidget(self._create_color_swatch(name, val), row, col)
        
        return grid

    def _create_color_swatch(self, name, hex_val):
        swatch_container = QWidget()
        vbox = QVBoxLayout(swatch_container)
        
        box = QFrame()
        box.setFixedSize(60, 40)
        box.setStyleSheet(f"background-color: {hex_val}; border: 1px solid {Theme.BORDER_DEFAULT}; border-radius: 4px;")
        
        label = QLabel(name)
        label.setStyleSheet(f"font-size: {Theme.SIZE_UI_SMALL}px; color: {Theme.TEXT_SECONDARY};")
        
        val_label = QLabel(hex_val)
        val_label.setStyleSheet(f"font-size: {Theme.SIZE_UI_TINY}px; color: {Theme.TEXT_MUTED};")
        
        vbox.addWidget(box, alignment=Qt.AlignCenter)
        vbox.addWidget(label, alignment=Qt.AlignCenter)
        vbox.addWidget(val_label, alignment=Qt.AlignCenter)
        return swatch_container

    def _create_semantic_colors(self):
        hbox = QHBoxLayout()
        semantics = [
            ("HUD_BG", Theme.HUD_BG),
            ("OVERLAY_BG", Theme.OVERLAY_BG),
            ("SELECTION_BG", Theme.SELECTION_BG),
            ("SEARCH_HIGHLIGHT", Theme.SEARCH_HIGHLIGHT),
        ]
        for name, val in semantics:
            hbox.addWidget(self._create_color_swatch(name, val))
        return hbox

    def _create_highlight_grid(self):
        grid = QGridLayout()
        for i, (name, val) in enumerate(Theme.HIGHLIGHT_COLORS.items()):
            grid.addWidget(self._create_color_swatch(name, val), 0, i)
        return grid

    def _create_logical_marks_section(self):
        hbox = QHBoxLayout()
        for name, char in Theme.LOGICAL_MARKS.items():
            container = QWidget()
            vbox = QVBoxLayout(container)
            
            label = QLabel(char)
            label.setStyleSheet(f"font-size: 30px; color: {Theme.LOGICAL_MARK_COLOR};")
            
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-size: {Theme.SIZE_UI_TINY}px; color: {Theme.TEXT_MUTED};")
            
            vbox.addWidget(label, alignment=Qt.AlignCenter)
            vbox.addWidget(name_label, alignment=Qt.AlignCenter)
            hbox.addWidget(container)
        
        # Add a swatch for the mark color itself
        hbox.addWidget(self._create_color_swatch("MARK_COLOR", Theme.LOGICAL_MARK_COLOR))
        return hbox

    def _create_typography_samples(self):
        container = QWidget()
        vbox = QVBoxLayout(container)
        
        samples = [
            ("Header (36px)", Theme.SIZE_HEADER, Theme.FONT_UI),
            ("Chapter (24px)", Theme.SIZE_CHAPTER, Theme.FONT_UI),
            ("Reader Default (18px)", Theme.SIZE_READER_DEFAULT, Theme.FONT_READER),
            ("UI Default (14px)", Theme.SIZE_UI_DEFAULT, Theme.FONT_UI),
            ("UI Small (12px)", Theme.SIZE_UI_SMALL, Theme.FONT_UI),
            ("UI Tiny (10px)", Theme.SIZE_UI_TINY, Theme.FONT_UI),
            ("Mono / Consolas", Theme.SIZE_UI_DEFAULT, Theme.FONT_MONO),
        ]
        
        for text, size, font in samples:
            label = QLabel(f"{text}: The quick brown fox jumps over the lazy dog.")
            label.setStyleSheet(f"font-family: '{font}'; font-size: {size}px; color: {Theme.TEXT_PRIMARY};")
            vbox.addWidget(label)
            
        return container

    def _create_component_samples(self):
        container = QWidget()
        grid = QGridLayout(container)
        
        # Row 1: Buttons
        btn_normal = QPushButton("Normal Button")
        btn_disabled = QPushButton("Disabled Button")
        btn_disabled.setEnabled(False)
        grid.addWidget(QLabel("Buttons:"), 0, 0)
        grid.addWidget(btn_normal, 0, 1)
        grid.addWidget(btn_disabled, 0, 2)
        
        # Row 2: Inputs
        line_edit = QLineEdit()
        line_edit.setPlaceholderText("QLineEdit placeholder...")
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("QTextEdit placeholder...")
        text_edit.setMaximumHeight(80)
        grid.addWidget(QLabel("Inputs:"), 1, 0)
        grid.addWidget(line_edit, 1, 1, 1, 2)
        grid.addWidget(text_edit, 2, 1, 1, 2)
        
        # Row 3: Combo
        combo = QComboBox()
        combo.addItems(["Option A", "Option B", "Option C"])
        grid.addWidget(QLabel("ComboBox:"), 3, 0)
        grid.addWidget(combo, 3, 1)
        
        return container

    def _create_dictionary_reference(self):
        container = QWidget()
        vbox = QVBoxLayout(container)
        
        # Gather all tokens from Theme class
        tokens = []
        for attr in dir(Theme):
            if attr.isupper() and not attr.startswith("_"):
                val = getattr(Theme, attr)
                if not callable(val):
                    tokens.append((attr, str(val)))
        
        tokens.sort()
        
        for name, val in tokens:
            row = QWidget()
            hbox = QHBoxLayout(row)
            hbox.setContentsMargins(0, 0, 0, 0)
            
            name_label = QLabel(name)
            name_label.setStyleSheet(f"font-family: '{Theme.FONT_MONO}'; color: {Theme.ACCENT_PRIMARY};")
            
            val_label = QLabel(val)
            val_label.setStyleSheet(f"font-family: '{Theme.FONT_MONO}'; color: {Theme.TEXT_SECONDARY};")
            val_label.setAlignment(Qt.AlignRight)
            
            hbox.addWidget(name_label)
            hbox.addStretch()
            hbox.addWidget(val_label)
            vbox.addWidget(row)
            
        return container
