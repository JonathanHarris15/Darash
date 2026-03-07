from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit,
    QToolBar, QFontComboBox, QComboBox,
    QColorDialog, QInputDialog, QWidget, QFrame,
    QToolButton, QMenu
)
from PySide6.QtCore import Qt, Signal, QUrl, QSize, QPoint
from PySide6.QtGui import (
    QAction, QTextCharFormat, QFont, QColor,
    QTextCursor, QTextListFormat, QDesktopServices, QIcon,
    QKeySequence, QTextBlockFormat, QMouseEvent
)


# ---------------------------------------------------------------------------
# QTextEdit sub-class with anchor click support
# ---------------------------------------------------------------------------

class _RichTextEdit(QTextEdit):
    """QTextEdit with anchor-click support and Tab/Shift+Tab indentation."""
    anchorClicked = Signal(QUrl)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Automatically break out of link character format whenever the cursor moves.
        # This prevents typing from getting "stuck" inside a hyperlink after backspacing
        # to its boundary.
        self.cursorPositionChanged.connect(self._break_link_format)

    def _break_link_format(self):
        """If the current insertion point is inside/adjacent to a link, strip the
        anchor formatting so the next keystroke produces plain text."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            return
        fmt = cursor.charFormat()
        if fmt.anchorHref():
            plain = QTextCharFormat(fmt)
            plain.setAnchor(False)
            plain.setAnchorHref("")
            plain.setAnchorNames([])
            plain.setFontUnderline(False)
            # Reset to the foreground colour of normal editor text
            plain.clearForeground()
            self.setCurrentCharFormat(plain)

    def mousePressEvent(self, event: QMouseEvent):
        # Fire anchor click on plain left-click (no Ctrl needed)
        if event.button() == Qt.LeftButton:
            anchor = self.anchorAt(event.position().toPoint())
            if anchor:
                self.anchorClicked.emit(QUrl(anchor))
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Show pointer cursor when hovering over a link
        anchor = self.anchorAt(event.position().toPoint())
        if anchor:
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Tab:
            self._change_indent(+1)
            event.accept()
            return
        if key == Qt.Key_Backtab:   # Shift+Tab
            self._change_indent(-1)
            event.accept()
            return
        super().keyPressEvent(event)

    def _change_indent(self, delta: int):
        """Increase (delta=+1) or decrease (delta=-1) indent of the current block.

        For bullet lists, the marker cycles with the indent level:
            1 → Disc (●)   2 → Circle (○)   3 → Square (■)   4 → Disc …

        On de-indent, we first look for an adjacent list at the new indent level
        and *join* it (preserving numbered sequence) before falling back to
        creating a fresh list.
        """
        _BULLET_CYCLE = [
            QTextListFormat.ListDisc,
            QTextListFormat.ListCircle,
            QTextListFormat.ListSquare,
        ]

        cursor = self.textCursor()
        lst = cursor.currentList()

        if lst:
            # ---- Build the target format ----
            fmt = QTextListFormat(lst.format())
            new_indent = max(1, fmt.indent() + delta)
            fmt.setIndent(new_indent)

            # Cycle bullet style by indent depth
            if fmt.style() in _BULLET_CYCLE:
                fmt.setStyle(_BULLET_CYCLE[(new_indent - 1) % len(_BULLET_CYCLE)])

            # ---- Try to merge into an adjacent list instead of creating new ----
            block = cursor.block()
            doc = self.document()
            merged = False
            for adj_block in (block.previous(), block.next()):
                if not adj_block.isValid():
                    continue
                adj_cursor = QTextCursor(doc)
                adj_cursor.setPosition(adj_block.position())
                adj_lst = adj_cursor.currentList()
                if adj_lst:
                    af = adj_lst.format()
                    if af.indent() == new_indent and af.style() == fmt.style():
                        adj_lst.add(block)
                        merged = True
                        break

            if not merged:
                cursor.createList(fmt)

        else:
            # Plain paragraph — adjust block indent
            block_fmt = cursor.blockFormat()
            new_indent = max(0, block_fmt.indent() + delta)
            block_fmt.setIndent(new_indent)
            cursor.setBlockFormat(block_fmt)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_html(text: str) -> bool:
    """Return True when the text looks like saved Qt rich-text HTML."""
    stripped = text.strip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html")


def _icon_label(char: str) -> QIcon:
    """Build a tiny placeholder icon from a single emoji/character.
    QAction already shows the text if no icon is supplied, so we skip heavy
    icon generation and rely on action text instead. This helper is kept for
    potential future upgrade."""
    return QIcon()


# ---------------------------------------------------------------------------
# Toolbar factory
# ---------------------------------------------------------------------------

class _FormattingToolBar(QToolBar):
    """A compact Rich-Text formatting toolbar embedded above the editor."""

    def __init__(self, editor: _RichTextEdit, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setMovable(False)
        self.setIconSize(QSize(16, 16))
        self.setStyleSheet("""
            QToolBar {
                background: #2a2a2a;
                border-bottom: 1px solid #444;
                spacing: 2px;
                padding: 2px 4px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px 5px;
                color: #ccc;
                font-size: 12px;
            }
            QToolButton:hover {
                background: #3a3a3a;
                border-color: #555;
            }
            QToolButton:checked {
                background: #005a9e;
                border-color: #007acc;
                color: white;
            }
            QComboBox, QFontComboBox {
                background: #333;
                color: #ccc;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 2px 4px;
                min-width: 60px;
            }
            QComboBox::drop-down, QFontComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid #555;
                background: transparent;
            }
            QComboBox::down-arrow, QFontComboBox::down-arrow {
                image: url(resources/icons/arrow_down_white.svg);
                width: 10px;
                height: 6px;
            }
        """)
        self._build()
        editor.cursorPositionChanged.connect(self._sync_state)
        editor.currentCharFormatChanged.connect(self._sync_format)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build(self):
        e = self.editor

        # --- Heading style ---
        self.style_combo = QComboBox()
        self.style_combo.setToolTip("Paragraph Style")
        self.style_combo.addItems(["Normal", "Heading 1", "Heading 2", "Heading 3"])
        self.style_combo.setFixedWidth(90)
        self.style_combo.setFocusPolicy(Qt.NoFocus)
        self.style_combo.currentIndexChanged.connect(self._apply_heading)
        self.addWidget(self.style_combo)

        # --- Font family ---
        self.font_combo = QFontComboBox()
        self.font_combo.setToolTip("Font")
        self.font_combo.setFixedWidth(140)
        self.font_combo.setFocusPolicy(Qt.NoFocus)
        self.font_combo.currentFontChanged.connect(
            lambda f: e.setCurrentFont(f)
        )
        self.addWidget(self.font_combo)

        # --- Font size ---
        self.size_combo = QComboBox()
        sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36", "48", "72"]
        self.size_combo.addItems(sizes)
        self.size_combo.setCurrentText("12")
        self.size_combo.setFixedWidth(50)
        self.size_combo.setFocusPolicy(Qt.NoFocus)
        self.size_combo.currentTextChanged.connect(self._apply_font_size)
        self.addWidget(self.size_combo)

        self.addSeparator()

        # --- Bold ---
        self.act_bold = QAction("B", self)
        self.act_bold.setToolTip("Bold (Ctrl+B)")
        self.act_bold.setShortcut(QKeySequence.Bold)
        self.act_bold.setCheckable(True)
        self.act_bold.setFont(QFont("", -1, QFont.Bold))
        self.act_bold.triggered.connect(self._toggle_bold)
        self.addAction(self.act_bold)

        # --- Italic ---
        self.act_italic = QAction("I", self)
        self.act_italic.setToolTip("Italic (Ctrl+I)")
        self.act_italic.setShortcut(QKeySequence.Italic)
        self.act_italic.setCheckable(True)
        f = QFont(); f.setItalic(True)
        self.act_italic.setFont(f)
        self.act_italic.triggered.connect(self._toggle_italic)
        self.addAction(self.act_italic)

        # --- Underline ---
        self.act_under = QAction("U", self)
        self.act_under.setToolTip("Underline (Ctrl+U)")
        self.act_under.setShortcut(QKeySequence.Underline)
        self.act_under.setCheckable(True)
        f = QFont(); f.setUnderline(True)
        self.act_under.setFont(f)
        self.act_under.triggered.connect(self._toggle_underline)
        self.addAction(self.act_under)

        # --- Strikethrough ---
        self.act_strike = QAction("S̶", self)
        self.act_strike.setToolTip("Strikethrough")
        self.act_strike.setCheckable(True)
        self.act_strike.triggered.connect(self._toggle_strike)
        self.addAction(self.act_strike)

        self.addSeparator()

        # --- Text colour ---
        self.act_text_color = QAction("A", self)
        self.act_text_color.setToolTip("Text Color")
        self.act_text_color.triggered.connect(self._pick_text_color)
        self.addAction(self.act_text_color)

        # --- Highlight colour ---
        self.act_highlight = QAction("🖊", self)
        self.act_highlight.setToolTip("Highlight Color")
        self.act_highlight.triggered.connect(self._pick_highlight_color)
        self.addAction(self.act_highlight)

        # --- Alignment dropdown ---
        self._align_options = [
            ("⬅  Left",   Qt.AlignLeft,   "⬅"),
            ("↔  Center", Qt.AlignCenter, "↔"),
            ("➡  Right",  Qt.AlignRight,  "➡"),
        ]
        self.align_btn = QToolButton()
        self.align_btn.setPopupMode(QToolButton.InstantPopup)
        self.align_btn.setFocusPolicy(Qt.NoFocus)
        self.align_btn.setToolTip("Text Alignment")
        self.align_btn.setText("⬅")
        self.align_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px 5px;
                color: #ccc;
                font-size: 12px;
            }
            QToolButton:hover { background: #3a3a3a; border-color: #555; }
            QToolButton::menu-indicator { image: none; }
        """)
        align_menu = QMenu(self)
        align_menu.setStyleSheet("""
            QMenu { background: #2a2a2a; color: #ccc; border: 1px solid #555; }
            QMenu::item:selected { background: #005a9e; }
        """)
        for label, alignment, icon_text in self._align_options:
            act = align_menu.addAction(label)
            act.triggered.connect(
                lambda checked, a=alignment, t=icon_text: self._set_alignment(a, t)
            )
        self.align_btn.setMenu(align_menu)
        self.addWidget(self.align_btn)

        self.addSeparator()

        # --- Lists ---
        self.act_bullet = QAction("• List", self)
        self.act_bullet.setToolTip("Bulleted List")
        self.act_bullet.setCheckable(True)
        self.act_bullet.triggered.connect(self._toggle_bullet_list)
        self.addAction(self.act_bullet)

        self.act_numbered = QAction("1. List", self)
        self.act_numbered.setToolTip("Numbered List")
        self.act_numbered.setCheckable(True)
        self.act_numbered.triggered.connect(self._toggle_numbered_list)
        self.addAction(self.act_numbered)

        self.addSeparator()

        # --- Bible Reference link ---
        self.act_bible_link = QAction("🔗 Bible", self)
        self.act_bible_link.setToolTip("Insert Bible Reference Link")
        self.act_bible_link.triggered.connect(self._insert_bible_link)
        self.addAction(self.act_bible_link)

    # ------------------------------------------------------------------
    # Format application helpers
    # ------------------------------------------------------------------
    def _merge_format(self, fmt: QTextCharFormat):
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self, checked):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self._merge_format(fmt)

    def _toggle_italic(self, checked):
        fmt = QTextCharFormat()
        fmt.setFontItalic(checked)
        self._merge_format(fmt)

    def _toggle_underline(self, checked):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(checked)
        self._merge_format(fmt)

    def _toggle_strike(self, checked):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(checked)
        self._merge_format(fmt)

    def _apply_font_size(self, size_str: str):
        try:
            size = float(size_str)
            if size > 0:
                fmt = QTextCharFormat()
                fmt.setFontPointSize(size)
                self._merge_format(fmt)
        except ValueError:
            pass

    def _pick_text_color(self):
        color = QColorDialog.getColor(self.editor.textColor(), self.editor, "Select Text Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self._merge_format(fmt)

    def _pick_highlight_color(self):
        color = QColorDialog.getColor(Qt.yellow, self.editor, "Select Highlight Color")
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self._merge_format(fmt)

    def _apply_heading(self, index):
        """Apply heading level as a block-level format, preserving per-character sizes."""
        cursor = self.editor.textCursor()
        # Operate on every block in the selection (or just the current block)
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
        else:
            start = cursor.position()
            end = cursor.position()

        doc = self.editor.document()
        block = doc.findBlock(start)
        while block.isValid() and block.position() <= end:
            bc = QTextCursor(block)
            block_fmt = bc.blockFormat()
            # heading level: 0 = normal, 1-6 = H1-H6
            block_fmt.setHeadingLevel(index)  # index 0 → normal, 1 → H1, etc.
            bc.setBlockFormat(block_fmt)
            block = block.next()

    def _toggle_bullet_list(self, checked):
        cursor = self.editor.textCursor()
        if checked:
            cursor.createList(QTextListFormat.ListDisc)
            self.act_numbered.setChecked(False)
        else:
            self._remove_list(cursor)

    def _toggle_numbered_list(self, checked):
        cursor = self.editor.textCursor()
        if checked:
            cursor.createList(QTextListFormat.ListDecimal)
            self.act_bullet.setChecked(False)
        else:
            self._remove_list(cursor)

    def _remove_list(self, cursor):
        lst = cursor.currentList()
        if lst:
            block = cursor.block()
            lst.remove(block)
            block_fmt = block.blockFormat()
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)

    def _insert_bible_link(self):
        ref, ok = QInputDialog.getText(
            self.editor, "Insert Bible Reference",
            "Enter reference (e.g. John 3:16):"
        )
        if not ok or not ref.strip():
            return
        ref = ref.strip()
        link_ref = ref.replace(" ", "+")
        cursor = self.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setAnchor(True)
        fmt.setAnchorHref(f"bible:{link_ref}")
        fmt.setForeground(QColor("#4fc3f7"))
        fmt.setFontUnderline(True)
        cursor.insertText(ref, fmt)
        # Reset formatting after inserting
        reset = QTextCharFormat()
        reset.setAnchor(False)
        reset.setForeground(self.editor.palette().text().color())
        reset.setFontUnderline(False)
        cursor.insertText(" ", reset)

    # ------------------------------------------------------------------
    # Sync toolbar state with cursor position
    # ------------------------------------------------------------------
    def _sync_format(self, fmt: QTextCharFormat):
        self.act_bold.setChecked(fmt.fontWeight() == QFont.Bold)
        self.act_italic.setChecked(fmt.fontItalic())
        self.act_under.setChecked(fmt.fontUnderline())
        self.act_strike.setChecked(fmt.fontStrikeOut())

        # Sync font combo (block signals to avoid recursion)
        self.font_combo.blockSignals(True)
        font = fmt.font()
        # fontPointSize() / font.pointSize() returns -1 when inherited.
        # Guard it to avoid "QFont::setPointSize: Point size <= 0" warnings.
        if font.pointSize() <= 0:
            font.setPointSize(max(1, int(self.editor.font().pointSize())) or 12)
        self.font_combo.setCurrentFont(font)
        self.font_combo.blockSignals(False)

        self.size_combo.blockSignals(True)
        pt = fmt.fontPointSize()
        if pt <= 0:
            pt = self.editor.font().pointSize()
        self.size_combo.setCurrentText(str(int(pt)) if pt > 0 else "12")
        self.size_combo.blockSignals(False)

    def _set_alignment(self, alignment, icon_text):
        self.editor.setAlignment(alignment)
        self.align_btn.setText(icon_text)

    def _sync_state(self):
        alignment = self.editor.alignment()
        for label, align, icon_text in self._align_options:
            if alignment == align:
                self.align_btn.setText(icon_text)
                break

        cursor = self.editor.textCursor()
        lst = cursor.currentList()
        if lst:
            fmt = lst.format()
            self.act_bullet.setChecked(fmt.style() == QTextListFormat.ListDisc)
            self.act_numbered.setChecked(fmt.style() == QTextListFormat.ListDecimal)
        else:
            self.act_bullet.setChecked(False)
            self.act_numbered.setChecked(False)


