from PySide6.QtGui import QColor

# UI Colors
APP_BACKGROUND_COLOR = QColor(30, 30, 30)
TEXT_COLOR = QColor(220, 220, 220)
REFERENCE_COLOR = QColor(100, 200, 255)
VERSE_NUM_COLOR = QColor(150, 150, 150)
HUD_BACKGROUND_COLOR = "rgba(30, 30, 30, 200)"
OVERLAY_BACKGROUND_COLOR = "#1e1e1e"
SEARCH_HIGHLIGHT_COLOR = QColor(255, 255, 0, 100)  # Translucent yellow
SELECTION_COLOR = QColor(0, 120, 215, 150)        # Translucent blue

HIGHLIGHT_COLORS = {
    "yellow": "#FFFF00",
    "green": "#00FF00",
    "blue": "#00FFFF",
    "pink": "#FF00FF",
    "orange": "#FFA500"
}

# Study Paths
DEFAULT_STUDIES_DIR = "studies"
SYMBOLS_DIR_NAME = "symbols"

# Fonts
DEFAULT_FONT_FAMILY = "Montserrat"
VERSE_FONT_FAMILY = "Times New Roman"
DEFAULT_FONT_SIZE = 18
HEADER_FONT_SIZE = 36
CHAPTER_FONT_SIZE = 24

# Layout Constants
LINE_SPACING_DEFAULT = 1.5
SCROLL_SENSITIVITY = 120.0
SIDE_MARGIN = 40
TOP_MARGIN = 50.0
RESIZE_DEBOUNCE_INTERVAL = 200  # ms
LAYOUT_DEBOUNCE_INTERVAL = 500  # ms

# Bible Metadata
OT_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", 
    "Joshua", "Judges", "Ruth", "I Samuel", "II Samuel", 
    "I Kings", "II Kings", "I Chronicles", "II Chronicles", "Ezra", 
    "Nehemiah", "Esther", "Job", "Psalms", "Proverbs", 
    "Ecclesiastes", "Song of Solomon", "Isaiah", "Jeremiah", 
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", 
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", 
    "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"
]

NT_BOOKS = [
    "Matthew", "Mark", "Luke", "John", "Acts", 
    "Romans", "I Corinthians", "II Corinthians", "Galatians", "Ephesians", 
    "Philippians", "Colossians", "I Thessalonians", "II Thessalonians", 
    "I Timothy", "II Timothy", "Titus", "Philemon", "Hebrews", 
    "James", "I Peter", "II Peter", "I John", "II John", 
    "III John", "Jude", "Revelation of John"
]
