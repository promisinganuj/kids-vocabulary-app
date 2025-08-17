#!/bin/bash

# VCE Vocabulary Flashcard Web Application Startup Script

echo "🚀 Starting VCE Vocabulary Flashcard Web Application..."

# Check if virtual environment exists
if [ ! -d "/Users/anuj/Downloads/.venv" ]; then
    echo "❌ Virtual environment not found at /Users/anuj/Downloads/.venv"
    echo "Please run: python3 -m venv /Users/anuj/Downloads/.venv"
    exit 1
fi

# Activate virtual environment and install requirements
source /Users/anuj/Downloads/.venv/bin/activate

# Install requirements if flask is not installed
if ! python -c "import flask" 2>/dev/null; then
    echo "📦 Installing Flask..."
    pip install flask
fi

echo "🌐 Starting web server..."
echo "📱 Access the application at: http://localhost:5000"
echo "🔧 Management interface at: http://localhost:5000/manage"
echo "⚠️  Press Ctrl+C to stop the server"
echo ""

# Start the Flask application
cd /Users/anuj/Downloads/app
python web_flashcards.py
