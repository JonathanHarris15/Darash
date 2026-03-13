from PySide6.QtWidgets import (
    QToolBar, QFontComboBox, QComboBox, QToolButton, QMenu, QColorDialog, QInputDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import (
    QAction, QTextCharFormat, QFont, QColor, QTextCursor, QTextListFormat, QKeySequence
)
from src.utils.path_utils import get_resource_path

class FormattingToolBar(QToolBar):
    """A compact Rich-Text formatting toolbar embedded above the editor."""
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor; self.setMovable(False); self.setIconSize(QSize(16, 16))
        arrow_path = get_resource_path("resources/icons/arrow_down_white.svg").replace("\\", "/")
        self.setStyleSheet(f"""
            QToolBar {{ background: #2a2a2a; border-bottom: 1px solid #444; spacing: 2px; padding: 2px 4px; }}
            QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 3px; padding: 3px 5px; color: #ccc; font-size: 12px; }}
            QToolButton:hover {{ background: #3a3a3a; border-color: #555; }}
            QToolButton:checked {{ background: #005a9e; border-color: #007acc; color: white; }}
            QComboBox, QFontComboBox {{ background: #333; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; min-width: 60px; }}
            QComboBox::drop-down, QFontComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 16px; border-left: 1px solid #555; background: transparent; }}
            QComboBox::down-arrow, QFontComboBox::down-arrow {{ image: url({arrow_path}); width: 10px; height: 6px; }}
        """)
        self._build(); editor.cursorPositionChanged.connect(self._sync_state); editor.currentCharFormatChanged.connect(self._sync_format)

    def _build(self):
        e = self.editor
        self.style_combo = QComboBox(); self.style_combo.addItems(["Normal", "Heading 1", "Heading 2", "Heading 3"]); self.style_combo.setFixedWidth(90); self.style_combo.setFocusPolicy(Qt.NoFocus); self.style_combo.currentIndexChanged.connect(self._apply_heading); self.addWidget(self.style_combo)
        self.font_combo = QFontComboBox(); self.font_combo.setFixedWidth(140); self.font_combo.setFocusPolicy(Qt.NoFocus); self.font_combo.currentFontChanged.connect(e.setCurrentFont); self.addWidget(self.font_combo)
        self.size_combo = QComboBox(); self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36", "48", "72"]); self.size_combo.setCurrentText("12"); self.size_combo.setFixedWidth(50); self.size_combo.setFocusPolicy(Qt.NoFocus); self.size_combo.currentTextChanged.connect(self._apply_font_size); self.addWidget(self.size_combo)
        self.addSeparator()
        self.act_bold = QAction("B", self); self.act_bold.setShortcut(QKeySequence.Bold); self.act_bold.setCheckable(True); self.act_bold.setFont(QFont("", -1, QFont.Bold)); self.act_bold.triggered.connect(self._toggle_bold); self.addAction(self.act_bold)
        self.act_italic = QAction("I", self); self.act_italic.setShortcut(QKeySequence.Italic); self.act_italic.setCheckable(True); f = QFont(); f.setItalic(True); self.act_italic.setFont(f); self.act_italic.triggered.connect(self._toggle_italic); self.addAction(self.act_italic)
        self.act_under = QAction("U", self); self.act_under.setShortcut(QKeySequence.Underline); self.act_under.setCheckable(True); f = QFont(); f.setUnderline(True); self.act_under.setFont(f); self.act_under.triggered.connect(self._toggle_underline); self.addAction(self.act_under)
        self.act_strike = QAction("S̶", self); self.act_strike.setCheckable(True); self.act_strike.triggered.connect(self._toggle_strike); self.addAction(self.act_strike)
        self.addSeparator()
        self.act_text_color = QAction("A", self); self.act_text_color.triggered.connect(self._pick_text_color); self.addAction(self.act_text_color)
        self.act_highlight = QAction("🖊", self); self.act_highlight.triggered.connect(self._pick_highlight_color); self.addAction(self.act_highlight)
        self._align_options = [("⬅  Left", Qt.AlignLeft, "⬅"), ("↔  Center", Qt.AlignCenter, "↔"), ("➡  Right", Qt.AlignRight, "➡")]
        self.align_btn = QToolButton(); self.align_btn.setPopupMode(QToolButton.InstantPopup); self.align_btn.setFocusPolicy(Qt.NoFocus); self.align_btn.setText("⬅"); self.align_btn.setStyleSheet("QToolButton { background: transparent; border: 1px solid transparent; border-radius: 3px; padding: 3px 5px; color: #ccc; font-size: 12px; } QToolButton::menu-indicator { image: none; }")
        align_menu = QMenu(self); align_menu.setStyleSheet("QMenu { background: #2a2a2a; color: #ccc; border: 1px solid #555; } QMenu::item:selected { background: #005a9e; }")
        for label, align, icon in self._align_options: act = align_menu.addAction(label); act.triggered.connect(lambda c, a=align, t=icon: (e.setAlignment(a), self.align_btn.setText(t)))
        self.align_btn.setMenu(align_menu); self.addWidget(self.align_btn)
        self.addSeparator()
        self.act_bullet = QAction("• List", self); self.act_bullet.setCheckable(True); self.act_bullet.triggered.connect(lambda c: e.textCursor().createList(QTextListFormat.ListDisc) if c else self._remove_list()); self.addAction(self.act_bullet)
        self.act_numbered = QAction("1. List", self); self.act_numbered.setCheckable(True); self.act_numbered.triggered.connect(lambda c: e.textCursor().createList(QTextListFormat.ListDecimal) if c else self._remove_list()); self.addAction(self.act_numbered)
        self.addSeparator()
        act_bible = QAction("🔗 Bible", self); act_bible.triggered.connect(self._insert_bible_link); self.addAction(act_bible)

    def _merge_format(self, fmt):
        cursor = self.editor.textCursor(); 
        if not cursor.hasSelection(): cursor.select(QTextCursor.WordUnderCursor)
        cursor.mergeCharFormat(fmt); self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self, checked): fmt = QTextCharFormat(); fmt.setFontWeight(QFont.Bold if checked else QFont.Normal); self._merge_format(fmt)
    def _toggle_italic(self, checked): fmt = QTextCharFormat(); fmt.setFontItalic(checked); self._merge_format(fmt)
    def _toggle_underline(self, checked): fmt = QTextCharFormat(); fmt.setFontUnderline(checked); self._merge_format(fmt)
    def _toggle_strike(self, checked): fmt = QTextCharFormat(); fmt.setFontStrikeOut(checked); self._merge_format(fmt)
    def _apply_font_size(self, s): 
        try: f = float(s); fmt = QTextCharFormat(); fmt.setFontPointSize(f); self._merge_format(fmt)
        except: pass
    def _pick_text_color(self): c = QColorDialog.getColor(self.editor.textColor(), self.editor); (fmt := QTextCharFormat()).setForeground(c); self._merge_format(fmt) if c.isValid() else None
    def _pick_highlight_color(self): c = QColorDialog.getColor(Qt.yellow, self.editor); (fmt := QTextCharFormat()).setBackground(c); self._merge_format(fmt) if c.isValid() else None
    def _apply_heading(self, i):
        cursor = self.editor.textCursor(); start, end = (cursor.selectionStart(), cursor.selectionEnd()) if cursor.hasSelection() else (cursor.position(), cursor.position())
        block = self.editor.document().findBlock(start)
        # Heading sizes and bold status
        sizes = {0: 12, 1: 22, 2: 18, 3: 14}
        is_bold = {0: False, 1: True, 2: True, 3: True}
        
        while block.isValid() and block.position() <= end:
            bc = QTextCursor(block)
            bf = bc.blockFormat()
            bf.setHeadingLevel(i)
            bc.setBlockFormat(bf)
            
            cf = QTextCharFormat()
            cf.setFontPointSize(sizes.get(i, 12))
            cf.setFontWeight(QFont.Bold if is_bold.get(i, False) else QFont.Normal)
            bc.mergeBlockCharFormat(cf)
            
            block = block.next()
    def _remove_list(self): 
        cursor = self.editor.textCursor(); lst = cursor.currentList()
        if lst: (block := cursor.block(), lst.remove(block), (bf := block.blockFormat(), bf.setIndent(0))[0], cursor.setBlockFormat(bf))

    def _insert_bible_link(self):
        ref, ok = QInputDialog.getText(self.editor, "Insert Bible Reference", "Reference:")
        if ok and ref.strip():
            c = self.editor.textCursor(); (fmt := QTextCharFormat()).setAnchor(True); fmt.setAnchorHref(f"bible:{ref.strip().replace(' ','+')}"); fmt.setForeground(QColor("#4fc3f7")); fmt.setFontUnderline(True)
            c.insertText(ref.strip(), fmt); (r := QTextCharFormat()).setAnchor(False); r.setForeground(self.editor.palette().text().color()); r.setFontUnderline(False); c.insertText(" ", r)

    def _sync_format(self, fmt):
        self.act_bold.setChecked(fmt.fontWeight() == QFont.Bold); self.act_italic.setChecked(fmt.fontItalic()); self.act_under.setChecked(fmt.fontUnderline()); self.act_strike.setChecked(fmt.fontStrikeOut())
        self.font_combo.blockSignals(True); f = fmt.font(); f.setPointSize(max(1, int(self.editor.font().pointSize())) if f.pointSize() <= 0 else f.pointSize()); self.font_combo.setCurrentFont(f); self.font_combo.blockSignals(False)
        self.size_combo.blockSignals(True); pt = fmt.fontPointSize(); self.size_combo.setCurrentText(str(int(pt if pt > 0 else self.editor.font().pointSize()))); self.size_combo.blockSignals(False)

    def _sync_state(self):
        if not hasattr(self, "style_combo"): return
        cursor = self.editor.textCursor()
        self.style_combo.blockSignals(True)
        # style_combo only has 4 items (0,1,2,3)
        lvl = cursor.blockFormat().headingLevel()
        self.style_combo.setCurrentIndex(min(lvl, 3))
        self.style_combo.blockSignals(False)
        
        align = self.editor.alignment()
        for l, a, i in self._align_options: 
            if align == a: self.align_btn.setText(i); break
        lst = self.editor.textCursor().currentList()
        self.act_bullet.setChecked(lst.format().style() == QTextListFormat.ListDisc if lst else False)
        self.act_numbered.setChecked(lst.format().style() == QTextListFormat.ListDecimal if lst else False)
