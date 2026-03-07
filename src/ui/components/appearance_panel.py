from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSlider, 
    QPushButton, QColorDialog, QScrollArea, QGroupBox, QFormLayout,
    QFontComboBox, QDoubleSpinBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase
import src.core.constants as constants

class AppearancePanel(QDialog):
    """
    Pop-out dialog for customizing the reader's appearance:
    Fonts, sizes, colors, and layout.
    """
    settingsChanged = Signal()

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setWindowTitle("Appearance Settings")
        self.resize(320, 500)
        self.setStyleSheet("""
            QDialog { background-color: #222; color: #ddd; }
            QLabel { color: #aaa; font-size: 11px; }
            QGroupBox { border: 1px solid #444; margin-top: 10px; padding-top: 10px; font-weight: bold; color: #eee; }
            QComboBox, QSpinBox, QDoubleSpinBox { background-color: #333; border: 1px solid #555; padding: 4px; color: white; }
            QPushButton { background-color: #444; border: 1px solid #555; padding: 6px; color: white; }
            QPushButton:hover { background-color: #555; }
        """)
        
        layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        content = QWidget()
        self.form = QFormLayout(content)
        self.form.setSpacing(10)
        
        # --- Typography Group ---
        typo_group = QGroupBox("Typography")
        typo_layout = QFormLayout(typo_group)
        
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self.scene.font)
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        typo_layout.addRow("Main Font:", self.font_combo)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(self.scene.font_size)
        self.size_spin.valueChanged.connect(self._on_size_changed)
        typo_layout.addRow("Font Size:", self.size_spin)
        
        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(0.5, 4.0)
        self.spacing_spin.setSingleStep(0.1)
        self.spacing_spin.setValue(self.scene.line_spacing)
        self.spacing_spin.valueChanged.connect(self._on_spacing_changed)
        typo_layout.addRow("Line Spacing:", self.spacing_spin)
        
        self.verse_num_size_spin = QSpinBox()
        self.verse_num_size_spin.setRange(6, 72)
        # We need to add this property to scene or store it in constants
        self.verse_num_size_spin.setValue(getattr(self.scene, 'verse_num_font_size', self.scene.font_size - 4))
        self.verse_num_size_spin.valueChanged.connect(self._on_verse_num_size_changed)
        typo_layout.addRow("Verse Num Size:", self.verse_num_size_spin)
        
        self.verse_mark_size_spin = QSpinBox()
        self.verse_mark_size_spin.setRange(6, 72)
        self.verse_mark_size_spin.setValue(getattr(self.scene, 'verse_mark_size', 18))
        self.verse_mark_size_spin.valueChanged.connect(self._on_verse_mark_size_changed)
        typo_layout.addRow("Verse Mark Size:", self.verse_mark_size_spin)
        
        self.form.addRow(typo_group)
        
        # --- Colors Group ---
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout(color_group)
        
        self.text_color_btn = self._create_color_btn(self.scene.text_color, self._on_text_color_changed)
        color_layout.addRow("Text Color:", self.text_color_btn)
        
        self.bg_color_btn = self._create_color_btn(self.scene.backgroundBrush().color(), self._on_bg_color_changed)
        color_layout.addRow("Background:", self.bg_color_btn)
        
        self.ref_color_btn = self._create_color_btn(self.scene.ref_color, self._on_ref_color_changed)
        color_layout.addRow("Ref Color:", self.ref_color_btn)
        
        self.logical_mark_color_btn = self._create_color_btn(self.scene.logical_mark_color, self._on_logical_mark_color_changed)
        color_layout.addRow("Logical Marks:", self.logical_mark_color_btn)
        
        self.form.addRow(color_group)
        
        # --- Layout Group ---
        layout_group = QGroupBox("Layout")
        layout_layout = QFormLayout(layout_group)
        
        self.side_margin_spin = QSpinBox()
        self.side_margin_spin.setRange(0, 500)
        self.side_margin_spin.setValue(self.scene.side_margin)
        self.side_margin_spin.valueChanged.connect(self._on_margin_changed)
        layout_layout.addRow("Side Margin:", self.side_margin_spin)
        
        self.tab_size_spin = QSpinBox()
        self.tab_size_spin.setRange(10, 200)
        self.tab_size_spin.setValue(self.scene.tab_size)
        self.tab_size_spin.valueChanged.connect(self._on_tab_size_changed)
        layout_layout.addRow("Tab Size (px):", self.tab_size_spin)
        
        self.arrow_opacity_spin = QDoubleSpinBox()
        self.arrow_opacity_spin.setRange(0.0, 1.0)
        self.arrow_opacity_spin.setSingleStep(0.1)
        self.arrow_opacity_spin.setValue(self.scene.arrow_opacity)
        self.arrow_opacity_spin.valueChanged.connect(self._on_arrow_opacity_changed)
        layout_layout.addRow("Arrow Opacity:", self.arrow_opacity_spin)

        self.logical_opacity_spin = QDoubleSpinBox()
        self.logical_opacity_spin.setRange(0.0, 1.0)
        self.logical_opacity_spin.setSingleStep(0.1)
        self.logical_opacity_spin.setValue(getattr(self.scene, 'logical_mark_opacity', 0.5))
        self.logical_opacity_spin.valueChanged.connect(self._on_logical_opacity_changed)
        layout_layout.addRow("Logical Mark Opacity:", self.logical_opacity_spin)

        self.sentence_break_check = QCheckBox()
        self.sentence_break_check.setChecked(getattr(self.scene, 'sentence_break_enabled', False))
        self.sentence_break_check.toggled.connect(self._on_sentence_break_changed)
        layout_layout.addRow("Break at Sentences:", self.sentence_break_check)
        
        self.form.addRow(layout_group)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Apply Button
        apply_btn = QPushButton("Apply All Changes")
        apply_btn.clicked.connect(self.apply_changes)
        layout.addWidget(apply_btn)

    def _create_color_btn(self, initial_color, callback):
        btn = QPushButton()
        btn.setFixedWidth(40)
        self._update_color_btn_style(btn, initial_color)
        btn.clicked.connect(lambda: self._pick_color(btn, callback))
        return btn

    def _update_color_btn_style(self, btn, color):
        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #666;")

    def _pick_color(self, btn, callback):
        color = QColorDialog.getColor(QColor(btn.styleSheet().split(":")[1].split(";")[0].strip()), self)
        if color.isValid():
            self._update_color_btn_style(btn, color)
            callback(color)

    def _on_font_changed(self, font):
        self.scene.target_font_family = font.family()

    def _on_size_changed(self, val):
        self.scene.target_font_size = val

    def _on_spacing_changed(self, val):
        self.scene.target_line_spacing = val

    def _on_verse_num_size_changed(self, val):
        self.scene.target_verse_num_size = val

    def _on_verse_mark_size_changed(self, val):
        self.scene.target_verse_mark_size = val

    def _on_text_color_changed(self, color):
        self.scene.text_color = color

    def _on_bg_color_changed(self, color):
        self.scene.setBackgroundBrush(color)
        self.scene.update()
        self.scene.save_settings()

    def _on_ref_color_changed(self, color):
        self.scene.ref_color = color

    def _on_logical_mark_color_changed(self, color):
        self.scene.logical_mark_color = color

    def _on_margin_changed(self, val):
        self.scene.target_side_margin = val

    def _on_tab_size_changed(self, val):
        self.scene.target_tab_size = val

    def _on_arrow_opacity_changed(self, val):
        self.scene.target_arrow_opacity = val

    def _on_logical_opacity_changed(self, val):
        self.scene.target_logical_mark_opacity = val

    def _on_sentence_break_changed(self, checked):
        self.scene.target_sentence_break_enabled = checked

    def apply_changes(self):
        self.scene.apply_layout_changes()
        self.settingsChanged.emit()
