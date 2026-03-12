from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from src.core.theme import Theme

class ReleaseNoteDialog(QDialog):
    """
    A styled dialog for displaying release notes in markdown format.
    Matches the application theme and provides a clean reading experience.
    """
    def __init__(self, parent=None, content: str = "", version: str = ""):
        super().__init__(parent)
        self.setWindowTitle(f"What's New in v{version}")
        self.setMinimumSize(600, 500)
        self.init_ui(content)
        self.apply_styles()

    def init_ui(self, content):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Markdown Browser
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        # Use setMarkdown for automatic rendering of markdown content
        self.browser.setMarkdown(content)
        
        # Override browser's internal stylesheet for better markdown rendering
        self.browser.document().setDefaultStyleSheet(f"""
            h1 {{ color: {Theme.ACCENT_PRIMARY}; font-size: 24px; margin-bottom: 10px; }}
            h2 {{ color: {Theme.ACCENT_GOLD}; font-size: 20px; margin-top: 15px; margin-bottom: 5px; }}
            h3 {{ color: {Theme.TEXT_PRIMARY}; font-size: 18px; }}
            li {{ color: {Theme.TEXT_PRIMARY}; margin-bottom: 5px; }}
            p {{ color: {Theme.TEXT_PRIMARY}; line-height: 1.5; }}
            code {{ background-color: {Theme.BG_TERTIARY}; padding: 2px 4px; border-radius: 3px; font-family: '{Theme.FONT_MONO}'; }}
        """)
        
        layout.addWidget(self.browser)

        # Footer with Close Button
        footer_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("Got it!")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setFixedWidth(140)
        self.close_btn.clicked.connect(self.accept)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.close_btn)
        footer_layout.addStretch()
        
        layout.addLayout(footer_layout)

    def apply_styles(self):
        # Global dialog styles
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Theme.BG_PRIMARY};
                border: 1px solid {Theme.BORDER_DEFAULT};
            }}
            QTextBrowser {{
                background-color: {Theme.BG_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 20px;
                font-family: '{Theme.FONT_UI}';
            }}
            QPushButton {{
                background-color: {Theme.ACCENT_PRIMARY};
                color: {Theme.BG_PRIMARY};
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {Theme.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Theme.ACCENT_PRIMARY};
                opacity: 0.8;
            }}
        """)
