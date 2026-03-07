from PySide6.QtWidgets import QWidget, QGraphicsView, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QTimer
import re
from src.scene.reader_scene import ReaderScene
from src.ui.components.jump_scrollbar import JumpScrollBar
from src.ui.components.clickable_label import ClickableLabel
from src.core.constants import (
    TEXT_COLOR, OVERLAY_BACKGROUND_COLOR,
    RESIZE_DEBOUNCE_INTERVAL, SELECTION_COLOR
)

class ReaderWidget(QWidget):
    """
    The main container widget for the Bible reader.
    Integrates the GraphicsView, custom scrollbar, HUD, and loading overlay.
    """
    def __init__(self, scene=None, parent=None):
        super().__init__(parent)
        self.scene = scene if scene is not None else ReaderScene()
        
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setFrameShape(QGraphicsView.NoFrame)
        self.view.setFocusPolicy(Qt.StrongFocus)
        self.view.setMouseTracking(True)
        self.view.setStyleSheet("QGraphicsView { outline: none; border: none; background: transparent; }")
        
        # Set selection color on view palette
        palette = self.view.palette()
        palette.setColor(palette.ColorGroup.Active, palette.ColorRole.Highlight, SELECTION_COLOR)
        palette.setColor(palette.ColorGroup.Inactive, palette.ColorRole.Highlight, SELECTION_COLOR)
        self.view.setPalette(palette)
        
        self.scrollbar = JumpScrollBar(Qt.Vertical)
        self.scrollbar.setSingleStep(20)
        
        # HUD Labels & Buttons
        self.ref_label = ClickableLabel(self.view)
        self.ref_label.setCursor(Qt.PointingHandCursor)
        self.ref_label.setToolTip("Click to Bookmark")
        self.ref_label.setStyleSheet(f"background-color: rgba(30, 30, 30, 200); color: {TEXT_COLOR.name()}; padding: 8px 12px; border-radius: 4px; font-size: 14px; font-weight: bold;")
        self.ref_label.hide()

        # --- Professional Loading Overlay ---
        self.overlay = QWidget(self.view)
        self.overlay.setStyleSheet(f"background-color: {OVERLAY_BACKGROUND_COLOR};")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        
        self.loading_title = QLabel("JEHU READER")
        self.loading_title.setStyleSheet("color: white; font-size: 32px; font-weight: bold; letter-spacing: 4px;")
        self.loading_title.setAlignment(Qt.AlignCenter)
        
        self.loading_subtitle = QLabel("Preparing the Holy Scriptures...")
        self.loading_subtitle.setStyleSheet("color: #aaa; font-size: 16px; font-style: italic;")
        self.loading_subtitle.setAlignment(Qt.AlignCenter)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 13px; margin-top: 20px;")
        self.info_label.setAlignment(Qt.AlignCenter)
        
        overlay_layout.addStretch()
        overlay_layout.addWidget(self.loading_title)
        overlay_layout.addWidget(self.loading_subtitle)
        overlay_layout.addWidget(self.info_label)
        overlay_layout.addStretch()
        
        self.overlay.hide()
        
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(RESIZE_DEBOUNCE_INTERVAL)
        self.resize_timer.timeout.connect(self.apply_delayed_resize)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)
        layout.addWidget(self.scrollbar)
        
        # Connections
        self.scene.layoutChanged.connect(self.update_scrollbar_range)
        self.scene.scrollChanged.connect(self.update_scrollbar_value)
        self.scene.currentReferenceChanged.connect(self.update_ref_label)
        self.scene.layoutStarted.connect(self.show_generic_loading)
        self.scene.settingsPreview.connect(self.show_settings_loading)
        self.scene.layoutFinished.connect(self.hide_loading)
        self.scrollbar.valueChanged.connect(self.scene.set_scroll_y)
        self.ref_label.clicked.connect(self._on_ref_label_clicked)
        
        self.total_count = len(self.scene.loader.flat_verses)
        self.scrollbar.setMaximum(self.total_count)

    def _on_ref_label_clicked(self):
        ref = self.ref_label.text()
        if ref:
            # Parse ref "Book Chap:Verse"
            match = re.match(r"(.*) (\d+):(\d+)", ref)
            if match:
                book, chap, verse = match.groups()
                self.scene.study_manager.add_bookmark(book, chap, verse)
                self.scene.bookmarksUpdated.emit()

    def update_scrollbar_range(self, total_count: int) -> None:
        self.total_count = total_count
        self._recalc_scrollbar()

    def update_scrollbar_value(self, value: int) -> None:
        self.scrollbar.blockSignals(True)
        self.scrollbar.setValue(value)
        self.scrollbar.blockSignals(False)
    
    def update_ref_label(self, text: str) -> None:
        self.ref_label.setText(text)
        self.ref_label.adjustSize()
        self.ref_label.show()
        self.reposition_ref_label()

    def reposition_ref_label(self) -> None:
        margin = 20
        if self.ref_label.isVisible():
            self.ref_label.move(margin, self.view.height() - self.ref_label.height() - margin)

    def show_generic_loading(self):
        self.loading_subtitle.setText("Recalculating Layout...")
        self.info_label.setText("")
        self.show_loading()

    def show_settings_loading(self, font_size: int, line_spacing: float) -> None:
        self.loading_subtitle.setText("Updating Typography...")
        self.info_label.setText(f"Font: {font_size}px  |  Spacing: {line_spacing:.1f}")
        self.show_loading()

    def show_loading(self):
        self.overlay.resize(self.view.size())
        self.overlay.show()

    def hide_loading(self) -> None:
        self.overlay.hide()

    def _recalc_scrollbar(self) -> None:
        self.scrollbar.setMaximum(self.total_count)
        self.scrollbar.setPageStep(10) # 10 verses per page step


    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        
        # Show loading screen immediately when resize starts
        self.loading_subtitle.setText("Adjusting to Window Size...")
        self.info_label.setText("")
        self.show_loading()
        
        self.reposition_ref_label()
        
        # Reset the timer - layout recalculation will only happen 200ms after the last resize event
        self.resize_timer.start()

    def apply_delayed_resize(self) -> None:
        # Get actual viewport rect
        rect = self.view.viewport().rect()
        if rect.width() <= 0:
            self.hide_loading()
            return
            
        # This will trigger scene.recalculate_layout if width changed
        if abs(rect.width() - self.scene.last_width) > 2:
            self.scene.setSceneRect(rect)
            # hide_loading will be called by layoutFinished signal
        else:
            self.hide_loading()
            
        self._recalc_scrollbar()
