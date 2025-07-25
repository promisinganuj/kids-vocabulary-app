# VCE Vocabulary Flashcard Generator

This Python application automatically generates interactive HTML flashcards from a vocabulary word list.

## Features

- 🃏 Interactive flashcards with click-to-flip functionality
- 🔍 Search functionality to find specific words
- 🎲 Shuffle cards for random practice
- 📱 Responsive design that works on mobile and desktop
- 🕒 Unique timestamp suffixes for each generated file
- 📊 Real-time word count and statistics

## Files

- `generate_flashcards.py` - Main Python script that generates HTML flashcards
- `../new-words.txt` - Source file containing vocabulary words (format: Word (Type) - Definition - Example)

## How to Use

1. **Run the generator:**
   ```bash
   python generate_flashcards.py
   ```

2. **Open the generated HTML file:**
   - The script will create a new HTML file with timestamp suffix
   - Open the file in your web browser
   - Example: `vce_vocabulary_flashcard_20250724_143022.html`

## Input Format

The `new-words.txt` file should follow this format:
```
1. Scrutinize (Verb) - To examine closely and critically - The detective scrutinized every piece of evidence for clues.
2. Perpetuate (Verb) - To make something continue indefinitely - The stereotypes perpetuated by the media harm minority communities.
```

Each line should contain:
- Number followed by period
- Word name
- Part of speech in parentheses
- Definition after first dash
- Example sentence after second dash

## Generated Features

The HTML flashcards include:
- **Interactive Cards:** Click any card to flip between word and definition
- **Search:** Type to search words, definitions, or examples
- **Controls:** Show all words, show all definitions, shuffle cards
- **Responsive Design:** Works on mobile and desktop devices
- **Statistics:** Display total word count and filtered results

## Requirements

- Python 3.6 or higher
- No external dependencies required (uses only standard library)

## Output

Each run generates a unique HTML file in the `app` directory with:
- Current timestamp in filename
- All vocabulary words from the source file
- Complete interactive functionality
- Generation timestamp displayed in the file

---

**Author:** VCE Vocabulary Flashcard Generator  
**Date:** 2025  
**Version:** 1.0
