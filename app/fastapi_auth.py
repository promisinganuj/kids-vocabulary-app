#!/usr/bin/env python3
"""
FastAPI Authentication Module for VCE Vocabulary Flashcard Application

This module handles user authentication, session management, and authorization for FastAPI.
It provides dependencies and utilities for protecting routes and managing user sessions.

Author: Authentication Module
Date: September 2025
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Cookie, Header, Query, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
                SELECT u.id, u.email, u.username, u.first_name, u.last_name, u.profile_type, u.year_of_birth, 
                       u.class_year, u.created_at, u.last_login, u.is_active, s.expires_at
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.expires_at > ?
            ''', (session_token, datetime.now()))
            
            row = cursor.fetchone()
            if row:
                return User(
                    user_id=row['id'],
                    email=row['email'],
                    username=row['username'],
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    profile_type=row['profile_type'],
                    year_of_birth=row['year_of_birth'],
                    class_year=row['class_year'],
                    created_at=row['created_at'],
                    last_login=row['last_login'],
                    is_active=row['is_active']
                )
        return None
    
    def delete_session(self, session_token: str) -> bool:
        """Delete a session."""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
            conn.commit()
            return cursor.rowcount > 0


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


# Global authentication manager and preferences
auth_manager: Optional[AuthenticationManager] = None
user_preferences: Optional[UserPreferences] = None

def init_authentication(db_manager: DatabaseManager):
    """Initialize authentication for FastAPI app."""
    global auth_manager, user_preferences
    auth_manager = AuthenticationManager(db_manager)
    user_preferences = UserPreferences(db_manager)

# FastAPI Dependencies
security = HTTPBearer(auto_error=False)

async def get_session_token(
    request: Request,
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(None)
) -> Optional[str]:
    """Extract session token from various sources."""
    # Priority: Cookie > Authorization header > Query parameter
    if session_token:
        return session_token
    if authorization:
        return authorization.credentials
    if token:
        return token
    
    # Check for custom session handling in cookies
    if hasattr(request, 'cookies'):
        return request.cookies.get('session_token')
    
    return None

async def get_current_user(
    token: Optional[str] = Depends(get_session_token)
) -> Optional[User]:
    """Get current user from session token."""
    if not token or not auth_manager:
        return None
    return auth_manager.validate_session(token)

async def require_authentication(
    current_user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require user to be authenticated."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def require_admin(
    current_user: User = Depends(require_authentication)
) -> User:
    """Require user to be admin."""
    if not auth_manager or not auth_manager.db_manager.is_user_admin(current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Utility functions for backward compatibility
def get_current_user_sync() -> Optional[User]:
    """Synchronous version for backward compatibility."""
    # This will be used in template context or other sync contexts
    # We'll need to store the current user in request state
    return None

def require_user_id_sync() -> int:
    """Get current user ID or raise error (sync version)."""
    user = get_current_user_sync()
    if not user:
        raise ValueError("User not authenticated")
    return user.user_id

def get_user_preference_sync(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get preference for current user (sync version)."""
    user = get_current_user_sync()
    if not user or not user_preferences:
        return default
    return user_preferences.get_preference(user.user_id, key, default)

# Request state management for storing current user
class RequestState:
    def __init__(self):
        self.current_user: Optional[User] = None
        self.session_token: Optional[str] = None

# This will be set by middleware
request_state: Optional[RequestState] = None