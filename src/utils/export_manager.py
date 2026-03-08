import re
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor
from src.ui.components.export_dialog import ExportDialog

class ExportManager(QObject):
    """
    Coordinates the extraction of content and showing the export dialog.
    """
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def trigger_export_dialog(self, export_type=None):
        """
        Shows the export dialog for the specified type or determines it from the active panel.
        """
        # Let's try to find the focused dock.
        
        if not export_type:
            # Try to determine from focused panel
            focused_widget = self.main_window.focusWidget()
            # Walk up to find the dock
            dock = focused_widget
            while dock and not isinstance(dock, (ExportDialog, )): # Add other types if needed
                if hasattr(dock, "windowTitle") and "Note" in dock.windowTitle():
                    export_type = "Notes"
                    break
                if hasattr(dock, "windowTitle") and "Outline" in dock.windowTitle():
                    export_type = "Outlines"
                    break
                dock = dock.parent()
        
        if not export_type:
            # Default to Notes if we can't determine
            export_type = "Notes"

        kwargs = {}
        dialog = ExportDialog(export_type, self.main_window, **kwargs)
        dialog.export_manager = self
        
        def refresh_content():
            if export_type == "Notes":
                html = self._extract_notes_html()
                dialog.set_content(html)
            elif export_type == "Outlines":
                html = self._extract_outline_data()
                dialog.set_content(html)

        dialog.updateNeeded.connect(refresh_content)
        refresh_content()
        dialog.exec()


    def _extract_notes_html(self):
        """Extracts HTML from the active NoteEditor."""
        for p in self.main_window.center_panels:
            try:
                if p.isVisible() and "Note" in p.windowTitle():
                    from src.ui.components.note_editor import NoteEditor
                    if isinstance(p.widget(), NoteEditor):
                        return p.widget().get_text()
            except RuntimeError:
                pass
        return "<h1>No note content found</h1>"

    def _extract_outline_data(self):
        """Extracts HTML structure data from the active OutlinePanel with proper formatting and bullets."""
        for p in self.main_window.center_panels:
            try:
                if p.isVisible() and "Outline" in p.windowTitle():
                    from src.ui.components.outline_panel import OutlinePanel
                    if isinstance(p.widget(), OutlinePanel):
                        panel = p.widget()
                        root = panel.outline_manager.get_node(panel.root_node_id)
                        if root:
                            # 1. Title as H1 - Left aligned
                            html = f"<h1>{root.get('title', 'Outline')}</h1>"
                            
                            def to_roman(n):
                                n += 1
                                val = [10, 9, 5, 4, 1]
                                syb = ["x", "ix", "v", "iv", "i"]
                                res = ""
                                for i in range(len(val)):
                                    while n >= val[i]: res += syb[i]; n -= val[i]
                                return res

                            def format_ref(start, end):
                                if not start or not end: return ""
                                # Simple logic mirroring OutlinePanel._format_ref_parts but joined
                                def parse(ref):
                                    m = re.match(r"(.*) (\d+):(\d+)([a-zA-Z]+)?", str(ref))
                                    return m.groups() if m else (None, None, None, None)
                                
                                s_book, s_chap, s_v, s_p = parse(start)
                                e_book, e_chap, e_v, e_p = parse(end)
                                
                                s_v_full = f"{s_v}{s_p if s_p else ''}"
                                e_v_full = f"{e_v}{e_p if e_p else ''}"
                                
                                if not s_book: return f"{start}-{end}"
                                
                                if s_book == e_book:
                                    if s_chap == e_chap:
                                        if s_v_full == e_v_full: return f"{s_book} {s_chap}:{s_v_full}"
                                        return f"{s_book} {s_chap}:{s_v_full}-{e_v_full}"
                                    return f"{s_book} {s_chap}:{s_v_full}-{e_chap}:{e_v_full}"
                                return f"{start}-{end}"

                            def get_list_type(level):
                                if level == 1: return "1" # Decimal
                                if level == 2: return "a" # Lower Alpha
                                if level == 3: return "i" # Lower Roman
                                return "1"

                            def traverse(node, level):
                                nonlocal html
                                ref = format_ref(node["range"]["start"], node["range"]["end"])
                                summary = node.get("summary", "").strip()
                                content = f"<b>[{ref}]</b> {summary}" if ref else summary
                                
                                if level == 0:
                                    # Root is a paragraph, but we start the list immediately after
                                    if content:
                                        html += f"<p>{content}</p>"
                                else:
                                    html += f"<li>{content}</li>"
                                
                                children = node.get("children", [])
                                if children:
                                    ltype = get_list_type(level + 1)
                                    html += f"<ol type='{ltype}'>"
                                    for child in children:
                                        traverse(child, level + 1)
                                    html += "</ol>"
                                    
                            traverse(root, 0)
                            return html
            except RuntimeError:
                pass
        return "<h1>No outline content found</h1>"