# ---------------------------------------------------------------------------
# Main Editor
# ---------------------------------------------------------------------------

class NoteEditor(QDialog):
    """
    A WYSIWYG Rich Text note editor with a Google-Docs-style toolbar.
    Supports bible: links to jump the reader to references.
    Backward-compatible: loads legacy Markdown text from old notes.
    """
    noteSaved = Signal(str)
    jumpRequested = Signal(str, str, str)  # book, chapter, verse
    DELETE_CODE = 10

    def __init__(self, initial_text="", ref="", parent=None, initial_title=""):
        super().__init__(parent)
        self.setWindowTitle(f"Note - {ref}")
        self.resize(700, 550)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setModal(False)

        self._ref = ref
        self.setObjectName("NoteEditorDialog")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ------------------------------------------------------------------
        # Header bar (ref label + title input)
        # ------------------------------------------------------------------
        header = QWidget()
        header.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #444;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(4)

        if ref:
            ref_label = QLabel(f"📖  {ref}")
            ref_label.setStyleSheet("color: #888; font-size: 11px;")
            header_layout.addWidget(ref_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Note title…")
        self.title_input.setText(initial_title)
        self.title_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                border-bottom: 1px solid #555;
                color: #f0f0f0;
                font-size: 18px;
                font-weight: bold;
                padding: 2px 0;
            }
            QLineEdit:focus {
                border-bottom-color: #007acc;
            }
        """)
        header_layout.addWidget(self.title_input)
        outer.addWidget(header)

        # ------------------------------------------------------------------
        # Rich Text editor
        # ------------------------------------------------------------------
        self.editor = _RichTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.anchorClicked.connect(self._on_link_activated)
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e8e8e8;
                border: none;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 12pt;
                padding: 12px 16px;
                selection-background-color: #264f78;
            }
        """)

        # Toolbar is created AFTER editor so it can reference it
        self.toolbar = _FormattingToolBar(self.editor, self)
        outer.addWidget(self.toolbar)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #3a3a3a;")
        outer.addWidget(line)

        outer.addWidget(self.editor)

        # ------------------------------------------------------------------
        # Bottom action bar
        # ------------------------------------------------------------------
        btn_bar = QWidget()
        btn_bar.setStyleSheet("background-color: #252525; border-top: 1px solid #444;")
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(10, 6, 10, 6)
        btn_layout.setSpacing(8)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: transparent; color: #e57373;
                border: 1px solid #555; border-radius: 4px;
                padding: 5px 12px;
            }
            QPushButton:hover { background: #3a1a1a; border-color: #e57373; }
        """)
        self.btn_delete.clicked.connect(lambda: self.done(self.DELETE_CODE))

        self.btn_save = QPushButton("💾 Save")
        self.btn_save.setDefault(True)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: #005a9e; color: white;
                border: none; border-radius: 4px;
                padding: 5px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #007acc; }
        """)
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent; color: #aaa;
                border: 1px solid #555; border-radius: 4px;
                padding: 5px 12px;
            }
            QPushButton:hover { background: #333; }
        """)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        outer.addWidget(btn_bar)

        # ------------------------------------------------------------------
        # Load initial content
        # ------------------------------------------------------------------
        self._load_content(initial_text)

    # ------------------------------------------------------------------
    # Content loading
    # ------------------------------------------------------------------
    def _load_content(self, text: str):
        """Detect whether *text* is legacy Markdown or saved HTML and load accordingly."""
        if not text:
            return
        if _is_html(text):
            self.editor.setHtml(text)
        else:
            # Load legacy Markdown gracefully via Qt's built-in renderer
            self.editor.setMarkdown(text)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _on_save_clicked(self):
        """Persist the note immediately without closing the panel."""
        self.noteSaved.emit(self.editor.toHtml())

    def get_text(self) -> str:
        """Return the current note body as HTML."""
        return self.editor.toHtml()

    def get_title(self) -> str:
        """Return the current title field value."""
        return self.title_input.text().strip()

    # ------------------------------------------------------------------
    # Link handling
    # ------------------------------------------------------------------
    def _on_link_activated(self, link):
        full_url_str = link.toString() if isinstance(link, QUrl) else str(link)
        if not full_url_str.startswith("bible:"):
            if full_url_str.startswith("http"):
                QDesktopServices.openUrl(QUrl(full_url_str))
            return

        ref_str = (
            full_url_str.split(":", 1)[-1]
            .strip("/")
            .replace("+", " ")
            .replace("%20", " ")
        )

        import re
        parts = re.split(r'[\s:]+', ref_str.strip())

        verse = "1"
        chapter = "1"
        book = ""

        if ":" in ref_str:
            main_part, verse = ref_str.rsplit(":", 1)
            main_parts = main_part.strip().split()
            chapter = main_parts[-1]
            book = " ".join(main_parts[:-1])
        else:
            if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
                verse = parts[-1]
                chapter = parts[-2]
                book = " ".join(parts[:-2])
            elif len(parts) >= 2 and parts[-1].isdigit():
                chapter = parts[-1]
                book = " ".join(parts[:-1])
            else:
                book = ref_str

        self.jumpRequested.emit(book.strip(), chapter.strip(), verse.strip())
