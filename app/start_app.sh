#!/bin/bash

# Start the VCE Vocabulary Flashcard Web Application
echo "🚀 Starting VCE Vocabulary Flashcard Web Application..."
echo "📊 Database: $(sqlite3 data/vocabulary.db 'SELECT COUNT(*) FROM tbl_vocab;') words loaded"
echo "🌐 Starting Flask server..."

python web_flashcards.py
