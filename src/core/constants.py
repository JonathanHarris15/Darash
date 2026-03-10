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
LOGICAL_MARK_COLOR = QColor("white")
LOGICAL_MARK_OPACITY_DEFAULT = 0.5

HIGHLIGHT_COLORS = {
    "yellow": "#FFFF00",
    "green": "#00FF00",
    "blue": "#00FFFF",
    "pink": "#FF00FF",
    "orange": "#FFA500"
}

LOGICAL_MARKS = {
    "arrow_right": "→",
    "arrow_left": "←",
    "arrow_parallel_right": "⇒",
    "arrow_parallel_left": "⇐",
    "arrow_diverge": "↔",
    "arrow_converge": "→←", 
    "equals": "=",
    "plus": "+",
    "question": "?",
    "therefore": "∴",
    "because": "∵"
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
TAB_SIZE_DEFAULT = 40
VERSE_NUMBER_RESERVED_WIDTH = 30
ARROW_OPACITY_DEFAULT = 0.6
VERSE_MARK_SIZE_DEFAULT = 18
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

BIBLE_SECTIONS = [
    {"name": "Torah", "books": ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"], "color": QColor(255, 100, 100, 150)},
    {"name": "History", "books": ["Joshua", "Judges", "Ruth", "I Samuel", "II Samuel", "I Kings", "II Kings", "I Chronicles", "II Chronicles", "Ezra", "Nehemiah", "Esther"], "color": QColor(100, 255, 100, 150)},
    {"name": "Poetry", "books": ["Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon"], "color": QColor(255, 255, 100, 150)},
    {"name": "Prophets", "books": ["Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"], "color": QColor(100, 100, 255, 150)},
    {"name": "Gospels", "books": ["Matthew", "Mark", "Luke", "John", "Acts"], "color": QColor(255, 100, 255, 150)},
    {"name": "Letters", "books": ["Romans", "I Corinthians", "II Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "I Thessalonians", "II Thessalonians", "I Timothy", "II Timothy", "Titus", "Philemon", "Hebrews", "James", "I Peter", "II Peter", "I John", "II John", "III John", "Jude", "Revelation of John"], "color": QColor(100, 255, 255, 150)}
]

# Application Info
APP_VERSION = "0.1.2"
GITHUB_REPO = "JonathanHarris15/Darash"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
