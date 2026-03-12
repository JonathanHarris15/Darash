"""
Shared utilities for creating consistently styled context menus across the application.
"""
from PySide6.QtWidgets import QMenu

from src.core.theme import Theme

# Unified dark-theme stylesheet applied to every context menu in the app.
_MENU_STYLE = f"""
    QMenu {{
        background-color: {Theme.BG_SECONDARY};
        color: {Theme.TEXT_SECONDARY};
        border: 1px solid {Theme.BORDER_DEFAULT};
        padding: 4px 0px;
    }}
    QMenu::item {{
        padding: 5px 20px 5px 12px;
    }}
    QMenu::item:selected {{
        background-color: {Theme.BG_TERTIARY};
        color: {Theme.TEXT_PRIMARY};
    }}
    QMenu::separator {{
        height: 1px;
        background: {Theme.BORDER_LIGHT};
        margin: 3px 8px;
    }}
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
