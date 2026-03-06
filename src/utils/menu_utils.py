"""
Shared utilities for creating consistently styled context menus across the application.
"""
from PySide6.QtWidgets import QMenu

# Unified dark-theme stylesheet applied to every context menu in the app.
_MENU_STYLE = """
    QMenu {
        background-color: #2b2b2b;
        color: #dedede;
        border: 1px solid #555;
        padding: 4px 0px;
    }
    QMenu::item {
        padding: 5px 20px 5px 12px;
    }
    QMenu::item:selected {
        background-color: #3a3f4b;
        color: #ffffff;
    }
    QMenu::separator {
        height: 1px;
        background: #444;
        margin: 3px 8px;
    }
"""


def create_menu(parent=None, title: str = "") -> QMenu:
    """
    Create a QMenu with the application's unified dark-theme style.

    Args:
        parent: Parent widget for the menu (used for positioning and ownership).
        title:  Optional title for the menu (used for sub-menus).

    Returns:
        A styled QMenu instance.
    """
    menu = QMenu(title, parent) if title else QMenu(parent)
    menu.setStyleSheet(_MENU_STYLE)
    return menu
