#!/usr/bin/env python3
"""
VCE Vocabulary Flashcard Web Application

A Flask-based web application for managing vocabulary flashcards.
Features:
- View flashcards with flip functionality
- Add new vocabulary words
- Remove learned words
- Persist changes to the vocabulary file
- Search and filter functionality

Author: Flashcard Web App
Date: 2025
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import re
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import shutil
from database_manager import DatabaseManager, initialize_from_text_file

app = Flask(__name__)

# Initialize database manager
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
text_file = os.path.join(parent_dir, 'seed-data', 'words-list.txt')

# Initialize database from text file if it exists
db_manager = initialize_from_text_file(text_file)


@app.route('/')
def index():
    """Main flashcards page."""
    words = db_manager.get_all_words()
    return render_template('flashcards.html', words=words, total_words=len(words))


@app.route('/api/words')
def get_words():
    """API endpoint to get all words."""
    search_query = request.args.get('search', '')
    words = db_manager.search_words(search_query)
    return jsonify({'words': words, 'total': len(words)})


@app.route('/api/words', methods=['POST'])
def add_word():
    """API endpoint to add a new word."""
    data = request.get_json()
    
    if not all(key in data for key in ['word', 'word_type', 'definition', 'example']):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    success, message = db_manager.add_word(
        data['word'], 
        data['word_type'], 
        data['definition'], 
        data['example']
    )
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/api/words/<int:word_id>', methods=['DELETE'])
def remove_word(word_id):
    """API endpoint to remove a word."""
    success, message = db_manager.remove_word(word_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 500


@app.route('/manage')
def manage():
    """Word management page."""
    words = db_manager.get_all_words()
    return render_template('manage.html', words=words, total_words=len(words))


@app.route('/api/words/<int:word_id>/difficulty', methods=['PUT'])
def update_word_difficulty(word_id):
    """API endpoint to update word difficulty."""
    data = request.get_json()
    
    if 'difficulty' not in data:
        return jsonify({'success': False, 'error': 'Difficulty level required'}), 400
    
    success, message = db_manager.update_word_difficulty(word_id, data['difficulty'])
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/api/words/<int:word_id>/review', methods=['POST'])
def record_word_review(word_id):
    """API endpoint to record word review."""
    data = request.get_json()
    
    if 'correct' not in data:
        return jsonify({'success': False, 'error': 'Review result required'}), 400
    
    success, message = db_manager.record_word_review(word_id, data['correct'])
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400


@app.route('/api/study/session', methods=['POST'])
def start_study_session():
    """API endpoint to start a study session."""
    data = request.get_json() or {}
    session_type = data.get('session_type', 'review')
    
    session_id = db_manager.start_study_session(session_type)
    
    if session_id:
        return jsonify({'success': True, 'session_id': session_id})
    else:
        return jsonify({'success': False, 'error': 'Failed to start session'}), 500


@app.route('/api/study/session/<int:session_id>', methods=['PUT'])
def end_study_session(session_id):
    """API endpoint to end a study session."""
    data = request.get_json()
    
    required_fields = ['words_reviewed', 'words_correct', 'duration_seconds']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Missing required session data'}), 400
    
    success = db_manager.end_study_session(
        session_id, 
        data['words_reviewed'], 
        data['words_correct'], 
        data['duration_seconds']
    )
    
    if success:
        return jsonify({'success': True, 'message': 'Session ended successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to end session'}), 500


@app.route('/api/words/difficulty/<difficulty>')
def get_words_by_difficulty(difficulty):
    """API endpoint to get words by difficulty level."""
    words = db_manager.get_words_by_difficulty(difficulty)
    return jsonify({'words': words, 'total': len(words)})


@app.route('/api/stats/study')
def get_study_stats():
    """API endpoint to get study statistics."""
    stats = db_manager.get_study_stats()
    return jsonify(stats)


if __name__ == '__main__':
    # Initialize database manager
    db_manager = DatabaseManager('data/vocabulary.db')
    
    # Load initial data if database is empty
    words = db_manager.get_all_words()
    if not words:
        print("Database is empty. Loading vocabulary from file...")
        loaded_count = db_manager.load_from_text_file('./../seed-data/words-list.txt')
        if loaded_count > 0:
            print(f"Successfully loaded {loaded_count} words from vocabulary file")
            words = db_manager.get_all_words()
        else:
            print("Error loading vocabulary from file")
    
    print("🚀 Starting Vocabulary Flashcard Web Application...")
    print(f"📊 Loaded {len(words)} words from database")
    print("🌐 Access the application at: http://localhost:5001")
    print("🔧 Management interface at: http://localhost:5001/manage")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
