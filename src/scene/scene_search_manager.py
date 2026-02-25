from PySide6.QtCore import Qt, Signal, QObject

class SceneSearchManager(QObject):
    """
    Handles search logic, result tracking, and navigation for the ReaderScene.
    """
    def __init__(self, scene):
        super().__init__(scene)
        self.scene = scene

    def handle_search(self, text: str):
        scene = self.scene
        scene.search_results.clear()
        scene.search_marks_y.clear()
        scene.current_search_idx = -1
        
        if not text:
            scene.searchStatusUpdated.emit(0, 0)
            scene.render_verses()
            return
            
        doc = scene.main_text_item.document()
        cursor = doc.find(text)
        while not cursor.isNull():
            start = cursor.selectionStart()
            scene.search_results.append((start, cursor.selectionEnd() - start))
            scene.search_marks_y.append(doc.documentLayout().blockBoundingRect(cursor.block()).top())
            cursor = doc.find(text, cursor)
            
        total = len(scene.search_results)
        if total > 0:
            scene.current_search_idx = 0
            self.scroll_to_current_match()
            
        scene.searchStatusUpdated.emit(scene.current_search_idx, total)
        scene._render_search_overlays()

    def scroll_to_current_match(self):
        scene = self.scene
        if 0 <= scene.current_search_idx < len(scene.search_marks_y):
            # In the virtual system, we should ideally find the verse index
            # for this search result and scroll to it.
            start_pos, _ = scene.search_results[scene.current_search_idx]
            ref = scene._get_ref_from_pos(start_pos)
            if ref:
                idx = scene.loader.get_verse_index(ref)
                if idx != -1:
                    scene.set_scroll_y(idx)
            
            scene.searchStatusUpdated.emit(scene.current_search_idx, len(scene.search_results))

    def next_match(self):
        scene = self.scene
        if not scene.search_results: return
        scene.current_search_idx = (scene.current_search_idx + 1) % len(scene.search_results)
        self.scroll_to_current_match()

    def prev_match(self):
        scene = self.scene
        if not scene.search_results: return
        scene.current_search_idx = (scene.current_search_idx - 1) % len(scene.search_results)
        self.scroll_to_current_match()

    def clear_search(self):
        scene = self.scene
        scene.search_results.clear()
        scene.search_marks_y.clear()
        scene.current_search_idx = -1
        scene.searchStatusUpdated.emit(-1, 0)
        scene._render_search_overlays()
