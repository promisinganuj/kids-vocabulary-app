#!/usr/bin/env python3
"""
Multi-User VCE Vocabulary Flashcard Web Application

A Flask-based web application for managing vocabulary flashcards with multi-user support.
Features:
- User authentication and registration
- User-specific vocabulary libraries
- View flashcards with flip functionality
- Add new vocabulary words
- Remove learned words
- Study session tracking
- Progress analytics
- Search and filter functionality

Author: Multi-User Flashcard Web App
Date: August 2025
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, g
import re
import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import shutil
from multi_user_database_manager import MultiUserDatabaseManager, initialize_multiuser_from_text_file
from auth import init_authentication, get_current_user, require_user_id, is_authenticated

# Admin helper functions
def require_admin():
    """Ensure current user is an admin. Returns user_id if admin, raises exception otherwise."""
    user_id = require_user_id()
    if not db_manager.is_user_admin(user_id):
        from flask import abort
        abort(403)  # Forbidden
    return user_id

def is_admin():
    """Check if current user is an admin."""
    try:
        user = get_current_user()
        if user:
            return db_manager.is_user_admin(user.user_id)
        return False
    except:
        return False
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

# Initialize database manager and authentication
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
text_file = os.path.join(parent_dir, 'seed-data', 'words-list.txt')

# Initialize multi-user database
db_manager = MultiUserDatabaseManager(os.path.join(script_dir, 'data', 'vocabulary_multiuser.db'))

# Initialize authentication
auth_manager, auth, user_preferences = init_authentication(app, db_manager)

# Favicon route to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    """Return empty response for favicon to prevent 404 errors."""
    return '', 204

# Authentication Routes
@app.route('/login')
def login_page():
    """Login page."""
    if is_authenticated():
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Registration page."""
    if is_authenticated():
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    """API endpoint to register a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    
    email = data.get('email', '').strip().lower()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')
    
    # Validation
    if not email or not username or not password:
        return jsonify({'success': False, 'error': 'Email, username, and password are required'}), 400
    
    if password != confirm_password:
        return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters long'}), 400
    
    # Email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({'success': False, 'error': 'Invalid email format'}), 400
    
    # Create user
    success, message, user_id = db_manager.create_user(email, username, password)
    
    if success and user_id:
        # Automatically load base vocabulary for new user
        try:
            copied_count = db_manager.copy_base_vocabulary_to_user(user_id)
            print(f"✅ Copied {copied_count} base words to new user {username} (ID: {user_id})")
            
            return jsonify({
                'success': True, 
                'message': f'Account created successfully! {copied_count} vocabulary words have been added to your library. Please log in.'
            })
        except Exception as e:
            print(f"⚠️ Error copying base vocabulary to new user {username}: {str(e)}")
            # User was created successfully, but vocabulary copy failed
            return jsonify({
                'success': True, 
                'message': 'Account created successfully! Please log in.',
                'warning': 'Some vocabulary words may not have been loaded. You can add them manually later.'
            })
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """API endpoint to log in a user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    
    email_or_username = data.get('email_or_username', '').strip()
    password = data.get('password', '')
    
    if not email_or_username or not password:
        return jsonify({'success': False, 'error': 'Email/username and password are required'}), 400
    
    # Authenticate user
    success, message, user = db_manager.authenticate_user(email_or_username, password)
    
    if success and user:
        # Create session
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        session_token = auth_manager.create_session(user, ip_address, user_agent)
        
        # Store session in Flask session
        session['session_token'] = session_token
        session['user_id'] = user.user_id
        session.permanent = True
        
        return jsonify({
            'success': True, 
            'message': 'Login successful',
            'user': user.to_dict()
        })
    else:
        return jsonify({'success': False, 'error': message}), 401

@app.route('/api/auth/logout', methods=['POST'])
@auth.login_required
def logout():
    """API endpoint to log out a user."""
    session_token = session.get('session_token')
    
    if session_token:
        auth_manager.invalidate_session(session_token)
    
    session.clear()
    
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/logout')
def logout_page():
    """Logout page redirect."""
    session_token = session.get('session_token')
    
    if session_token:
        auth_manager.invalidate_session(session_token)
    
    session.clear()
    flash('You have been logged out successfully.')
    return redirect(url_for('login_page'))

# Main Application Routes
@app.route('/')
@auth.login_required
def index():
    """Main flashcards page."""
    user_id = require_user_id()
    words = db_manager.get_user_words(user_id)
    is_user_admin = is_admin()
    return render_template('flashcards.html', words=words, total_words=len(words), is_admin=is_user_admin)

