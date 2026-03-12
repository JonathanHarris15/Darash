from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import QRectF
from src.core.constants import (
    OT_BOOKS, NT_BOOKS,
    SCROLL_SENSITIVITY, RESIZE_DEBOUNCE_INTERVAL,
    LAYOUT_DEBOUNCE_INTERVAL, VERSE_NUMBER_RESERVED_WIDTH
)
from src.core.theme import Theme

class SceneSettingsManager:
    """
    Manages scene typography, margins, and persistent settings.
    """
    def __init__(self, scene):
        self.scene = scene

    def load_settings(self):
        scene = self.scene
        settings = scene.study_manager.data.get("settings", {})
        scene.font_size = settings.get("font_size", Theme.SIZE_READER_DEFAULT)
        scene.line_spacing = settings.get("line_spacing", 1.5)
        scene.font_family = settings.get("font_family", Theme.FONT_READER)
        scene.verse_num_font_size = settings.get("verse_num_size", scene.font_size - 4)
        scene.side_margin = settings.get("side_margin", 40)
        scene.tab_size = settings.get("tab_size", 40)
        scene.arrow_opacity = settings.get("arrow_opacity", 0.6)
        scene.verse_mark_size = settings.get("verse_mark_size", 18)
        scene.logical_mark_opacity = settings.get("logical_mark_opacity", 0.5)
        scene.sentence_break_enabled = settings.get("sentence_break_enabled", False)
        scene.primary_translation = settings.get("primary_translation", "ESV")
        scene.enabled_interlinear = settings.get("enabled_interlinear", [])
        
        scene.target_font_size = scene.font_size
        scene.target_line_spacing = scene.line_spacing
        scene.target_font_family = scene.font_family
        scene.target_verse_num_size = scene.verse_num_font_size
        scene.target_side_margin = scene.side_margin
        scene.target_tab_size = scene.tab_size
        scene.target_arrow_opacity = scene.arrow_opacity
        scene.target_verse_mark_size = scene.verse_mark_size
        scene.target_logical_mark_opacity = scene.logical_mark_opacity
        scene.target_sentence_break_enabled = scene.sentence_break_enabled
        
        # Initialize target settings to match current settings
        scene.target_primary_translation = scene.primary_translation
        scene.target_enabled_interlinear = list(scene.enabled_interlinear)

    def save_settings(self):
        scene = self.scene
        settings = scene.study_manager.data["settings"]
        settings["font_size"] = scene.font_size
        settings["line_spacing"] = scene.line_spacing
        settings["font_family"] = scene.font_family
        settings["verse_num_size"] = scene.verse_num_font_size
        settings["side_margin"] = scene.side_margin
        settings["tab_size"] = scene.tab_size
        settings["arrow_opacity"] = scene.arrow_opacity
        settings["verse_mark_size"] = scene.verse_mark_size
        settings["logical_mark_opacity"] = scene.logical_mark_opacity
        settings["sentence_break_enabled"] = scene.sentence_break_enabled
        settings["primary_translation"] = scene.primary_translation
        settings["enabled_interlinear"] = scene.enabled_interlinear
        
        settings["text_color"] = scene.text_color.name()
        settings["ref_color"] = scene.ref_color.name()
        settings["logical_mark_color"] = scene.logical_mark_color.name()
        settings["bg_color"] = scene.backgroundBrush().color().name()
        scene.study_manager.save_data()

    def update_fonts(self):
        scene = self.scene
        scene.font = QFont(scene.font_family, scene.font_size)
        scene.header_font = QFont(Theme.FONT_UI, Theme.SIZE_HEADER, QFont.Bold)
        scene.chapter_font = QFont(Theme.FONT_UI, Theme.SIZE_CHAPTER, QFont.Bold)
        scene.verse_num_font = QFont(scene.font_family, scene.verse_num_font_size)
        scene.verse_mark_font = QFont(scene.font_family, scene.verse_mark_size)

    def apply_layout_changes(self):
        scene = self.scene
        scene.font_size = scene.target_font_size
        scene.line_spacing = scene.target_line_spacing
        scene.font_family = scene.target_font_family
        scene.verse_num_font_size = scene.target_verse_num_size
        scene.side_margin = scene.target_side_margin
        scene.tab_size = scene.target_tab_size
        scene.arrow_opacity = scene.target_arrow_opacity
        scene.verse_mark_size = scene.target_verse_mark_size
        scene.logical_mark_opacity = scene.target_logical_mark_opacity
        scene.sentence_break_enabled = scene.target_sentence_break_enabled
        scene.primary_translation = scene.target_primary_translation
        scene.enabled_interlinear = scene.target_enabled_interlinear
        
        self.update_fonts()
        self.save_settings()
        scene.recalculate_layout(scene.last_width, center_verse_idx=int(scene.virtual_scroll_y))
        scene.setSceneRect(QRectF(0, scene.scroll_y, scene.last_width, scene.view_height))
        scene._render_study_overlays()
        scene._render_search_overlays()
        scene.render_verses()
        scene.scrollChanged.emit(int(scene.virtual_scroll_y))
        scene.layoutFinished.emit()
