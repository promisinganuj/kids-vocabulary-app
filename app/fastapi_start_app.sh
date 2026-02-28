#!/bin/bash

# Start the Vocabulary Flashcard Multi-User Web Application (FastAPI)
echo "🚀 Starting Vocabulary Flashcard Multi-User Web Application (FastAPI)..."

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

# Load environment from .env if present
if [ -f ".env" ]; then
    echo "🔧 Loading .env configuration..."
    set -a
    source .env
    set +a
fi

# Verify DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is not set. Please set it in .env or environment."
    exit 1
fi

echo "🌐 Starting FastAPI server on http://localhost:5001..."

# Start FastAPI application with uvicorn
python -m uvicorn fastapi_web_flashcards:app --host 0.0.0.0 --port 5001 --reload
