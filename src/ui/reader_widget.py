from PySide6.QtWidgets import QWidget, QGraphicsView, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt, QTimer, QPointF
import re
from src.scene.reader_scene import ReaderScene
from src.ui.components.jump_scrollbar import JumpScrollBar
from src.ui.components.clickable_label import ClickableLabel
from src.ui.components.mark_popup import MarkPopup
from src.ui.components.suggested_symbols_dialog import SuggestedSymbolsDialog
from src.ui.components.outline_dialog import OutlineDialog
from src.ui.components.strongs_ui import StrongsTooltip, StrongsVerboseDialog
from src.core.theme import Theme
from src.core.constants import RESIZE_DEBOUNCE_INTERVAL

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
        self.view.setStyleSheet(f"QGraphicsView {{ outline: none; border: none; background: {Theme.BG_PRIMARY}; }}")
        
        # Set selection color on view palette
        palette = self.view.palette()
        palette.setColor(palette.ColorGroup.Active, palette.ColorRole.Highlight, Theme.color("SELECTION_BG"))
        palette.setColor(palette.ColorGroup.Inactive, palette.ColorRole.Highlight, Theme.color("SELECTION_BG"))
        self.view.setPalette(palette)
        
        self.scrollbar = JumpScrollBar(Qt.Vertical)
        self.scrollbar.setSingleStep(20)
        
        # HUD Labels & Buttons
        self.ref_label = ClickableLabel(self.view)
        self.ref_label.setCursor(Qt.PointingHandCursor)
        self.ref_label.setToolTip("Click to Bookmark")
        self.ref_label.setStyleSheet(f"background-color: {Theme.HUD_BG}; color: {Theme.ACCENT_PRIMARY}; padding: 8px 12px; border-radius: 4px; font-size: 14px; font-weight: bold;")
        self.ref_label.hide()

        # UI Components
        self.mark_popup = MarkPopup(self)
        self.strongs_tooltip = StrongsTooltip(self)
        
        # --- Professional Loading Overlay ---
        self.overlay = QWidget(self.view)
        self.overlay.setStyleSheet(f"background-color: {Theme.OVERLAY_BG};")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        
        self.loading_title = QLabel("JEHU READER")
        self.loading_title.setStyleSheet(f"color: {Theme.TEXT_PRIMARY}; font-size: 32px; font-weight: bold; letter-spacing: 4px;")
        self.loading_title.setAlignment(Qt.AlignCenter)
        
        self.loading_subtitle = QLabel("Preparing the Holy Scriptures...")
        self.loading_subtitle.setStyleSheet(f"color: {Theme.TEXT_SECONDARY}; font-size: 16px; font-style: italic;")
        self.loading_subtitle.setAlignment(Qt.AlignCenter)
        
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 13px; margin-top: 20px;")
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
        
        # Fallback timer to ensure loading screen hides even if layout signals are missed
        self.fallback_hide_timer = QTimer(self)
        self.fallback_hide_timer.setSingleShot(True)
        self.fallback_hide_timer.setInterval(2000)
        self.fallback_hide_timer.timeout.connect(self.hide_loading)
        
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
        
        # UI Signals from Scene
        self.scene.showMarkPopup.connect(self._on_show_mark_popup)
        self.scene.showSuggestedSymbols.connect(self._on_show_suggested_symbols)
        self.scene.showOutlineDialog.connect(self._on_show_outline_dialog)
        self.scene.showStrongsTooltip.connect(self._on_show_strongs_tooltip)
        self.scene.showStrongsVerboseDialog.connect(self._on_show_strongs_verbose_dialog)
        
        # MarkPopup Connections
        self.mark_popup.markSelected.connect(self.scene.interaction_manager.on_mark_selected)
        self.mark_popup.addNoteRequested.connect(self.scene.interaction_manager.on_add_note_requested)
        self.mark_popup.addBookmarkRequested.connect(self.scene.interaction_manager.on_add_bookmark_requested)
        self.mark_popup.createOutlineRequested.connect(self.scene.outline_manager.create_outline_from_selection)
        
        self.total_count = len(self.scene.loader.flat_verses)
        self.scrollbar.setMaximum(self.total_count)

    def _on_show_mark_popup(self, pos, ref):
        self.mark_popup.show_at(pos.toPoint() if isinstance(pos, QPointF) else pos)

    def _on_show_suggested_symbols(self, top_words, heading_text):
        dialog = SuggestedSymbolsDialog(top_words, heading_text, self)
        dialog.exec()

    def _on_show_outline_dialog(self, start_ref, end_ref):
        dialog = OutlineDialog(self, start_ref=start_ref, end_ref=end_ref)
        if dialog.exec():
            data = dialog.get_data()
            if data["title"]:
                self.scene.outline_manager.create_outline(data["start_ref"], data["end_ref"], data["title"])

    def _on_show_strongs_tooltip(self, pos, sn, entry):
        if entry:
            self.strongs_tooltip.show_entry(sn, entry, pos.toPoint() if isinstance(pos, QPointF) else pos)
        else:
            self.strongs_tooltip.hide()

    def _on_show_strongs_verbose_dialog(self, sn, entry, usages):
        dialog = StrongsVerboseDialog(sn, entry, usages, self)
        dialog.jumpRequested.connect(self.scene.jump_to)
        dialog.show()

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
        self.fallback_hide_timer.start()

    def hide_loading(self) -> None:
        self.overlay.hide()
        self.fallback_hide_timer.stop()

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
