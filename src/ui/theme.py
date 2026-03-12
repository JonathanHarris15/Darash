from PySide6.QtGui import QColor

class Theme:
    """
    Single Source of Truth for Design Tokens and Theme Engine.
    """
    # --- Color Palette ---
    BG_PRIMARY = "#1e1e1e"
    BG_SECONDARY = "#2d2d2d"
    BG_TERTIARY = "#3d3d3d"
    
    TEXT_PRIMARY = "#dcdcdc"
    TEXT_SECONDARY = "#aaaaaa"
    TEXT_MUTED = "#888888"
    
    ACCENT_PRIMARY = "#64c8ff"  # Reference blue
    ACCENT_HOVER = "#85d4ff"
    ACCENT_GOLD = "#ffcc00"     # Strongs highlight
    
    BORDER_DEFAULT = "#444444"
    BORDER_LIGHT = "#555555"
    
    # --- Semantic Colors ---
    HUD_BG = "rgba(30, 30, 30, 200)"
    OVERLAY_BG = "#1e1e1e"
    
    # --- Highlighting & Selection ---
    SELECTION_BG = "rgba(0, 120, 215, 150)"      # Translucent blue
    SEARCH_HIGHLIGHT = "rgba(255, 255, 0, 100)" # Translucent yellow
    
    HIGHLIGHT_COLORS = {
        "yellow": "#FFFF00",
        "green": "#00FF00",
        "blue": "#00FFFF",
        "pink": "#FF00FF",
        "orange": "#FFA500"
    }
    
    LOGICAL_MARKS = {
        "relation": "→",
        "parallel": "‖",
        "contrast": "≠",
        "continuation": "…",
        "result": "∴",
        "cause": "∵"
    }
    LOGICAL_MARK_COLOR = "#00ffcc"

    # --- Typography ---
    FONT_UI = "Montserrat"
    FONT_READER = "Times New Roman"
    FONT_MONO = "Consolas"
    
    SIZE_READER_DEFAULT = 18
    SIZE_UI_DEFAULT = 14
    SIZE_UI_SMALL = 12
    SIZE_UI_TINY = 10
    SIZE_HEADER = 36
    SIZE_CHAPTER = 24

    # --- Convenience Accessors for Scene ---
    @classmethod
    def color(cls, name):
        """Returns a QColor for the given token name."""
        val = getattr(cls, name, "#ffffff")
        if isinstance(val, str) and val.startswith("rgba"):
            # Simple rgba(r, g, b, a) parser
            parts = val.replace("rgba(", "").replace(")", "").split(",")
            r, g, b, a = [int(p.strip()) for p in parts]
            return QColor(r, g, b, a)
        return QColor(val)

    @classmethod
    def get_global_stylesheet(cls):
        """Returns the base application stylesheet."""
        return f"""
            QMainWindow, QDialog, QDockWidget {{
                background-color: {cls.BG_PRIMARY};
                color: {cls.TEXT_PRIMARY};
                font-family: '{cls.FONT_UI}';
            }}
            
            QToolTip {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER_DEFAULT};
                border-radius: 4px;
                padding: 4px;
            }}

            /* Scrollbars */
            QScrollBar:vertical {{
                background: {cls.BG_PRIMARY};
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {cls.BG_TERTIARY};
                min-height: 20px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background: {cls.BG_PRIMARY};
                height: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:horizontal {{
                background: {cls.BG_TERTIARY};
                min-width: 20px;
                border: none;
                border-radius: 5px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}

            /* Buttons */
            QPushButton {{
                background-color: {cls.BG_TERTIARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER_DEFAULT};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {cls.BORDER_LIGHT};
                border-color: {cls.ACCENT_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {cls.BG_SECONDARY};
            }}
            QPushButton:disabled {{
                color: {cls.TEXT_MUTED};
                background-color: {cls.BG_PRIMARY};
            }}

            /* Inputs */
            QLineEdit, QTextEdit {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 1px solid {cls.BORDER_DEFAULT};
                border-radius: 4px;
                padding: 4px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {cls.ACCENT_PRIMARY};
            }}
        """
