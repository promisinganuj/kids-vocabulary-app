#!/usr/bin/env python3
"""
Authentication Module for VCE Vocabulary Flashcard Application

This module handles user authentication, session management, and authorization.
It provides decorators and utilities for protecting routes and managing user sessions.

Author: Authentication Module
Date: August 2025
"""

import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any, Tuple
from flask import session, request, jsonify, redirect, url_for, g
from database_manager import DatabaseManager, User


class AuthenticationManager:
    """Manages user authentication and sessions."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session_timeout_hours = 24  # Sessions expire after 24 hours
    
    def create_session(self, user: User, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> str:
        """Create a new session for the user."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=self.session_timeout_hours)
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (user.user_id, session_token, expires_at, ip_address, user_agent))
            conn.commit()
        
        return session_token
    
    def validate_session(self, session_token: str) -> Optional[User]:
        """Validate session token and return user if valid."""
        if not session_token:
            return None
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.user_id, s.expires_at, u.email, u.username, u.created_at, u.last_login, u.is_active
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP AND u.is_active = 1
            ''', (session_token,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Update last accessed time
            cursor.execute('''
                UPDATE user_sessions 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE session_token = ?
            ''', (session_token,))
            conn.commit()
            
            # Return user object
            return User(
                user_id=row['user_id'],
                email=row['email'],
                username=row['username'],
                created_at=row['created_at'],
                last_login=row['last_login'],
                is_active=bool(row['is_active'])
            )
    
    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session token."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
            conn.commit()
            return cursor.rowcount > 0
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from database."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_sessions WHERE expires_at <= CURRENT_TIMESTAMP')
            conn.commit()
            return cursor.rowcount


class AuthDecorator:
    """Authentication decorator for Flask routes."""
    
    def __init__(self, auth_manager: AuthenticationManager):
        self.auth_manager = auth_manager
    
    def login_required(self, f):
        """Decorator that requires user to be logged in."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for session token in various places
            token = None
            
            # 1. Check Flask session
            if 'session_token' in session:
                token = session['session_token']
            
            # 2. Check Authorization header
            elif request.headers.get('Authorization'):
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # 3. Check query parameter (for API calls)
            elif request.args.get('token'):
                token = request.args.get('token')
            
            if not token:
                return self._handle_unauthorized()
            
            # Validate session
            user = self.auth_manager.validate_session(token)
            if not user:
                # Invalid session, clear it
                session.pop('session_token', None)
                session.pop('user_id', None)
                return self._handle_unauthorized()
            
            # Store user in Flask g for easy access in route
            g.current_user = user
            g.session_token = token
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def admin_required(self, f):
        """Decorator that requires user to be admin."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check if user is logged in
            if not hasattr(g, 'current_user') or not g.current_user:
                return self._handle_unauthorized()
            
            # Check if user is admin (for now, we'll add admin flag later)
            # For simplicity, treat user_id = 1 as admin
            if g.current_user.user_id != 1:
                return jsonify({'error': 'Admin access required'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def api_key_required(self, f):
        """Decorator for API endpoints that require API key."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({'error': 'API key required'}), 401
            
            # For now, we'll implement a simple API key check
            # In production, you'd want to store API keys in database
            valid_api_key = os.environ.get('VOCABULARY_API_KEY', 'dev-api-key-123')
            
            if api_key != valid_api_key:
                return jsonify({'error': 'Invalid API key'}), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def _handle_unauthorized(self):
        """Handle unauthorized access based on request type."""
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        else:
            return redirect(url_for('login_page'))


class UserPreferences:
    """Manages user preferences."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_preference(self, user_id: int, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a user preference value."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT preference_value FROM user_preferences 
                WHERE user_id = ? AND preference_key = ?
            ''', (user_id, key))
            
            row = cursor.fetchone()
            return row['preference_value'] if row else default
    
    def set_preference(self, user_id: int, key: str, value: str) -> bool:
        """Set a user preference value."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_preferences (user_id, preference_key, preference_value)
                    VALUES (?, ?, ?)
                ''', (user_id, key, value))
                conn.commit()
                return True
        except Exception:
            return False
    
    def get_all_preferences(self, user_id: int) -> Dict[str, str]:
        """Get all preferences for a user."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT preference_key, preference_value FROM user_preferences 
                WHERE user_id = ?
            ''', (user_id,))
            
            return {row['preference_key']: row['preference_value'] for row in cursor.fetchall()}
    
    def set_multiple_preferences(self, user_id: int, preferences: Dict[str, str]) -> bool:
        """Set multiple preferences at once."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                for key, value in preferences.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_preferences (user_id, preference_key, preference_value)
                        VALUES (?, ?, ?)
                    ''', (user_id, key, str(value)))
                conn.commit()
                return True
        except Exception:
            return False


def init_authentication(app, db_manager: DatabaseManager):
    """Initialize authentication for Flask app."""
    app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Create authentication manager
    auth_manager = AuthenticationManager(db_manager)
    
    # Create auth decorator
    auth = AuthDecorator(auth_manager)
    
    # Create preferences manager
    preferences = UserPreferences(db_manager)
    
    # Store in app context for easy access
    app.auth_manager = auth_manager
    app.auth = auth
    app.user_preferences = preferences
    
    # Add cleanup task for expired sessions
    @app.before_request
    def cleanup_sessions():
        """Clean up expired sessions periodically."""
        import random
        # Run cleanup 1% of the time to avoid overhead
        if random.random() < 0.01:
            auth_manager.cleanup_expired_sessions()
    
    # Helper function to get current user in templates
    @app.context_processor
    def inject_user():
        return dict(current_user=getattr(g, 'current_user', None))
    
    return auth_manager, auth, preferences


# Utility functions
def get_current_user() -> Optional[User]:
    """Get current user from Flask g."""
    return getattr(g, 'current_user', None)


def is_authenticated() -> bool:
    """Check if current user is authenticated."""
    return get_current_user() is not None


def require_user_id() -> int:
    """Get current user ID or raise error."""
    user = get_current_user()
    if not user:
        raise ValueError("User not authenticated")
    return user.user_id


def get_user_preference(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get preference for current user."""
    from flask import current_app
    user = get_current_user()
    if not user:
        return default
    
    if hasattr(current_app, 'user_preferences'):
        return getattr(current_app, 'user_preferences').get_preference(user.user_id, key, default)
    return default


if __name__ == '__main__':
    # Test authentication
    from app.database_manager import DatabaseManager
    
    db_manager = DatabaseManager('data/vocabulary.db')
    auth_manager = AuthenticationManager(db_manager)
    
    # Test authentication
    success, message, user = db_manager.authenticate_user("admin@vocabulary.local", "admin123")
    if success and user:
        print(f"✅ Authentication successful: {user.email}")
        
        # Create session
        token = auth_manager.create_session(user, "127.0.0.1", "Test Agent")
        print(f"✅ Session created: {token[:20]}...")
        
        # Validate session
        validated_user = auth_manager.validate_session(token)
        if validated_user:
            print(f"✅ Session validation successful: {validated_user.email}")
        else:
            print("❌ Session validation failed")
        
        # Test preferences
        prefs = UserPreferences(db_manager)
        prefs.set_preference(user.user_id, "test_pref", "test_value")
        value = prefs.get_preference(user.user_id, "test_pref")
        print(f"✅ Preferences test: {value}")
    else:
        print(f"❌ Authentication failed: {message}")
