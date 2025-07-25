#!/bin/bash

# Azure App Service startup script
echo "🚀 Starting VCE Vocabulary Flashcards on Azure..."

# Create data directory if it doesn't exist
mkdir -p data

# Copy vocabulary file if it exists
if [ -f "new-words.txt" ]; then
    echo "📖 Copying vocabulary file to data directory..."
    cp new-words.txt data/
fi

# Start the application with Gunicorn
echo "🌐 Starting Gunicorn server..."
gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:application
