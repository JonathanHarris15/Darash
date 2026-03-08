import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QSpinBox, QCheckBox, QGroupBox, QFileDialog, 
    QScrollArea, QFrame, QWidget, QDoubleSpinBox, QColorDialog,
    QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QSizeF, QRectF
from PySide6.QtGui import QPixmap, QImage, QPainter, QTextDocument, QPageLayout, QPageSize, QColor
from src.utils.exporter import Exporter

class ExportDialog(QDialog):
    """
    Popup for exporting content (Notes, Outlines).
    Left: Preview of PDF
    Right: Options
    Bottom Right: Download path & Export
    """
    
    updateNeeded = Signal()

    def __init__(self, export_type="Notes", parent=None, **kwargs):
        super().__init__(parent)
        self.setWindowTitle(f"Export {export_type}")
        self.setMinimumSize(900, 600)
        self.export_type = export_type
        self.output_path = ""
        self.content_html = "" # This will be set by the caller
        self.content_data = [] # For DOCX export
        self.kwargs = kwargs
        
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        
        # --- Left Side: Preview ---
        preview_container = QVBoxLayout()
        self.preview_label = QLabel("Loading preview...")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumWidth(400)
        self.preview_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        preview_container.addWidget(scroll_area)
        
        main_layout.addLayout(preview_container, 2)
        
        # --- Right Side: Options ---
        options_container = QVBoxLayout()
        
        self.options_group = QGroupBox("PDF Options")
        options_layout = QVBoxLayout(self.options_group)
        
        # Common Options
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        
        options_layout.addWidget(QLabel("Font Size:"))
        options_layout.addWidget(self.font_size_spin)
        
        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(1.0, 3.0)
        self.line_spacing_spin.setSingleStep(0.1)
        self.line_spacing_spin.setValue(1.2)
        self.line_spacing_spin.valueChanged.connect(self.update_preview)
        
        options_layout.addWidget(QLabel("Line Spacing:"))
        options_layout.addWidget(self.line_spacing_spin)
        
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Portrait", "Landscape"])
        self.orientation_combo.currentIndexChanged.connect(self.update_preview)
        options_layout.addWidget(QLabel("Orientation:"))
        options_layout.addWidget(self.orientation_combo)
        
        # Type Specific Options
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PDF", "DOCX"])
        options_layout.addWidget(QLabel("Export Format:"))
        options_layout.addWidget(self.format_combo)
            
        options_layout.addStretch()
        options_container.addWidget(self.options_group)
        
        # --- Bottom Right: Buttons ---
        button_layout = QHBoxLayout()
        self.path_btn = QPushButton("Set Download Path")
        self.path_btn.clicked.connect(self.select_path)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.do_export)
        self.export_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        button_layout.addWidget(self.path_btn)
        button_layout.addWidget(self.export_btn)
        options_container.addLayout(button_layout)
        
        main_layout.addLayout(options_container, 1)
        
    def set_content(self, html, data=None):
        self.content_html = html
        self.content_data = data or []
        self.update_preview()
        
    def update_preview(self):
        """Generates a paginated preview of the exported document."""
        if not self.content_html:
            return
            
        doc = QTextDocument()
        font_size = self.font_size_spin.value()
        font_family = self.kwargs.get("font_family", "Times New Roman")
        
        base_style = f"""
            <style>
                body {{
                    font-family: '{font_family}';
                    font-size: {font_size}pt;
                    line-height: {self.line_spacing_spin.value()};
                    color: black;
                    background-color: white;
                }}
            </style>
        """
        
        html = self.content_html
            
        doc.setHtml(f"<html><head>{base_style}</head><body>{html}</body></html>")
        
        resources = getattr(self.export_manager, "_current_export_resources", {})
        if resources:
            from PySide6.QtCore import QUrl
            for res_id, res_img in resources.items():
                doc.addResource(QTextDocument.ImageResource, QUrl(res_id), res_img)
        
        # Dimensions based on basic Letter size at 100dpi
        page_w = 850
        page_h = 1100
        if self.orientation_combo.currentText() == "Landscape":
            page_w, page_h = page_h, page_w
            
        # Margins (approximate 1 inch at 100dpi)
        margin = 100
        content_w = page_w - (margin * 2)
        content_h = page_h - (margin * 2)
        
        doc.setPageSize(QSizeF(content_w, content_h))
        page_count = doc.pageCount()
        
        gap = 40
        total_height = int((page_count * page_h) + ((page_count + 1) * gap))
        
        image = QImage(page_w + (gap * 2), total_height, QImage.Format_RGB32)
        image.fill(QColor("#dddddd")) # Gray background outside pages
        
        painter = QPainter(image)
        for i in range(page_count):
            page_rect = QRectF(gap, gap + i * (page_h + gap), page_w, page_h)
            painter.fillRect(page_rect, Qt.white)
            
            # Translate to draw document content within the margins of this page
            painter.save()
            painter.translate(gap + margin, page_rect.top() + margin - (i * content_h))
            
            clip_rect = QRectF(0, i * content_h, content_w, content_h)
            doc.drawContents(painter, clip_rect)
            painter.restore()
            
        painter.end()
        
        pixmap = QPixmap.fromImage(image)
        
        label_width = self.preview_label.width()
        if label_width < 200:
            label_width = 400
            
        self.preview_label.setPixmap(pixmap.scaledToWidth(label_width - 30, Qt.SmoothTransformation))
        
    def select_path(self):
        ext = "pdf"
        if hasattr(self, "format_combo") and self.format_combo.currentText() == "DOCX":
            ext = "docx"
            
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", f"{ext.upper()} Files (*.{ext})")
        if path:
            self.output_path = path
            self.path_btn.setText(os.path.basename(path))
            
    def do_export(self):
        if not self.output_path:
            self.select_path()
            if not self.output_path:
                return
                
        options = {
            "font_size": self.font_size_spin.value(),
            "line_spacing": self.line_spacing_spin.value(),
            "orientation": self.orientation_combo.currentText(),
            "font_family": self.kwargs.get("font_family", "Times New Roman"),
        }
        
        try:
            is_docx = hasattr(self, "format_combo") and self.format_combo.currentText() == "DOCX"
            if is_docx:
                Exporter.export_to_docx(self.content_html, self.output_path, options)
            else:
                if self.export_type == "Notes":
                    html = self.export_manager._extract_notes_html()
                else:
                    html, _ = self.export_manager._extract_outline_data()
                    
                resources = getattr(self.export_manager, "_current_export_resources", {})
                Exporter.export_to_pdf(html, self.output_path, options, resources)
            self.accept()
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Export Failed", f"An error occurred during export: {str(e)}")
