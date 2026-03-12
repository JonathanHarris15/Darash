import sys, os, tempfile, base64
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTextDocument, QImage, QPainter, QColor
from PySide6.QtCore import QUrl, QRectF, QSizeF

def run():
    app = QApplication(sys.argv)
    doc = QTextDocument()

    png_path = r"c:\Users\jono1\OneDrive\Documents\Personal Projects\Jehu-Reader\symbols_library\images\Christ-Symbol.png"

    with open(png_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    # Attempt 1: Raw path
    # Attempt 2: file:/// with forward slashes
    # Attempt 3: base64
    html = f"""
    <body>
        <p>Raw path: <br><img src="{png_path}" width="50" height="50"/></p>
        <p>File URI: <br><img src="file:///{png_path.replace(chr(92), '/')}" width="50" height="50"/></p>
        <p>Base64: <br><img src="data:image/png;base64,{b64}" width="50" height="50"/></p>
    </body>
    """
    doc.setHtml(html)

    # Draw it
    doc.setPageSize(QSizeF(400, 600))
    img = QImage(400, 600, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    painter = QPainter(img)
    doc.drawContents(painter)
    painter.end()

    img.save("qt_img_test.png")
    print("Saved to qt_img_test.png")

if __name__ == "__main__":
    run()
