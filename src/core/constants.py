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
    {"name": "Torah", "books": ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"], "color": "#ff6464"},
    {"name": "History", "books": ["Joshua", "Judges", "Ruth", "I Samuel", "II Samuel", "I Kings", "II Kings", "I Chronicles", "II Chronicles", "Ezra", "Nehemiah", "Esther"], "color": "#64ff64"},
    {"name": "Poetry", "books": ["Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon"], "color": "#ffff64"},
    {"name": "Prophets", "books": ["Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"], "color": "#6464ff"},
    {"name": "Gospels", "books": ["Matthew", "Mark", "Luke", "John", "Acts"], "color": "#ff64ff"},
    {"name": "Letters", "books": ["Romans", "I Corinthians", "II Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians", "I Thessalonians", "II Thessalonians", "I Timothy", "II Timothy", "Titus", "Philemon", "Hebrews", "James", "I Peter", "II Peter", "I John", "II John", "III John", "Jude", "Revelation of John"], "color": "#64ffff"}
]

# Application Info
APP_VERSION = "0.1.2"
GITHUB_REPO = "JonathanHarris15/Darash"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Layout Constants
SCROLL_SENSITIVITY = 120.0
RESIZE_DEBOUNCE_INTERVAL = 200  # ms
LAYOUT_DEBOUNCE_INTERVAL = 500  # ms
VERSE_NUMBER_RESERVED_WIDTH = 30
