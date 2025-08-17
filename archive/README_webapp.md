# VCE Vocabulary Flashcard Web Application

A dynamic, interactive web application### 🔧 Word Management Interface (/manage)

1. **Adding New Words:**
   - Fill in all required fields (Word, Type, Definition, Example)
   - **Duplicate Prevention**: App warns if word already exists
   - Real-time duplicate checking as you type
   - Click "Add Word" to save
   - Word is immediately added to your vocabulary file

2. **Removing Words:**
   - Use the "Remove" button next to any word
   - Confirm deletion (this action cannot be undone)
   - Word is permanently removed from vocabulary file

3. **Searching:**
   - Use the search bar to filter the word table
   - Search works across all fields (word, type, definition, example)nd studying VCE vocabulary words. This Flask-based application allows you to add new words, remove learned ones, and interact with flashcards in real-time.

## Features

### 🃏 Interactive Flashcards
- **Flip Cards**: Click any card to see the definition and example
- **Hide/Show**: Mark words as learned by hiding them (click × button)
- **Search**: Find specific words, definitions, or examples
- **Shuffle**: Randomize card order for varied practice
- **Bulk Actions**: Show/hide all cards at once

### 🔧 Word Management
- **Add Words**: Add new vocabulary with word, type, definition, and example
- **Remove Words**: Delete words you've mastered permanently
- **Real-time Updates**: Changes are instantly reflected and saved to file
- **Backup System**: Automatic backups created before file modifications

### 📊 Statistics & Tracking
- **Live Stats**: Track total, visible, and hidden word counts
- **Progress Monitoring**: See your learning progress in real-time
- **Search Filtering**: Filter words by any criteria

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- Virtual environment (recommended)

### Quick Start

1. **Navigate to the app directory:**
   ```bash
   cd /Users/anuj/Downloads/app
   ```

2. **Run the startup script:**
   ```bash
   ./start_webapp.sh
   ```

3. **Access the application:**
   - Main flashcards: http://localhost:5000
   - Manage words: http://localhost:5000/manage

### Manual Installation

If you prefer manual setup:

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv /Users/anuj/Downloads/.venv
   source /Users/anuj/Downloads/.venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install flask
   ```

3. **Run the application:**
   ```bash
   python web_flashcards.py
   ```

## Usage Guide

### Main Flashcard Interface (/)

1. **Studying Words:**
   - Click any card to flip between word and definition/example
   - Use search bar to find specific words
   - Hide words you've learned using the × button

2. **Control Buttons:**
   - **Show Words**: Display word side of all cards
   - **Show Definitions**: Display definition side of all cards
   - **Shuffle**: Randomize card order
   - **Show All**: Make all hidden cards visible
   - **Hide All**: Hide all cards

### Management Interface (/manage)

1. **Adding New Words:**
   - Fill in all required fields (Word, Type, Definition, Example)
   - Click "Add Word" to save
   - Word is immediately added to your vocabulary file

2. **Removing Words:**
   - Use the "Remove" button next to any word
   - Confirm deletion (this action cannot be undone)
   - Word is permanently removed from vocabulary file

3. **Searching:**
   - Use the search bar to filter the word table
   - Search works across all fields (word, type, definition, example)

## File Structure

```
app/
├── web_flashcards.py          # Main Flask application
├── templates/
│   ├── flashcards.html        # Main flashcard interface
│   └── manage.html            # Word management interface
├── convert_vocabulary.py      # Format conversion script
├── start_webapp.sh            # Startup script
├── requirements.txt           # Python dependencies
└── README_webapp.md           # This file

Parent Directory:
├── new-words.txt              # Vocabulary data file (unnumbered format)
└── new-words.txt.backup_*     # Automatic backups
```

## API Endpoints

The application provides REST API endpoints for programmatic access:

- `GET /api/words` - Retrieve all words (with optional search parameter)
- `POST /api/words` - Add a new word
- `DELETE /api/words/<id>` - Remove a word by ID

## Data Format

Vocabulary words are stored in `new-words.txt` with the simplified format:
```
Word (type) - Definition - Example sentence.
Another (noun) - Its definition - An example using the word.
```

**Note**: The app automatically prevents duplicate entries and maintains a clean, unnumbered format.

## Migration from Numbered Format

If you have an existing vocabulary file with numbered entries, use the conversion script:

```bash
cd /Users/anuj/Downloads/app
python3 convert_vocabulary.py
```

This will:
- Remove numbering from entries
- Eliminate duplicate words (case-insensitive)
- Create a backup of your original file
- Maintain full compatibility with the web app

## Backup System

- Automatic backups are created before any modifications
- Backup files are named: `new-words.txt.backup_YYYYMMDD_HHMMSS`
- Original file structure is preserved

## Features in Detail

### Smart Search
- Search across all word properties
- Real-time filtering as you type
- Case-insensitive matching

### Visual Feedback
- Hidden cards become transparent and grayscale
- Hover effects for better interactivity
- Color-coded buttons for different actions

### Responsive Design
- Works on desktop, tablet, and mobile devices
- Adaptive layouts for different screen sizes
- Touch-friendly interface

### Data Persistence
- All changes are automatically saved to file
- Maintains original file format compatibility
- Works with existing `generate_flashcards.py` files

## Troubleshooting

### Common Issues

1. **"Module not found" error:**
   - Ensure Flask is installed: `pip install flask`
   - Check that you're using the correct Python environment

2. **Port already in use:**
   - Change the port in `web_flashcards.py`: `app.run(port=5001)`
   - Or kill the existing process using port 5000

3. **File permission errors:**
   - Ensure the app has write permissions to the parent directory
   - Check that `new-words.txt` is not locked by another application

4. **Empty word list:**
   - Check that `new-words.txt` exists in the parent directory
   - Verify the file format matches the expected pattern

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Ensure all dependencies are installed
3. Verify file permissions and paths
4. Check browser console for JavaScript errors

## Development Notes

- Built with Flask (Python web framework)
- Uses Jinja2 templating for dynamic HTML
- Vanilla JavaScript for client-side interactivity
- CSS Grid and Flexbox for responsive layouts
- RESTful API design for future extensibility

## Future Enhancements

Potential improvements for future versions:
- User accounts and progress tracking
- Export functionality (PDF, CSV)
- Spaced repetition algorithms
- Audio pronunciation
- Multiple vocabulary sets
- Import from external sources
- Advanced statistics and analytics

---

**Enjoy studying with your interactive vocabulary flashcards! 📚✨**
