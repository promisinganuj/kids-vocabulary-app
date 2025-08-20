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
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import shutil
from database_manager import DatabaseManager, initialize_from_text_file
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

def search_word_with_openai(word: str) -> dict:
    """
    Search for word definition using Azure OpenAI LLM via HTTP requests.
    
    Args:
        word: The word to search for
        
    Returns:
        dict: Response in the format {word, type, definition, example, error}
    """
    try:
        # Get Azure OpenAI configuration and validate
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        if not api_key:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI API key not configured. Please set AZURE_OPENAI_API_KEY environment variable."
            }
        
        if not endpoint:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI endpoint not configured. Please set AZURE_OPENAI_ENDPOINT environment variable."
            }
            
        if not deployment:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI deployment not configured. Please set AZURE_OPENAI_DEPLOYMENT environment variable."
            }
        
        # Create the prompt for word definition
        prompt = f"""Please provide information about the word "{word}" in the following JSON format:

{{
    "word": "The word in Camel case",
    "type": "Part of speech (Noun, Verb, Adjective, Adverb, etc.)",
    "definition": "Clear and concise definition",
    "example": "A sentence example using the word",
    "error": null
}}

If the word is not a valid English word or you cannot provide information about it, respond with:
{{
    "word": null,
    "type": null,
    "definition": null,
    "example": null,
    "error": "not a valid word" or appropriate error message
}}

If the word can be of many types, please return one one which is the most common.

Only respond with valid JSON, no additional text."""

        # Ensure endpoint ends with a slash
        if not endpoint.endswith('/'):
            endpoint += '/'
        
        # Prepare Azure OpenAI HTTP request
        url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful dictionary assistant. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        # Make the HTTP request
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].strip()
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                
                # Validate the response format
                required_keys = ["word", "type", "definition", "example", "error"]
                if not all(key in result for key in required_keys):
                    return {
                        "word": None,
                        "type": None,
                        "definition": None,
                        "example": None,
                        "error": "Invalid response format from AI"
                    }
                
                return result
                
            except json.JSONDecodeError:
                return {
                    "word": None,
                    "type": None,
                    "definition": None,
                    "example": None,
                    "error": "Failed to parse AI response"
                }
        else:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": f"Azure OpenAI API error: {response.status_code} - {response.text[:100]}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": "Azure OpenAI request timed out. Please try again."
        }
    except requests.exceptions.ConnectionError:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": "Unable to connect to Azure OpenAI service. Please check your internet connection and endpoint."
        }
    except requests.exceptions.RequestException as e:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": f"Azure OpenAI service error: {str(e)}"
        }

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


@app.route('/api/search/word/<word>')
def search_word_definition(word):
    """API endpoint to search for word definition using OpenAI LLM."""
    try:
        # Use OpenAI to search for word definition
        result = search_word_with_openai(word)
        
        # Check if there was an error
        if result.get("error"):
            return jsonify({
                'success': False, 
                'error': result["error"]
            }), 400
        
        # If successful, return the word data
        if result.get("word"):
            word_data = {
                'word': result["word"],
                'type': result["type"] or 'unknown',
                'definition': result["definition"] or 'No definition available',
                'example': result["example"] or f"The word '{word}' can be used in a sentence."
            }
            
            return jsonify({
                'success': True, 
                'data': word_data
            })
        else:
            return jsonify({
                'success': False, 
                'error': 'Word not found or invalid'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': 'An unexpected error occurred while searching'
        }), 500


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


@app.route('/api/study/preferences', methods=['GET', 'POST'])
def study_preferences():
    """API endpoint to manage user study preferences."""
    if request.method == 'POST':
        data = request.get_json()
        # Store preferences in session/database (simplified for now)
        # In a full implementation, this would be stored per user
        preferences = {
            'daily_goal': data.get('daily_goal', 20),
            'session_goal': data.get('session_goal', 10),
            'time_limit': data.get('time_limit', 0),  # 0 = no limit
            'preferred_mode': data.get('preferred_mode', 'mixed'),
            'difficulty_preference': data.get('difficulty_preference', 'medium')
        }
        return jsonify({'success': True, 'preferences': preferences})
    else:
        # Return default preferences
        default_prefs = {
            'daily_goal': 20,
            'session_goal': 10,
            'time_limit': 0,
            'preferred_mode': 'mixed',
            'difficulty_preference': 'medium'
        }
        return jsonify(default_prefs)


@app.route('/api/study/session/custom', methods=['POST'])
def start_custom_study_session():
    """API endpoint to start a customized study session."""
    data = request.get_json() or {}
    
    # Extract session configuration
    session_config = {
        'type': data.get('session_type', 'mixed'),  # new, review, mixed, difficult
        'word_goal': data.get('word_goal', 10),
        'time_limit': data.get('time_limit', 0),  # 0 = no limit
        'difficulty': data.get('difficulty', 'all')  # easy, medium, hard, all
    }
    
    # Get words based on session type
    if session_config['type'] == 'new':
        words = db_manager.get_new_words(limit=session_config['word_goal'] * 2)  # Get extra for selection
    elif session_config['type'] == 'review':
        words = db_manager.get_review_words(limit=session_config['word_goal'] * 2)
    elif session_config['type'] == 'difficult':
        words = db_manager.get_difficult_words(limit=session_config['word_goal'] * 2)
    else:  # mixed
        words = db_manager.get_mixed_words(limit=session_config['word_goal'] * 2)
    
    # Filter by difficulty if specified
    if session_config['difficulty'] != 'all':
        words = [w for w in words if w.get('difficulty', 'medium') == session_config['difficulty']]
    
    # Start the session
    session_id = db_manager.start_study_session(session_config['type'])
    
    if session_id:
        return jsonify({
            'success': True, 
            'session_id': session_id,
            'config': session_config,
            'word_count': len(words),
            'words': words[:session_config['word_goal']]  # Return exact number requested
        })
    else:
        return jsonify({'success': False, 'error': 'Failed to start session'}), 500


@app.route('/api/study/session/<int:session_id>/progress', methods=['POST'])
def update_session_progress(session_id):
    """API endpoint to update session progress."""
    data = request.get_json()
    
    # Update session progress in real-time
    progress = {
        'words_reviewed': data.get('words_reviewed', 0),
        'words_correct': data.get('words_correct', 0),
        'current_accuracy': data.get('accuracy', 0),
        'time_elapsed': data.get('time_elapsed', 0)
    }
    
    # Here you could store intermediate progress to database
    # For now, just return success
    return jsonify({'success': True, 'progress': progress})


@app.route('/api/study/session/<int:session_id>/reset', methods=['POST'])
def reset_study_session(session_id):
    """API endpoint to reset a study session."""
    # Reset session progress
    success = db_manager.reset_study_session(session_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Session reset successfully'})
    else:
        return jsonify({'success': False, 'error': 'Failed to reset session'}), 500


@app.route('/api/study/achievements')
def get_achievements():
    """API endpoint to get user achievements."""
    achievements = db_manager.get_user_achievements()
    return jsonify({'achievements': achievements})


@app.route('/api/study/analytics')
def get_study_analytics():
    """API endpoint to get study analytics and progress data."""
    analytics = {
        'daily_stats': db_manager.get_daily_study_stats(),
        'weekly_progress': db_manager.get_weekly_progress(),
        'mastery_breakdown': db_manager.get_mastery_breakdown(),
        'streak_info': db_manager.get_study_streak(),
        'recent_sessions': db_manager.get_recent_sessions(limit=10)
    }
    return jsonify(analytics)


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
