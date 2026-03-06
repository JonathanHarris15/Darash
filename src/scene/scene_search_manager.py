from PySide6.QtCore import Qt, Signal, QObject

class SceneSearchManager(QObject):
    """
    Handles search logic, result tracking, and navigation for the ReaderScene.
    """
    def __init__(self, scene):
        super().__init__(scene)
        self.scene = scene
        self.search_engine = None

    def handle_search(self, text: str):
        scene = self.scene
        if self.search_engine is None:
            from src.core.search_engine import SearchEngine
            self.search_engine = SearchEngine(scene.loader.flat_verses)

        scene.search_results.clear()
        scene.search_marks_y.clear()
        if hasattr(scene, 'search_verse_refs'):
            scene.search_verse_refs.clear()
        if hasattr(scene, 'search_heading_matches'):
            scene.search_heading_matches.clear()
        scene.current_search_idx = -1
        
        if not text:
            scene.searchStatusUpdated.emit(0, 0)
            scene._render_search_overlays()
            scene.render_verses()
            return
            
        results = self.search_engine.search(text)
        scene.search_results = results
        
        scene.search_verse_refs = {res.display_ref for res in results if res.scope == 'verse'}
        scene.search_heading_matches = {(res.scope, res.display_ref) for res in results if res.scope in ('chapter', 'book')}
        
        # Calculate virtual scroll positions for the scrollbar marks
        scene.search_marks_y = [scene.loader.get_verse_index(res.scroll_ref) for res in results]
            
        total = len(scene.search_results)
        if total > 0:
            scene.current_search_idx = 0
            self.scroll_to_current_match()
            
        scene.searchStatusUpdated.emit(scene.current_search_idx, total)
        scene._render_search_overlays()

    def scroll_to_current_match(self):
        scene = self.scene
        if 0 <= scene.current_search_idx < len(scene.search_results):
            result = scene.search_results[scene.current_search_idx]
            idx = scene.loader.get_verse_index(result.scroll_ref)
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
        if hasattr(scene, 'search_verse_refs'):
            scene.search_verse_refs.clear()
        if hasattr(scene, 'search_heading_matches'):
            scene.search_heading_matches.clear()
        scene.current_search_idx = -1
        scene.searchStatusUpdated.emit(-1, 0)
        scene._render_search_overlays()
        scene.render_verses()
