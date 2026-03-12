from PySide6.QtCore import Qt, QPointF, QObject
from PySide6.QtGui import QColor, QGuiApplication, QTextCursor
from src.scene.components.reader_items import ArrowItem, OutlineDividerItem

class SceneStudyInputHandler:
    """Handles specialized study interactions: arrows, strongs, and deletions."""
    def __init__(self, scene, parent_handler):
        self.scene = scene
        self.parent = parent_handler

    def handle_delete_key(self):
        scene, view = self.scene, self.scene.views()[0]
        mouse_pos = scene.last_mouse_scene_pos
        item = scene.itemAt(mouse_pos, view.transform())
        if isinstance(item, OutlineDividerItem) and item.parent_node and item.split_idx != -1:
            if scene.study_manager.outline_manager.delete_divider_smart(item.parent_node["id"], item.split_idx):
                scene._render_outline_overlays(); scene.studyDataChanged.emit()
            return

        key_str = scene._get_word_key_at_pos(mouse_pos)
        if not key_str: return
        
        modified = False; scene.study_manager.save_state()
        if key_str in scene.study_manager.data["symbols"]:
            del scene.study_manager.data["symbols"][key_str]; modified = True

        arrows = scene.study_manager.data.get("arrows", {})
        if key_str in arrows: del arrows[key_str]; modified = True
        else:
            to_remove = []
            for s_key, a_list in arrows.items():
                new_l = [a for a in a_list if not (a.get('end_key') == key_str and a.get('type') == 'ghost')]
                if len(new_l) < len(a_list):
                    modified = True
                    if new_l: arrows[s_key] = new_l
                    else: to_remove.append(s_key)
            for sk in to_remove: del arrows[sk]

        if key_str in scene.study_manager.data.get("logical_marks", {}):
            del scene.study_manager.data["logical_marks"][key_str]; modified = True
            
        if modified:
            scene.study_manager.save_data(); scene._render_study_overlays(); scene.studyDataChanged.emit()

    def handle_strongs_lookup(self):
        scene = self.scene; mouse_pos = scene.last_mouse_scene_pos
        sn_str, _ = scene._get_strongs_at_pos(mouse_pos)
        if sn_str:
            scene.showStrongsTooltip.emit(mouse_pos, None)
            sn = sn_str.split()[0]; entry = scene.strongs_manager.get_entry(sn)
            if entry:
                scene.showStrongsVerboseDialog.emit(sn, entry, scene.strongs_manager.get_usages(sn))

    def start_arrow_drawing(self):
        scene = self.scene; mouse_pos = scene.last_mouse_scene_pos
        key = scene._get_word_key_at_pos(mouse_pos)
        if key:
            scene.arrow_start_key = key; scene.arrow_start_center = scene._get_word_center(key)
            if scene.arrow_start_center: scene.is_drawing_arrow = True; self.draw_temp_arrow(mouse_pos)

    def finish_arrow_drawing(self):
        scene = self.scene; mouse_pos = scene.last_mouse_scene_pos
        end_key, start_key = scene._get_word_key_at_pos(mouse_pos), scene.arrow_start_key
        if not end_key or end_key == start_key:
            scene.is_drawing_arrow = False; scene.arrow_start_key = scene.arrow_start_center = None
            self.clear_temp_arrow(); scene._render_study_overlays(); scene.studyDataChanged.emit(); return

        view = scene.views()[0]; screen_pos = view.viewport().mapToGlobal(view.mapFromScene(mouse_pos))
        from src.utils.menu_utils import create_menu
        menu = create_menu(view, "Arrow Type")
        act_s, act_sn, act_g = menu.addAction("Standard"), menu.addAction("Snake"), menu.addAction("Ghost")
        chosen = menu.exec(screen_pos)
        scene.is_drawing_arrow = False; scene.arrow_start_key = scene.arrow_start_center = None; self.clear_temp_arrow()
        if chosen:
            a_type = "straight" if chosen == act_s else ("snake" if chosen == act_sn else "ghost")
            scene.study_manager.add_arrow(start_key, end_key, QColor(255,255,255,150).name(QColor.HexArgb), arrow_type=a_type)
            scene._render_study_overlays(); scene.studyDataChanged.emit()

    def draw_temp_arrow(self, end_pos):
        self.clear_temp_arrow(); scene = self.scene
        if not scene.arrow_start_center: return
        scene.temp_arrow_item = ArrowItem(scene.arrow_start_center, end_pos, QColor(255,255,255,128))
        scene.addItem(scene.temp_arrow_item)

    def clear_temp_arrow(self):
        if self.scene.temp_arrow_item: self.scene.removeItem(self.scene.temp_arrow_item); self.scene.temp_arrow_item = None
