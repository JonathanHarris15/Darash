from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, 
    QLabel, QMenu, QColorDialog, QScrollArea, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QAction

class BookmarkWidget(QFrame):
    clicked = Signal(str, str, str) # book, chap, verse
    deleted = Signal(str) # ref
    colorChanged = Signal(str, str) # ref, color
    titleChanged = Signal(str, str) # ref, title

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data # {ref, color, book, chapter, verse, title}
        self.ref = data['ref']
        
        # Larger size for sliding
        self.setFixedSize(160, 30)
        self._update_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        self.label = QLabel(self._get_display_text())
        self.label.setStyleSheet("color: white; font-size: 10px; font-weight: bold;")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label.hide()
        layout.addWidget(self.label)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(self._get_tooltip_text())

        # Peek 10px
        self.move(-150, 0)

        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self._menu_active = False

    def _get_display_text(self):
        title = self.data.get('title', '')
        return f"{title} ({self.ref})" if title else self.ref

    def _get_tooltip_text(self):
        title = self.data.get('title', '')
        return f"{title}\n{self.ref}" if title else self.ref

    def _update_style(self):
        self.setStyleSheet(f"""
            BookmarkWidget {{
                background-color: {self.data['color']};
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 30);
                border-left: none;
            }}
        """)

    def enterEvent(self, event):
        self.label.setText(self._get_display_text())
        self.label.show()
        self.anim.stop()
        self.anim.setEndValue(QPoint(0, self.y()))
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._menu_active:
            super().leaveEvent(event)
            return
            
        self.label.hide()
        self.anim.stop()
        self.anim.setEndValue(QPoint(-150, self.y()))
        self.anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data['book'], self.data['chapter'], self.data['verse'])
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
        super().mousePressEvent(event)

    def _show_context_menu(self, pos):
        # Ensure sidebar is raised
        p = self.parent()
        while p:
            if isinstance(p, QScrollArea):
                p.raise_()
                break
            p = p.parent()

        self._menu_active = True
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        set_title_act = QAction("Set Title", self)
        set_title_act.triggered.connect(self._set_title)
        menu.addAction(set_title_act)
        
        change_color_act = QAction("Change Color", self)
        change_color_act.triggered.connect(self._change_color)
        menu.addAction(change_color_act)
        
        delete_act = QAction("Delete Bookmark", self)
        delete_act.triggered.connect(lambda: self.deleted.emit(self.ref))
        menu.addAction(delete_act)
        
        menu.exec(self.mapToGlobal(pos))
        self._menu_active = False
        
        # Trigger leave logic if mouse is no longer over the widget
        if not self.underMouse():
            self.leaveEvent(None)

    def _set_title(self):
        title, ok = QInputDialog.getText(self, "Bookmark Title", "Enter a title for this bookmark:", text=self.data.get('title', ''))
        if ok:
            self.data['title'] = title
            self.label.setText(self._get_display_text())
            self.setToolTip(self._get_tooltip_text())
            self.titleChanged.emit(self.ref, title)

    def _change_color(self):
        color = QColorDialog.getColor(QColor(self.data['color']), self, "Select Bookmark Color")
        if color.isValid():
            new_color = color.name()
            self.data['color'] = new_color
            self._update_style()
            self.colorChanged.emit(self.ref, new_color)

class BookmarkSidebar(QScrollArea):
    bookmarkJumpRequested = Signal(str, str, str)
    bookmarksChanged = Signal()

    def __init__(self, study_manager, parent=None):
        super().__init__(parent)
        self.study_manager = study_manager
        
        self.setWidgetResizable(True)
        self.setFixedWidth(15) # Peek width
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Smooth Scroll State
        from PySide6.QtCore import QTimer
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setInterval(16)
        self.scroll_timer.timeout.connect(self._update_scroll)
        self.target_scroll_y = 0.0
        self.current_scroll_y = 0.0
        self._wheel_accumulator = 0.0

        self.content = QWidget()
        self.content.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(0, 10, 0, 0)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.setWidget(self.content)
        self.refresh_bookmarks()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        self._wheel_accumulator += delta
        
        while abs(self._wheel_accumulator) >= 20:
            step = 20 if self._wheel_accumulator > 0 else -20
            self.target_scroll_y -= step * 0.8 # Sensitivity
            self._wheel_accumulator -= step
            
        max_scroll = self.verticalScrollBar().maximum()
        self.target_scroll_y = max(0, min(max_scroll, self.target_scroll_y))
        
        if not self.scroll_timer.isActive():
            self.scroll_timer.start()
        event.accept()

    def _update_scroll(self):
        diff = self.target_scroll_y - self.current_scroll_y
        if abs(diff) < 0.5:
            self.current_scroll_y = self.target_scroll_y
            self.scroll_timer.stop()
        else:
            self.current_scroll_y += diff * 0.15 # Smoothing factor
        
        self.verticalScrollBar().setValue(int(self.current_scroll_y))

    def enterEvent(self, event):
        self.setFixedWidth(160)
        self.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Don't shrink if a child bookmark has an active menu
        from src.ui.components.bookmark_ui import BookmarkWidget
        for bw in self.findChildren(BookmarkWidget):
            if bw._menu_active:
                super().leaveEvent(event)
                return

        self.setFixedWidth(15)
        super().leaveEvent(event)

    def refresh_bookmarks(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for b_data in self.study_manager.data.get("bookmarks", []):
            # Container to hold the sliding bookmark
            container = QWidget()
            container.setFixedSize(160, 35) # Same width as expanded bookmark
            
            bw = BookmarkWidget(b_data, container)
            bw.clicked.connect(self.bookmarkJumpRequested.emit)
            bw.deleted.connect(self._on_bookmark_deleted)
            bw.colorChanged.connect(self._on_bookmark_color_changed)
            bw.titleChanged.connect(self._on_bookmark_title_changed)
            
            self.layout.addWidget(container)

    def _on_bookmark_deleted(self, ref):
        self.study_manager.delete_bookmark(ref)
        self.refresh_bookmarks()
        self.bookmarksChanged.emit()

    def _on_bookmark_color_changed(self, ref, color):
        self.study_manager.update_bookmark_color(ref, color)
        self.bookmarksChanged.emit()

    def _on_bookmark_title_changed(self, ref, title):
        self.study_manager.update_bookmark_title(ref, title)
        self.bookmarksChanged.emit()
