import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage

def run():
    app = QApplication(sys.argv)
    img = QImage("qt_img_test.png")
    
    found_pixels = []
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y).name()
            # If it's not white and not black, it's part of the symbol (the symbol is colorful, or at least gray due to anti-aliasing)
            if c != "#ffffff" and c != "#000000" and c != "#ff0000": 
                found_pixels.append(y)
                break
                
    # Let's see at what Y coordinates the pixels start
    # The image has 3 lines: 
    # y~30: raw path
    # y~100: file URI
    # y~170: base64
    
    clusters = []
    if found_pixels:
        current_cluster = [found_pixels[0]]
        for y in found_pixels[1:]:
            if y - current_cluster[-1] < 10:
                current_cluster.append(y)
            else:
                clusters.append(current_cluster)
                current_cluster = [y]
        clusters.append(current_cluster)
        
    print(f"Total non-W/B pixel rows: {len(found_pixels)}")
    for i, c in enumerate(clusters):
        print(f"Cluster {i+1}: Y={c[0]} to Y={c[-1]}")

if __name__ == "__main__":
    run()
