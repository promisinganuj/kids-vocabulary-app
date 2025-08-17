#!/bin/bash

# Start the VCE Vocabulary Flashcard Multi-User Web Application
echo "🚀 Starting VCE Vocabulary Flashcard Multi-User Web Application..."

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
if [ ! -f "data/vocabulary_multiuser.db" ]; then
    echo "🔧 Initializing multi-user database..."
    python -c "from multi_user_database_manager import MultiUserDatabaseManager; import os; MultiUserDatabaseManager(os.path.join('data', 'vocabulary_multiuser.db'))"
fi

# Display database stats
echo "📊 Multi-user database status:"
echo "   Users: $(sqlite3 data/vocabulary_multiuser.db 'SELECT COUNT(*) FROM users;')"
echo "   Total words: $(sqlite3 data/vocabulary_multiuser.db 'SELECT COUNT(*) FROM vocabulary;')"
echo "   Base vocabulary: $(sqlite3 data/vocabulary_multiuser.db 'SELECT COUNT(*) FROM base_vocabulary;')"
echo "🌐 Starting Flask multi-user server on http://localhost:5001..."

python web_flashcards_multiuser.py
