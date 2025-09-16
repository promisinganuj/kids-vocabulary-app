#!/bin/bash

# Start the Vocabulary Flashcard Multi-User Web Application
echo "🚀 Starting Vocabulary Flashcard Multi-User Web Application..."
echo "ℹ️  Available versions:"
echo "   - FastAPI (default): ./fastapi_start_app.sh"
echo "   - Flask (legacy): ./flask_start_app.sh"
echo ""
echo "🔧 Starting FastAPI version by default..."

# Execute the FastAPI start script
exec ./fastapi_start_app.sh
