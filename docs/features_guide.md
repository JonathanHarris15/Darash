# Jehu-Reader: Features & Usage Guide

Welcome to **Jehu-Reader**, a powerful Bible study application designed for deep analysis, cross-referencing, and structural outlining. This guide explains the core features of the application and how to use them effectively.

---

## 📖 Bible Reading & Navigation

### Multi-Translation Support
Jehu-Reader allows you to view multiple translations side-by-side or stacked.
- **How to use**: Click the translation selector in the navigation bar to toggle translations. You can drag and drop translations in the selector to reorder them.

### Chapter Navigation
Navigate through the Bible with ease.
- **Navigation Bar**: Use the book and chapter dropdowns at the top of the reading view. Use the **Prev** and **Next** buttons for quick sequential reading.
- **Bookmarks**: Save specific locations for quick access later. Use the **Bookmarks Panel** in the sidebar to manage and jump to your saved verses.

### Jump Scrollbar
The custom scrollbar on the right of the reading view provides a bird's-eye view of the current book.
- **Ticks**: Markers indicate chapter boundaries.
- **Search Results**: Search matches appear as highlights on the scrollbar for easy navigation.

---

## 🔍 Advanced Search

Jehu-Reader features a robust search engine with logical operators.

### Search Operators
- `AND`: Find verses containing both terms (e.g., `faith AND works`).
- `OR`: Find verses containing either term (e.g., `grace OR mercy`).
- `NOT`: Exclude terms (e.g., `spirit NOT soul`).
- **Grouping**: Use parentheses for complex queries (e.g., `(faith AND works) OR love`).

### Scoped Search
You can limit your search to a specific range:
- **Verse**: Search within the current verse.
- **Chapter**: Search within the current chapter.
- **Book**: Search within the current book.
- **Global**: Search the entire Bible.

---

## 🛠️ Study Tools

### Marks & Highlighting
Highlight key words or phrases with customizable colors and styles.
- **How to use**: Right-click a selected word or verse and choose a color from the **Mark Popup**.

### Symbols
Attach icons to verses to represent themes or concepts.
- **How to use**: Right-click a verse and select "Add Symbol". Choose from the built-in library or use AI-based **Suggested Symbols**.

### Arrows & Relationship Tracing
Draw connections between words or verses to visualize relationships.
- **Ghost Arrows**: When you hover over a word, "ghost" icons appear. Drag from these icons to start drawing an arrow.
- **Snaking Paths**: Arrows automatically "snake" around text blocks to keep the layout clean.

### Sentence Breaking
Toggle "Break at Sentences" to split verses into individual sentences for more granular study and indentation.

---

## 📝 Organization & Outlining

### Book Outlines
Create hierarchical structures for any book of the Bible.
- **Creating an Outline**: Use the **Study Overview** sidebar to create a new outline. 
- **Editing**: In the **Outline Panel**, you can add sections, split verses into those sections, and nest headings to build a tree structure.

### Rich Text Notes
Keep detailed notes alongside your study.
- **Rich Text Editor**: Supports bold, italics, links, and indented lists.
- **Verse Links**: Notes can be linked to specific verses for quick reference.

---

## 🖥️ Layout & UI Customization

### Split Views
Working with multiple passages? Split the central view.
- **How to use**: Drag and drop panels or use the split buttons to create horizontal or vertical splits.
- **Linked Scrolling**: Use the link button between split views to synchronize their scrolling.

### Appearance Settings
Customize the look and feel to your preference.
- **Panel**: Access the **Appearance Panel** to change fonts, font sizes, line spacing, and color themes.

### Activity Bar
The sidebar icon bar (similar to VS Code) lets you quickly toggle between the **Study Overview**, **Bookmarks**, **Strong's Dictionary**, and **Settings**.

---

## 💾 Data & Export

### Persistent Studies
All your marks, symbols, arrows, notes, and outlines are automatically saved to your `study.json` file. The application supports full Undo/Redo for most study actions.

### Exporting Content
Ready to share or print your work?
- **Export Formats**: Export your **Notes** and **Outlines** to **PDF** or **DOCX**.
- **Options**: Customize margins, fonts, and which elements to include in the final export via the **Export Dialog**.
