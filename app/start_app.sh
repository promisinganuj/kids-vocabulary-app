#!/bin/bash

# Start the VCE Vocabulary Flashcard Web Application
echo "🚀 Starting VCE Vocabulary Flashcard Web Application..."

# Change to the app directory
cd "$(dirname "$0")" || exit 1

# Go back to project root to activate virtual environment
cd .. || exit 1

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate
fi

# Go back to app directory
cd app || exit 1

echo "📊 Database: $(sqlite3 data/vocabulary.db 'SELECT COUNT(*) FROM tbl_vocab;') words loaded"
echo "🌐 Starting Flask server..."

python web_flashcards.py
