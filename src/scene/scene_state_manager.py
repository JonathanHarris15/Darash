from PySide6.QtCore import QTimer, QRectF
from src.core.constants import SCROLL_SENSITIVITY

class SceneStateManager:
    """Handles scroll state, chunk boundaries, and scene rect orchestration."""
    def __init__(self, scene):
        self.scene = scene
        self.virtual_scroll_y = 0.0
        self.target_virtual_scroll_y = 0.0
        self.scroll_timer = QTimer(scene)
        self.scroll_timer.setInterval(16)
        self.scroll_timer.timeout.connect(self.update_scroll_step)
        
        self.chunk_start_idx = 0
        self.chunk_end_idx = 0
        self.CHUNK_SIZE = 400

    def check_chunk_boundaries(self):
        buffer = 100 
        if (self.virtual_scroll_y < self.chunk_start_idx + buffer or self.virtual_scroll_y > self.chunk_end_idx - buffer):
            if (self.chunk_start_idx > 0 and self.virtual_scroll_y < self.chunk_start_idx + buffer) or \
               (self.chunk_end_idx < len(self.scene.loader.flat_verses) and self.virtual_scroll_y > self.chunk_end_idx - buffer):
                self.scene.recalculate_layout(self.scene.last_width, center_verse_idx=int(self.virtual_scroll_y))

    def _sync_physical_scroll(self):
        v_idx = int(self.virtual_scroll_y); frac = self.virtual_scroll_y - v_idx
        if 0 <= v_idx < len(self.scene.loader.flat_verses):
            ref = self.scene.loader.flat_verses[v_idx]['ref']
            if ref in self.scene.verse_y_map:
                y_top, y_bottom = self.scene.verse_y_map[ref]
                self.scene.scroll_y = y_top + (frac * (y_bottom - y_top))
        self.scene.update_scene_rect_only()
        self.scene.scrollChanged.emit(int(self.virtual_scroll_y))
        self.scene._update_item_visibility()

    def update_scroll_step(self):
        diff = self.target_virtual_scroll_y - self.virtual_scroll_y
        if abs(diff) < 0.001: 
            self.virtual_scroll_y = self.target_virtual_scroll_y; self.scroll_timer.stop()
        else: 
            self.virtual_scroll_y += diff * 0.15
        self.check_chunk_boundaries(); self._sync_physical_scroll()

    def set_scroll_y(self, value):
        self.target_virtual_scroll_y = float(value); self.virtual_scroll_y = self.target_virtual_scroll_y
        self.check_chunk_boundaries(); self._sync_physical_scroll()

    def handle_resize(self, width, height):
        if abs(width - self.scene.last_width) > 2:
            self.scene.last_width = width
            self.scene.recalculate_layout(width, center_verse_idx=int(self.virtual_scroll_y))
            self.scene._render_study_overlays(); self.scene._render_search_overlays()
        self.scene.view_height = height
        self.scene.update_scene_rect_only()
