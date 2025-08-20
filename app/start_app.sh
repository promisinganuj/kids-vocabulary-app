#!/bin/bash

# Start the Vocabulary Flashcard Multi-User Web Application
echo "🚀 Starting Vocabulary Flashcard Multi-User Web Application..."

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

# Check if multi-user database exists, if not initialize it
if [ ! -f "data/vocabulary.db" ]; then
    echo "🔧 Initializing database..."
    python -c "from database_manager import DatabaseManager; import os; DatabaseManager(os.path.join('data', 'vocabulary.db'))"
fi

# Display database stats
echo "📊 Database status:"
echo "   Users: $(sqlite3 data/vocabulary.db 'SELECT COUNT(*) FROM users;')"
echo "   Total words: $(sqlite3 data/vocabulary.db 'SELECT COUNT(*) FROM vocabulary;')"
echo "   Base vocabulary: $(sqlite3 data/vocabulary.db 'SELECT COUNT(*) FROM base_vocabulary;')"
echo "🌐 Starting Flask multi-user server on http://localhost:5001..."

python web_flashcards.py
