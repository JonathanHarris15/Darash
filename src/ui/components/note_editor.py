from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QWidget, QFrame, QToolButton, QMenu
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices

from src.ui.components.rich_text_edit import RichTextEdit
from src.ui.components.formatting_toolbar import FormattingToolBar
from src.ui.components.spellcheck_title_edit import SpellcheckTitleEdit

def _is_html(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped.startswith("<!doctype") or stripped.startswith("<html")

class NoteEditor(QDialog):
    """A WYSIWYG Rich Text note editor. Supports bible: links. Backward-compatible with Markdown."""
    noteSaved = Signal(str)
    jumpRequested = Signal(str, str, str)
    exportRequested = Signal()
    DELETE_CODE = 10

    def __init__(self, initial_text="", ref="", parent=None, initial_title=""):
        super().__init__(parent)
        self.setWindowTitle(f"Note - {ref}"); self.resize(700, 550); self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint); self.setModal(False)
        self._ref = ref; self.setObjectName("NoteEditorDialog")
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)

        header = QWidget(); header.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #444;")
        h_lay = QVBoxLayout(header); h_lay.setContentsMargins(10, 8, 10, 8); h_lay.setSpacing(4)
        if ref:
            rl = QLabel(f"📖  {ref}"); rl.setStyleSheet("color: #888; font-size: 11px;"); h_lay.addWidget(rl)
        t_row = QHBoxLayout(); self.title_input = SpellcheckTitleEdit(); self.title_input.setPlaceholderText("Note title…"); self.title_input.setText(initial_title)
        self.title_input.setStyleSheet("QTextEdit { background: transparent; border: none; border-bottom: 1px solid #555; color: #f0f0f0; font-size: 18px; font-weight: bold; padding: 2px 0; } QTextEdit:focus { border-bottom-color: #007acc; }")
        t_row.addWidget(self.title_input, 1)
        self.menu_btn = QToolButton(); self.menu_btn.setText("⋮"); self.menu_btn.setStyleSheet("QToolButton { background: transparent; color: #888; font-size: 18px; border: none; } QToolButton:hover { color: white; }")
        self.menu_btn.setPopupMode(QToolButton.InstantPopup); self.menu_btn.setMenu(self._build_export_menu())
        t_row.addWidget(self.menu_btn); h_lay.addLayout(t_row); outer.addWidget(header)

        from src.managers.spellcheck_manager import SpellcheckManager
        self.editor = RichTextEdit(); self.editor.setAcceptRichText(True); self.editor.anchorClicked.connect(self._on_link_activated)
        self.editor.enableSpellcheck(SpellcheckManager.get_instance())
        self.editor.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #e8e8e8; border: none; font-family: 'Segoe UI', 'Arial', sans-serif; font-size: 12pt; padding: 12px 16px; selection-background-color: #264f78; }")
        self.toolbar = FormattingToolBar(self.editor, self); outer.addWidget(self.toolbar)
        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("color: #3a3a3a;"); outer.addWidget(line); outer.addWidget(self.editor)

        btn_bar = QWidget(); btn_bar.setStyleSheet("background-color: #252525; border-top: 1px solid #444;")
        b_lay = QHBoxLayout(btn_bar); b_lay.setContentsMargins(10, 6, 10, 6); b_lay.setSpacing(8)
        self.btn_delete = QPushButton("🗑 Delete"); self.btn_delete.setStyleSheet("QPushButton { background: transparent; color: #e57373; border: 1px solid #555; border-radius: 4px; padding: 5px 12px; } QPushButton:hover { background: #3a1a1a; border-color: #e57373; }"); self.btn_delete.clicked.connect(lambda: self.done(self.DELETE_CODE))
        self.btn_save = QPushButton("💾 Save"); self.btn_save.setDefault(True); self.btn_save.setStyleSheet("QPushButton { background: #005a9e; color: white; border: none; border-radius: 4px; padding: 5px 16px; font-weight: bold; } QPushButton:hover { background: #007acc; }"); self.btn_save.clicked.connect(lambda: self.noteSaved.emit(self.editor.toHtml()))
        self.btn_can = QPushButton("Cancel"); self.btn_can.setStyleSheet("QPushButton { background: transparent; color: #aaa; border: 1px solid #555; border-radius: 4px; padding: 5px 12px; } QPushButton:hover { background: #333; }"); self.btn_can.clicked.connect(self.reject)
        b_lay.addWidget(self.btn_delete); b_lay.addStretch(); b_lay.addWidget(self.btn_can); b_lay.addWidget(self.btn_save); outer.addWidget(btn_bar)

        if initial_text:
            if _is_html(initial_text): self.editor.setHtml(initial_text)
            else: self.editor.setMarkdown(initial_text)

    def _build_export_menu(self):
        m = QMenu(self); m.setStyleSheet("QMenu { background-color: #252525; color: #ccc; border: 1px solid #444; } QMenu::item:selected { background-color: #333; }")
        a = QAction("📤 Export Note...", self); a.triggered.connect(self.exportRequested.emit); m.addAction(a); return m

    def get_text(self) -> str: return self.editor.toHtml()
    def get_title(self) -> str: return self.title_input.text().strip()

    def _on_link_activated(self, link):
        url = link.toString() if isinstance(link, QUrl) else str(link)
        if not url.startswith("bible:"):
            if url.startswith("http"): QDesktopServices.openUrl(QUrl(url))
            return
        ref = url.split(":", 1)[-1].strip("/").replace("+", " ").replace("%20", " ")
        import re; parts = re.split(r'[\s:]+', ref.strip()); v, c, b = "1", "1", ""
        if ":" in ref:
            m, v = ref.rsplit(":", 1); mp = m.strip().split(); c = mp[-1]; b = " ".join(mp[:-1])
        else:
            if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit(): v, c, b = parts[-1], parts[-2], " ".join(parts[:-2])
            elif len(parts) >= 2 and parts[-1].isdigit(): c, b = parts[-1], " ".join(parts[:-1])
            else: b = ref
        self.jumpRequested.emit(b.strip(), c.strip(), v.strip())