@app.route('/api/words')
@auth.login_required
def get_words():
    """API endpoint to get all words for current user."""
    user_id = require_user_id()
    search_query = request.args.get('search', '')
    include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
    
    if search_query:
        words = db_manager.search_user_words(user_id, search_query)
    else:
        words = db_manager.get_user_words(user_id)

    # Exclude hidden words from the default list unless explicitly requested
    if not include_hidden:
        # Support either 'hidden' or 'is_hidden' flags depending on DB implementation
        def is_hidden_word(w):
            try:
                return bool(w.get('hidden') or w.get('is_hidden'))
            except Exception:
                return False
        words = [w for w in words if not is_hidden_word(w)]

    return jsonify({'words': words, 'total': len(words)})

@app.route('/api/words', methods=['POST'])
@auth.login_required
def add_word():
    """API endpoint to add a new word for current user."""
    user_id = require_user_id()
    data = request.get_json()
    
    if not all(key in data for key in ['word', 'word_type', 'definition', 'example']):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    success, message = db_manager.add_user_word(
        user_id,
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
@auth.login_required
def remove_word(word_id):
    """API endpoint to remove a word for current user."""
    user_id = require_user_id()
    success, message = db_manager.remove_user_word(user_id, word_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 500

@app.route('/api/search/word/<word>')
@auth.login_required
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
@auth.login_required
def manage():
    """Word management page."""
    user_id = require_user_id()
    words = db_manager.get_user_words(user_id)
    is_user_admin = is_admin()
    return render_template('manage.html', words=words, total_words=len(words), is_admin=is_user_admin)

@app.route('/profile')
@auth.login_required
def profile():
    """User profile page."""
    user = get_current_user()
    if not user:
        return redirect(url_for('login_page'))
    
    preferences = user_preferences.get_all_preferences(user.user_id)
    return render_template('profile.html', user=user, preferences=preferences)

@app.route('/api/user/preferences', methods=['GET', 'POST'])
@auth.login_required
def user_preferences_api():
    """API endpoint to manage user preferences."""
    user_id = require_user_id()
    
    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        
        success = user_preferences.set_multiple_preferences(user_id, data)
        if success:
            return jsonify({'success': True, 'message': 'Preferences updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update preferences'}), 500
    else:
        preferences = user_preferences.get_all_preferences(user_id)
        return jsonify(preferences)

@app.route('/api/user/profile', methods=['GET'])
@auth.login_required
def get_user_profile():
    """API endpoint to get current user profile."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict())

# Health check and info routes
@app.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        total_users = len(db_manager.get_connection().execute('SELECT id FROM users').fetchall())
        return {
            'status': 'healthy',
            'database': 'connected',
            'total_users': total_users,
            'version': '2.0.0-multiuser'
        }, 200
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'version': '2.0.0-multiuser'
        }, 500

@app.route('/api/info')
def app_info():
    """Application information endpoint."""
    return jsonify({
        'name': 'VCE Vocabulary Flashcards',
        'version': '2.0.0-multiuser',
        'description': 'Multi-user vocabulary learning application',
        'features': [
            'User authentication',
            'Personal vocabulary libraries',
            'Study session tracking',
            'AI-powered word definitions',
            'Progress analytics'
        ]
    })

# Word Management Routes
@app.route('/api/words/<int:word_id>/like', methods=['POST'])
@auth.login_required
def like_word(word_id):
    """Like a word."""
    user_id = require_user_id()
    
    success, message = db_manager.like_word(user_id, word_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/words/<int:word_id>/unlike', methods=['POST'])
@auth.login_required
def unlike_word(word_id):
    """Unlike a word."""
    user_id = require_user_id()
    
    success, message = db_manager.unlike_word(user_id, word_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/words/<int:word_id>/hide', methods=['POST'])
@auth.login_required
def hide_word(word_id):
    """Hide a word from user's vocabulary."""
    user_id = require_user_id()
    
    success, message = db_manager.hide_word_for_user(user_id, word_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/words/<int:word_id>/unhide', methods=['POST'])
@auth.login_required
def unhide_word(word_id):
    """Unhide a word in user's vocabulary."""
    user_id = require_user_id()
    
    success, message = db_manager.unhide_word_for_user(user_id, word_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/words/<int:word_id>/review', methods=['POST'])
@auth.login_required
def review_word(word_id):
    """Record a word review (correct/incorrect) for the user."""
    user_id = require_user_id()
    
    data = request.get_json()
    if not data or 'correct' not in data:
        return jsonify({'success': False, 'error': 'Missing "correct" parameter'}), 400
    
    correct = bool(data['correct'])
    auto = bool(data.get('auto', True))

    success, message = db_manager.record_word_review(user_id, word_id, correct)

    actions = []
    if success and auto:
        try:
            if correct:
                # Correct answer: ease the difficulty and hide from active queue
                db_manager.update_word_difficulty(user_id, word_id, 'easy')
                db_manager.hide_word_for_user(user_id, word_id)
                actions.extend(['set_easy', 'hidden'])
            else:
                # Incorrect answer: raise difficulty and keep visible
                db_manager.update_word_difficulty(user_id, word_id, 'hard')
                db_manager.unhide_word_for_user(user_id, word_id)
                actions.extend(['set_hard', 'unhidden'])
        except Exception:
            # Don't fail the review if adjustments encounter issues
            pass
    
    if success:
        return jsonify({'success': True, 'message': message, 'actions': actions, 'correct': correct})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/words/<int:word_id>/know', methods=['POST'])
@auth.login_required
def mark_word_known(word_id):
    """Mark a word as known: set difficulty to easy and hide it."""
    user_id = require_user_id()

    ok_diff, msg_diff = db_manager.update_word_difficulty(user_id, word_id, 'easy')
    ok_hide, msg_hide = db_manager.hide_word_for_user(user_id, word_id)

    if ok_diff and ok_hide:
        return jsonify({'success': True, 'message': 'Marked as known (easy) and hidden'})

    errors = []
    if not ok_diff and msg_diff:
        errors.append(msg_diff)
    if not ok_hide and msg_hide:
        errors.append(msg_hide)
    return jsonify({'success': False, 'error': '; '.join(errors) or 'Failed to mark as known'}), 400

@app.route('/api/words/<int:word_id>/difficulty', methods=['PUT'])
@auth.login_required
def update_word_difficulty(word_id):
    """Update the difficulty level of a word for the user."""
    user_id = require_user_id()
    
    data = request.get_json()
    if not data or 'difficulty' not in data:
        return jsonify({'success': False, 'error': 'Missing "difficulty" parameter'}), 400
    
    difficulty = data['difficulty']
    if difficulty not in ['easy', 'medium', 'hard']:
        return jsonify({'success': False, 'error': 'Invalid difficulty level'}), 400
    
    success, message = db_manager.update_word_difficulty(user_id, word_id, difficulty)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

# Study Session Management Routes
@app.route('/api/study/session/custom', methods=['POST'])
@auth.login_required
def create_custom_study_session():
    """Create a custom study session for the user."""
    user_id = require_user_id()
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Missing session configuration'}), 400
    
    session_type = data.get('session_type', 'review')
    word_goal = data.get('word_goal', 10)
    time_limit = data.get('time_limit', 0)  # 0 means no time limit
    difficulty = data.get('difficulty', 'all')
    
    success, message, session_id = db_manager.create_study_session(
        user_id, session_type, word_goal, time_limit, difficulty
    )
    
    if success:
        return jsonify({
            'success': True, 
            'message': message,
            'session_id': session_id
        })
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/study/session/<session_id>', methods=['PUT'])
@auth.login_required
def update_study_session(session_id):
    """Update a study session (typically to end it)."""
    user_id = require_user_id()
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Missing session data'}), 400
    
    success, message = db_manager.update_study_session(
        user_id, session_id, data
    )
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/study/session/<session_id>/progress', methods=['POST'])
@auth.login_required
def update_session_progress(session_id):
    """Update study session progress."""
    user_id = require_user_id()
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Missing progress data'}), 400
    
    success, message = db_manager.update_session_progress(
        user_id, session_id, data
    )
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/study/session/<session_id>/reset', methods=['POST'])
@auth.login_required
def reset_study_session(session_id):
    """Reset a study session."""
    user_id = require_user_id()
    
    success, message = db_manager.reset_study_session(user_id, session_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/user/liked-words')
@auth.login_required
def get_user_liked_words():
    """Get list of word IDs that the user has liked."""
    user_id = require_user_id()
    
    liked_word_ids = db_manager.get_user_word_likes(user_id)
    return jsonify({'liked_words': liked_word_ids})

@app.route('/api/most-liked-words')
@auth.login_required
def get_most_liked_words():
    """Get the most liked words across all users."""
    limit = request.args.get('limit', 50, type=int)
    
    words = db_manager.get_most_liked_words(limit)
    return jsonify({'words': words})

# Password Reset Routes
@app.route('/forgot-password')
def forgot_password_page():
    """Render forgot password page."""
    return render_template('forgot_password.html')

@app.route('/reset-password')
def reset_password_page():
    """Render reset password page."""
    token = request.args.get('token')
    if not token:
        flash('Invalid reset link', 'error')
        return redirect(url_for('login_page'))
    
    # Validate token
    valid, message, user_id = db_manager.validate_reset_token(token)
    if not valid:
        flash(message, 'error')
        return redirect(url_for('login_page'))
    
    return render_template('reset_password.html', token=token)

@app.route('/api/auth/forgot-password', methods=['POST'])
def request_password_reset():
    """Request a password reset token."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'}), 400
    
    success, message, token = db_manager.create_password_reset_token(email)
    
    if success and token:
        # In a real app, you would send this via email
        # For demo purposes, we'll log it
        print(f"Password reset token for {email}: {token}")
        print(f"Reset link: http://localhost:5001/reset-password?token={token}")
        
        return jsonify({
            'success': True, 
            'message': message,
            'dev_token': token,  # Remove this in production!
            'dev_link': f"http://localhost:5001/reset-password?token={token}"  # Remove this in production!
        })
    else:
        return jsonify({'success': True, 'message': message})  # Always return success for security

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password using a token."""
    data = request.get_json()
    token = data.get('token', '').strip()
    new_password = data.get('password', '')
    
    if not token or not new_password:
        return jsonify({'success': False, 'error': 'Token and new password are required'}), 400
    
    success, message = db_manager.reset_password_with_token(token, new_password)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

# Error handlers
@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized access."""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
    else:
        return redirect(url_for('login_page'))

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found'}), 404
    else:
        return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    else:
        return render_template('500.html'), 500

# Admin Routes
@app.route('/admin')
@auth.login_required
def admin_dashboard():
    """Admin dashboard page."""
    require_admin()  # Ensure user is admin
    
    # Get system statistics
    stats = db_manager.get_system_stats()
    users = db_manager.get_all_users()
    
    return render_template('admin.html', stats=stats, users=users)

@app.route('/api/admin/users')
@auth.login_required
def admin_get_users():
    """API endpoint to get all users (admin only)."""
    require_admin()
    
    users = db_manager.get_all_users()
    return jsonify({'success': True, 'users': users})

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@auth.login_required
def admin_update_user(user_id):
    """API endpoint to update a user (admin only)."""
    require_admin()
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400
    
    success, message = db_manager.update_user(
        user_id=user_id,
        email=data.get('email'),
        username=data.get('username'),
        is_admin=data.get('is_admin')
    )
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@auth.login_required
def admin_delete_user(user_id):
    """API endpoint to delete a user (admin only)."""
    require_admin()
    
    success, message = db_manager.delete_user(user_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/admin/users/<int:user_id>/reload-vocabulary', methods=['POST'])
@auth.login_required
def admin_reload_user_vocabulary(user_id):
    """API endpoint to reload base vocabulary for a user (admin only)."""
    require_admin()
    
    success, message, count = db_manager.reload_base_vocabulary_for_user(user_id)
    
    if success:
        return jsonify({'success': True, 'message': message, 'words_reloaded': count})
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/api/admin/stats')
@auth.login_required
def admin_get_stats():
    """API endpoint to get system statistics (admin only)."""
    require_admin()
    
    stats = db_manager.get_system_stats()
    return jsonify({'success': True, 'stats': stats})

if __name__ == '__main__':
    # Load initial data if database is empty
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM vocabulary')
        word_count = cursor.fetchone()['count']
    
    if word_count == 0:
        print("Database is empty. Checking for seed data...")
        if os.path.exists(text_file):
            # For demo purposes, load data for the first user (admin)
            print(f"Loading seed data for admin user from: {text_file}")
            # Get admin user ID
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM users WHERE email = ?', ('admin@vocabulary.local',))
                admin_row = cursor.fetchone()
                if admin_row:
                    admin_user_id = admin_row['id']
                    loaded_count = db_manager.load_vocabulary_from_text_file(text_file, admin_user_id)
                    if loaded_count > 0:
                        print(f"Successfully loaded {loaded_count} words for admin user")
                else:
                    print("No admin user found. Please register an admin user first.")
        else:
            print(f"No seed data found at: {text_file}")
    else:
        print(f"📊 Database contains {word_count} words")
    
    print("🚀 Starting Multi-User Vocabulary Flashcard Web Application...")
    print("🌐 Access the application at: http://localhost:5001")
    print("🔐 Login required - register a new account or use admin credentials")
    print("🔧 Management interface at: http://localhost:5001/manage")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
