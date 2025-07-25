#!/usr/bin/env python3
"""
Production Web Application Entry Point for Azure App Service
"""

import os
from web_flashcards import app, db_manager

# Set production configurations
app.config['DEBUG'] = False
app.config['TESTING'] = False

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Initialize database if it doesn't exist
if not os.path.exists('data/vocabulary.db'):
    print("🚀 Initializing database for production...")
    
    # Check if vocabulary file exists
    if os.path.exists('data/new-words.txt'):
        loaded_count = db_manager.load_from_text_file('data/new-words.txt')
        print(f"✅ Loaded {loaded_count} words into production database")
    else:
        print("⚠️ No vocabulary file found. Database will be empty.")

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for Azure monitoring."""
    try:
        # Test database connection
        words = db_manager.get_all_words()
        return {
            'status': 'healthy',
            'database': 'connected',
            'word_count': len(words),
            'version': '2.0.0'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'version': '2.0.0'
        }, 500

if __name__ == '__main__':
    # This will be used by Gunicorn
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
else:
    # WSGI application object for Gunicorn
    application = app
