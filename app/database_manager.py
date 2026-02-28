#!/usr/bin/env python3
"""
Database Manager for Vocabulary Flashcard Application

This module handles all database operations using SQLAlchemy (PostgreSQL) with multi-user support.
It manages users, vocabulary words, study sessions, and user preferences.

Author: Vocabulary DB Manager
Date: August 2025
"""

import os
import re
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.exc import IntegrityError

from _db_adapter import ConnectionAdapter
from database import SessionLocal, init_tables
from settings import settings

# Password hashing with bcrypt (cost factor 12)


class User:
    """Class to represent a user."""
    
    def __init__(self, user_id: int, email: str, username: str, created_at: str, 
                 last_login: Optional[str] = None, is_active: bool = True,
                 first_name: Optional[str] = None, last_name: Optional[str] = None,
                 mobile_number: Optional[str] = None, profile_type: str = 'Student',
                 class_year: Optional[int] = None, year_of_birth: Optional[int] = None,
                 school_name: Optional[str] = None, preferred_study_time: Optional[str] = None,
                 learning_goals: Optional[str] = None, avatar_color: Optional[str] = None):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.created_at = created_at
        self.last_login = last_login
        self.is_active = is_active
        self.first_name = first_name
        self.last_name = last_name
        self.mobile_number = mobile_number
        self.profile_type = profile_type
        self.class_year = class_year
        self.year_of_birth = year_of_birth
        self.school_name = school_name
        self.preferred_study_time = preferred_study_time
        self.learning_goals = learning_goals
        self.avatar_color = avatar_color
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'username': self.username,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'mobile_number': self.mobile_number,
            'profile_type': self.profile_type,
            'class_year': self.class_year,
            'year_of_birth': self.year_of_birth,
            'school_name': self.school_name,
            'preferred_study_time': self.preferred_study_time,
            'learning_goals': self.learning_goals,
            'avatar_color': self.avatar_color
        }


class VocabularyWord:
    """Class to represent a vocabulary word with its definition and example."""
    
    def __init__(self, word: str, word_type: str, definition: str, example: str, 
                 word_id: Optional[int] = None, user_id: Optional[int] = None,
                 difficulty: str = 'medium', times_reviewed: int = 0, 
                 times_correct: int = 0, mastery_level: int = 0,
                 created_at: Optional[str] = None, last_reviewed: Optional[str] = None,
                 is_hidden: int = 0):
        self.word = word.strip()
        self.word_type = word_type.strip()
        self.definition = definition.strip()
        self.example = example.strip()
        self.word_id = word_id
        self.user_id = user_id
        self.difficulty = difficulty
        self.times_reviewed = times_reviewed
        self.times_correct = times_correct
        self.mastery_level = mastery_level
        self.created_at = created_at
        self.last_reviewed = last_reviewed
        self.is_hidden = is_hidden
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert word to dictionary for JSON serialization."""
        return {
            'id': self.word_id,
            'word': self.word,
            'word_type': self.word_type,
            'definition': self.definition,
            'example': self.example,
            'user_id': self.user_id,
            'difficulty': self.difficulty,
            'times_reviewed': self.times_reviewed,
            'times_correct': self.times_correct,
            'mastery_level': self.mastery_level,
            'created_at': self.created_at,
            'last_reviewed': self.last_reviewed,
            'is_hidden': self.is_hidden,
            'accuracy': round((self.times_correct / self.times_reviewed * 100) if self.times_reviewed > 0 else 0, 1)
        }


class DatabaseManager:
    """Main database manager for vocabulary operations."""
    
    def __init__(self):
        """Initialize database manager.
        
        Uses DATABASE_URL from settings (PostgreSQL).
        Schema is managed by Alembic migrations.
        """
        # Skip DB init if already done by entrypoint (avoids race
        # when multiple uvicorn workers import this module simultaneously).
        if not os.environ.get("_DB_INITIALIZED"):
            self.init_database()
            os.environ["_DB_INITIALIZED"] = "1"
    
    def get_connection(self) -> ConnectionAdapter:
        """Get a database connection backed by a SQLAlchemy session.
        
        Returns a ConnectionAdapter wrapping a SQLAlchemy session.
        Supports context-manager pattern (auto commit/rollback).
        """
        session = SessionLocal()
        return ConnectionAdapter(session)
    
    def init_database(self) -> None:
        """Initialize the database and create tables.
        
        Uses SQLAlchemy ORM models (models.py) to create all tables.
        Schema changes are managed by Alembic migrations.
        """
        # Create all tables from ORM models
        init_tables()
        

        
        # Log initialization
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) as count FROM base_vocabulary')
                row = cursor.fetchone()
                count = row['count'] if row else 0
            print(f"\u2705 Database initialized (PostgreSQL)")
            print(f"\U0001f4ca Database contains {count} base vocabulary words")
        except Exception:
            print(f"\u2705 Database initialized (PostgreSQL)")

    def update_schema_if_needed(self):
        """Schema is managed by Alembic migrations. No-op."""
        pass

    # ─── Account Lockout Helpers ─────────────────────────────────
    MAX_FAILED_LOGINS = 5
    LOCKOUT_DURATION_MINUTES = 15

    def _record_failed_login(self, user_id: int, conn) -> None:
        """Record a failed login attempt."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET failed_login_count = COALESCE(failed_login_count, 0) + 1,
                last_failed_login = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))
        conn.commit()

    def _reset_failed_logins(self, user_id: int, conn) -> None:
        """Reset failed login counter after successful login."""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET failed_login_count = 0, last_failed_login = NULL WHERE id = ?
        """, (user_id,))
        conn.commit()

    def _check_account_lockout(self, user_id: int, conn) -> Optional[str]:
        """Check if account is locked due to too many failed attempts. Returns message if locked, None if OK."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT failed_login_count, last_failed_login FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        failed_count = row['failed_login_count'] or 0
        last_failed = row['last_failed_login']
        if failed_count >= self.MAX_FAILED_LOGINS and last_failed:
            from datetime import datetime
            try:
                if isinstance(last_failed, str):
                    last_failed_dt = datetime.fromisoformat(last_failed.replace('Z', '+00:00'))
                else:
                    last_failed_dt = last_failed
                lockout_until = last_failed_dt + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                if datetime.now() < lockout_until:
                    remaining = int((lockout_until - datetime.now()).total_seconds() / 60) + 1
                    return f"Account locked due to too many failed attempts. Try again in {remaining} minutes."
                else:
                    # Lockout expired, reset counter
                    self._reset_failed_logins(user_id, conn)
            except Exception:
                pass
        return None

    # ─── Password Policy ────────────────────────────────────────
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """Validate password meets security requirements.
        
        Rules:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter  
        - At least one digit
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one digit"
        return True, "Password meets requirements"

        # User Authentication Methods
    def create_user(self, email: str, username: str, password: str) -> Tuple[bool, str, Optional[int]]:
        """Create a new user account."""
        try:
            # Validate input
            if not email or not username or not password:
                return False, "Email, username, and password are required", None
            
            # Validate password strength
            pw_valid, pw_msg = self.validate_password_strength(password)
            if not pw_valid:
                return False, pw_msg, None
            
            # Hash password with bcrypt (cost factor 12)
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            salt = ''  # salt is embedded in bcrypt hash
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (email, username, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                ''', (email.lower().strip(), username.strip(), password_hash, salt))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                # Create default preferences (only if user was created successfully)
                if user_id:
                    self._create_default_user_preferences(user_id)
                
                return True, "User created successfully", user_id
                
        except IntegrityError as e:
            if 'email' in str(e):
                return False, "Email already exists", None
            elif 'username' in str(e):
                return False, "Username already exists", None
            else:
                return False, "User creation failed", None
        except Exception as e:
            return False, f"Error creating user: {str(e)}", None
    

    def create_or_get_oauth_user(self, email: str, oauth_provider: str, oauth_id: str,
                                  first_name: Optional[str] = None, last_name: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """Find or create a user from an OAuth provider (e.g. Google).

        If a user with this email already exists, link the OAuth provider info
        and return that user.  Otherwise, create a new account (no password).
        Returns (success, message, User | None).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if user already exists by email
                cursor.execute(
                    "SELECT id, email, username, created_at, last_login, is_active, "
                    "first_name, last_name, mobile_number, profile_type, class_year, "
                    "year_of_birth, school_name, preferred_study_time, learning_goals, "
                    "avatar_color, oauth_provider, oauth_id "
                    "FROM users WHERE email = ?",
                    (email.lower().strip(),)
                )
                row = cursor.fetchone()

                if row:
                    user_id = row['id']
                    # Link OAuth info if not already set
                    if not row['oauth_provider']:
                        cursor.execute(
                            "UPDATE users SET oauth_provider = ?, oauth_id = ? WHERE id = ?",
                            (oauth_provider, oauth_id, user_id)
                        )
                    # Update name if currently empty
                    if first_name and not row['first_name']:
                        cursor.execute("UPDATE users SET first_name = ? WHERE id = ?", (first_name, user_id))
                    if last_name and not row['last_name']:
                        cursor.execute("UPDATE users SET last_name = ? WHERE id = ?", (last_name, user_id))
                    # Bump login stats
                    cursor.execute(
                        "UPDATE users SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1 WHERE id = ?",
                        (user_id,)
                    )
                    conn.commit()

                    user = User(
                        user_id=row['id'], email=row['email'], username=row['username'],
                        created_at=row['created_at'], last_login=row['last_login'],
                        is_active=bool(row['is_active']), first_name=first_name or row['first_name'],
                        last_name=last_name or row['last_name'], mobile_number=row['mobile_number'],
                        profile_type=row['profile_type'] or 'Student',
                        class_year=row['class_year'], year_of_birth=row['year_of_birth'],
                        school_name=row['school_name'],
                        preferred_study_time=row['preferred_study_time'],
                        learning_goals=row['learning_goals'],
                        avatar_color=row['avatar_color'] or '#3498db',
                    )
                    return True, "Existing user signed in via Google", user
                else:
                    # Create a brand-new OAuth user (no password)
                    username = email.split("@")[0]
                    # Ensure username uniqueness
                    base_username = username
                    suffix = 0
                    while True:
                        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                        if not cursor.fetchone():
                            break
                        suffix += 1
                        username = f"{base_username}{suffix}"

                    cursor.execute(
                        "INSERT INTO users (email, username, password_hash, salt, "
                        "first_name, last_name, oauth_provider, oauth_id) "
                        "VALUES (?, ?, NULL, NULL, ?, ?, ?, ?)",
                        (email.lower().strip(), username, first_name, last_name,
                         oauth_provider, oauth_id)
                    )
                    user_id = cursor.lastrowid
                    conn.commit()

                    if user_id:
                        self._create_default_user_preferences(user_id)

                    user = User(
                        user_id=user_id, email=email.lower().strip(), username=username,
                        created_at=str(datetime.now()), first_name=first_name,
                        last_name=last_name,
                    )
                    return True, "New account created via Google", user

        except Exception as e:
            return False, f"OAuth user error: {str(e)}", None

    def authenticate_user(self, email_or_username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Authenticate user with email/username and password."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find user by email or username
                cursor.execute('''
                    SELECT id, email, username, password_hash, salt, is_active, created_at, last_login,
                           first_name, last_name, mobile_number, profile_type, class_year, 
                           year_of_birth, school_name, preferred_study_time, learning_goals, avatar_color
                    FROM users 
                    WHERE (email = ? OR username = ?) AND is_active = 1
                ''', (email_or_username.lower().strip(), email_or_username.strip()))
                
                user_row = cursor.fetchone()
                
                if not user_row:
                    return False, "Invalid credentials", None
                
                # Verify password (supports both bcrypt and legacy pbkdf2 hashes)
                stored_hash = user_row['password_hash']
                salt = user_row['salt']
                
                # Check account lockout first
                lockout_msg = self._check_account_lockout(user_row['id'], conn)
                if lockout_msg:
                    return False, lockout_msg, None
                
                if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$'):
                    # bcrypt hash
                    if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                        self._record_failed_login(user_row['id'], conn)
                        return False, "Invalid credentials", None
                else:
                    # Legacy pbkdf2 hash - verify then upgrade to bcrypt
                    import hashlib
                    legacy_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                                       salt.encode('utf-8'), 100000).hex()
                    if legacy_hash != stored_hash:
                        self._record_failed_login(user_row['id'], conn)
                        return False, "Invalid credentials", None
                    # Upgrade to bcrypt on successful login
                    new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
                    cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?',
                                   (new_hash, '', user_row['id']))
                
                # Reset failed login count on success
                self._reset_failed_logins(user_row['id'], conn)
                
                # Update last login
                cursor.execute('''
                    UPDATE users 
                    SET last_login = CURRENT_TIMESTAMP, login_count = login_count + 1
                    WHERE id = ?
                ''', (user_row['id'],))
                conn.commit()
                
                # Create user object
                user = User(
                    user_id=user_row['id'],
                    email=user_row['email'],
                    username=user_row['username'],
                    created_at=user_row['created_at'],
                    last_login=user_row['last_login'],
                    is_active=bool(user_row['is_active']),
                    first_name=user_row['first_name'],
                    last_name=user_row['last_name'],
                    mobile_number=user_row['mobile_number'],
                    profile_type=user_row['profile_type'] or 'Student',
                    class_year=user_row['class_year'],
                    year_of_birth=user_row['year_of_birth'],
                    school_name=user_row['school_name'],
                    preferred_study_time=user_row['preferred_study_time'],
                    learning_goals=user_row['learning_goals'],
                    avatar_color=user_row['avatar_color'] or '#3498db'
                )
                
                return True, "Authentication successful", user
                
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
    def update_user_profile(self, user_id: int, profile_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update user profile information."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic update query
                valid_fields = [
                    'first_name', 'last_name', 'mobile_number', 'profile_type',
                    'class_year', 'year_of_birth', 'school_name', 'preferred_study_time',
                    'learning_goals', 'avatar_color'
                ]
                
                update_fields = []
                values = []
                
                for field, value in profile_data.items():
                    if field in valid_fields:
                        update_fields.append(f"{field} = ?")
                        values.append(value)
                
                if not update_fields:
                    return False, "No valid fields to update"
                
                values.append(user_id)
                
                query = f'''
                    UPDATE users 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                '''
                
                cursor.execute(query, values)
                
                if cursor.rowcount == 0:
                    return False, "User not found"
                
                conn.commit()
                return True, "Profile updated successfully"
                
        except Exception as e:
            return False, f"Error updating profile: {str(e)}"
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID with all profile information."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, email, username, created_at, last_login, is_active,
                           first_name, last_name, mobile_number, profile_type, class_year, 
                           year_of_birth, school_name, preferred_study_time, learning_goals, avatar_color
                    FROM users 
                    WHERE id = ? AND is_active = 1
                ''', (user_id,))
                
                user_row = cursor.fetchone()
                
                if not user_row:
                    return None
                
                return User(
                    user_id=user_row['id'],
                    email=user_row['email'],
                    username=user_row['username'],
                    created_at=user_row['created_at'],
                    last_login=user_row['last_login'],
                    is_active=bool(user_row['is_active']),
                    first_name=user_row['first_name'],
                    last_name=user_row['last_name'],
                    mobile_number=user_row['mobile_number'],
                    profile_type=user_row['profile_type'] or 'Student',
                    class_year=user_row['class_year'],
                    year_of_birth=user_row['year_of_birth'],
                    school_name=user_row['school_name'],
                    preferred_study_time=user_row['preferred_study_time'],
                    learning_goals=user_row['learning_goals'],
                    avatar_color=user_row['avatar_color'] or '#3498db'
                )
                
        except Exception as e:
            print(f"Error getting user by ID: {str(e)}")
            return None
    
    def _create_default_user_preferences(self, user_id: int) -> None:
        """Create default preferences for a new user."""
        default_preferences = {
            'daily_goal': '20',
            'session_goal': '10',
            'time_limit': '0',
            'preferred_mode': 'mixed',
            'difficulty_preference': 'medium',
            'theme': 'light',
            'sound_enabled': 'true',
            'notifications_enabled': 'true',
            'auto_pronunciation': 'false'
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for key, value in default_preferences.items():
                try:
                    cursor.execute('''
                        INSERT INTO user_preferences (user_id, preference_key, preference_value)
                        VALUES (?, ?, ?)
                    ''', (user_id, key, value))
                except IntegrityError:
                    pass  # preference already exists
            conn.commit()
    
    # Vocabulary Management Methods
    def load_vocabulary_from_text_file(self, text_file_path: str, user_id: int) -> int:
        """Load vocabulary words from text file into database for a specific user."""
        if not os.path.exists(text_file_path):
            print(f"❌ Text file not found: {text_file_path}")
            return 0
        
        print(f"📖 Loading vocabulary from: {text_file_path} for user {user_id}")
        
        with open(text_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Pattern for unnumbered format: "Word (Type) - Definition - Example."
        pattern = r'([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
        matches = re.findall(pattern, content)
        
        if not matches:
            # Try numbered format as fallback
            pattern_numbered = r'\d+\.\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
            matches = re.findall(pattern_numbered, content)
        
        if not matches:
            print("❌ No vocabulary words found in the expected format.")
            return 0
        
        # Load words into database
        loaded_count = 0
        skipped_count = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for match in matches:
                word, word_type, definition, example = match
                
                try:
                    cursor.execute('''
                        INSERT INTO vocabulary (user_id, word, word_type, definition, example, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (user_id, word.strip(), word_type.strip(), definition.strip(), example.strip(), 'seed_data'))
                    loaded_count += 1
                except IntegrityError:
                    # Word already exists for this user (duplicate)
                    skipped_count += 1
                    print(f"⚠️  Skipping duplicate for user {user_id}: {word.strip()}")
            
            conn.commit()
        
        print(f"✅ Loaded {loaded_count} words into database for user {user_id}")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} duplicate entries")
        
        return loaded_count
    
    def load_base_vocabulary_from_text_file(self, text_file_path: str, created_by_user_id: Optional[int] = None) -> int:
        """Load vocabulary words from text file into base vocabulary table."""
        if not os.path.exists(text_file_path):
            print(f"❌ Text file not found: {text_file_path}")
            return 0
        
        print(f"📖 Loading base vocabulary from: {text_file_path}")
        
        with open(text_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Pattern for unnumbered format: "Word (Type) - Definition - Example."
        pattern = r'([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
        matches = re.findall(pattern, content)
        
        if not matches:
            # Try numbered format as fallback
            pattern_numbered = r'\d+\.\s+([A-Za-z]+(?:\s+[A-Za-z]+)*)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
            matches = re.findall(pattern_numbered, content)
        
        if not matches:
            print("❌ No vocabulary words found in the expected format.")
            return 0
        
        # Load words into base vocabulary
        loaded_count = 0
        skipped_count = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for match in matches:
                word, word_type, definition, example = match
                
                try:
                    cursor.execute('''
                        INSERT INTO base_vocabulary (word, word_type, definition, example, created_by, approved_by)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (word.strip(), word_type.strip(), definition.strip(), example.strip(), created_by_user_id, created_by_user_id))
                    loaded_count += 1
                except IntegrityError:
                    # Word already exists in base vocabulary (duplicate)
                    skipped_count += 1
                    print(f"⚠️  Skipping duplicate base word: {word.strip()}")
            
            conn.commit()
        
        print(f"✅ Loaded {loaded_count} words into base vocabulary")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} duplicate entries")
        
        return loaded_count
    
    def copy_base_vocabulary_to_user(self, user_id: int) -> int:
        """Copy all active base vocabulary words to a user's personal vocabulary."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all active base vocabulary words
            cursor.execute('''
                SELECT id, word, word_type, definition, example, difficulty, category
                FROM base_vocabulary 
                WHERE is_active = 1
            ''')
            
            base_words = cursor.fetchall()
            copied_count = 0
            skipped_count = 0
            
            for base_word in base_words:
                try:
                    cursor.execute('''
                        INSERT INTO vocabulary 
                        (user_id, word, word_type, definition, example, difficulty, source, base_word_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        base_word['word'],
                        base_word['word_type'],
                        base_word['definition'],
                        base_word['example'],
                        base_word['difficulty'],
                        'base_vocabulary',
                        base_word['id']
                    ))
                    copied_count += 1
                except IntegrityError:
                    # Word already exists for this user
                    skipped_count += 1
            
            conn.commit()
            
        print(f"✅ Copied {copied_count} base words to user {user_id}")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} words already in user's vocabulary")
        
        return copied_count
    
    def get_user_words(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all vocabulary words for a specific user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM vocabulary 
                WHERE user_id = ? 
                ORDER BY LOWER(word)
            ''', (user_id,))
            
            words = []
            for row in cursor.fetchall():
                word = VocabularyWord(
                    word_id=row['id'],
                    user_id=row['user_id'],
                    word=row['word'],
                    word_type=row['word_type'],
                    definition=row['definition'],
                    example=row['example'],
                    difficulty=row['difficulty'],
                    times_reviewed=row['times_reviewed'],
                    times_correct=row['times_correct'],
                    mastery_level=row['mastery_level'],
                    created_at=row['created_at'],
                    last_reviewed=row['last_reviewed'],
                    is_hidden=row['is_hidden'] or 0
                )
                words.append(word.to_dict())
            
            return words
    
    # Word Likes Management
    def like_word(self, user_id: int, word_id: int) -> Tuple[bool, str]:
        """Like a word for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if word exists and belongs to user
                cursor.execute('''
                    SELECT id, base_word_id FROM vocabulary 
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                word_row = cursor.fetchone()
                if not word_row:
                    return False, "Word not found or not accessible"
                
                # Insert like
                cursor.execute('''
                    INSERT INTO word_likes (user_id, word_id)
                    VALUES (?, ?)
                ''', (user_id, word_id))
                
                # Update like count on the word
                cursor.execute('''
                    UPDATE vocabulary 
                    SET like_count = like_count + 1 
                    WHERE id = ?
                ''', (word_id,))
                
                # If this is a base vocabulary word, update base vocabulary like count too
                if word_row['base_word_id']:
                    cursor.execute('''
                        UPDATE base_vocabulary 
                        SET total_likes = total_likes + 1 
                        WHERE id = ?
                    ''', (word_row['base_word_id'],))
                
                conn.commit()
                return True, "Word liked successfully"
                
        except IntegrityError:
            return False, "You have already liked this word"
        except Exception as e:
            return False, f"Error liking word: {str(e)}"
    
    def unlike_word(self, user_id: int, word_id: int) -> Tuple[bool, str]:
        """Unlike a word for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if like exists
                cursor.execute('''
                    SELECT id FROM word_likes 
                    WHERE user_id = ? AND word_id = ?
                ''', (user_id, word_id))
                
                if not cursor.fetchone():
                    return False, "You haven't liked this word"
                
                # Get word info for base word update
                cursor.execute('''
                    SELECT base_word_id FROM vocabulary 
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                word_row = cursor.fetchone()
                if not word_row:
                    return False, "Word not found"
                
                # Remove like
                cursor.execute('''
                    DELETE FROM word_likes 
                    WHERE user_id = ? AND word_id = ?
                ''', (user_id, word_id))
                
                # Update like count on the word
                cursor.execute('''
                    UPDATE vocabulary 
                    SET like_count = CASE 
                        WHEN like_count > 0 THEN like_count - 1 
                        ELSE 0 
                    END
                    WHERE id = ?
                ''', (word_id,))
                
                # If this is a base vocabulary word, update base vocabulary like count too
                if word_row['base_word_id']:
                    cursor.execute('''
                        UPDATE base_vocabulary 
                        SET total_likes = CASE 
                            WHEN total_likes > 0 THEN total_likes - 1 
                            ELSE 0 
                        END
                        WHERE id = ?
                    ''', (word_row['base_word_id'],))
                
                conn.commit()
                return True, "Word unliked successfully"
                
        except Exception as e:
            return False, f"Error unliking word: {str(e)}"
    
    def get_user_word_likes(self, user_id: int) -> List[int]:
        """Get list of word IDs that a user has liked."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT word_id FROM word_likes 
                WHERE user_id = ?
            ''', (user_id,))
            
            return [row['word_id'] for row in cursor.fetchall()]
    
    def get_most_liked_words(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most liked base vocabulary words."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT word, word_type, definition, example, total_likes, category
                FROM base_vocabulary 
                WHERE is_active = 1 AND total_likes > 0
                ORDER BY total_likes DESC, LOWER(word)
                LIMIT ?
            ''', (limit,))
            
            words = []
            for row in cursor.fetchall():
                words.append({
                    'word': row['word'],
                    'word_type': row['word_type'],
                    'definition': row['definition'],
                    'example': row['example'],
                    'total_likes': row['total_likes'],
                    'category': row['category']
                })
            
            return words
    
    # Password Reset Management
    def create_password_reset_token(self, email: str) -> Tuple[bool, str, Optional[str]]:
        """Create a password reset token for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find user by email
                cursor.execute('''
                    SELECT id, username FROM users 
                    WHERE email = ? AND is_active = 1
                ''', (email.lower().strip(),))
                
                user_row = cursor.fetchone()
                if not user_row:
                    # Don't reveal if email exists or not for security
                    return True, "If this email is registered, you will receive reset instructions", None
                
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=24)  # Token expires in 24 hours
                
                # Clean up old tokens for this user
                cursor.execute('''
                    UPDATE password_reset_tokens 
                    SET used = 1 
                    WHERE user_id = ? AND used = 0
                ''', (user_row['id'],))
                
                # Insert new token
                cursor.execute('''
                    INSERT INTO password_reset_tokens (user_id, token, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_row['id'], reset_token, expires_at))
                
                conn.commit()
                
                return True, "Password reset instructions sent to your email", reset_token
                
        except Exception as e:
            return False, f"Error creating reset token: {str(e)}", None
    
    def validate_reset_token(self, token: str) -> Tuple[bool, str, Optional[int]]:
        """Validate a password reset token."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, expires_at, used FROM password_reset_tokens 
                    WHERE token = ?
                ''', (token,))
                
                token_row = cursor.fetchone()
                if not token_row:
                    return False, "Invalid reset token", None
                
                if token_row['used']:
                    return False, "Reset token has already been used", None
                
                if datetime.now() > datetime.fromisoformat(token_row['expires_at']):
                    return False, "Reset token has expired", None
                
                return True, "Token is valid", token_row['user_id']
                
        except Exception as e:
            return False, f"Error validating token: {str(e)}", None
    
    def reset_password_with_token(self, token: str, new_password: str) -> Tuple[bool, str]:
        """Reset user password using a valid token."""
        try:
            # Validate token first
            valid, message, user_id = self.validate_reset_token(token)
            if not valid:
                return False, message
            
            pw_valid, pw_msg = self.validate_password_strength(new_password)
            if not pw_valid:
                return False, pw_msg
            
            # Hash new password with bcrypt
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
            salt = ''  # salt is embedded in bcrypt hash
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update user password
                cursor.execute('''
                    UPDATE users 
                    SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (password_hash, salt, user_id))
                
                # Mark token as used
                cursor.execute('''
                    UPDATE password_reset_tokens 
                    SET used = 1 
                    WHERE token = ?
                ''', (token,))
                
                # Invalidate all user sessions for security
                cursor.execute('''
                    DELETE FROM user_sessions 
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                
                return True, "Password reset successfully"
                
        except Exception as e:
            return False, f"Error resetting password: {str(e)}"
    
    # Word Management  
    def hide_word_for_user(self, user_id: int, word_id: int) -> Tuple[bool, str]:
        """Hide a word for a user (instead of deleting it)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if word exists and belongs to user
                cursor.execute('''
                    SELECT source FROM vocabulary 
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                word_row = cursor.fetchone()
                if not word_row:
                    return False, "Word not found or not accessible"
                
                # Mark word as hidden
                cursor.execute('''
                    UPDATE vocabulary 
                    SET is_hidden = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                conn.commit()
                return True, "Word hidden from your vocabulary"
                
        except Exception as e:
            return False, f"Error hiding word: {str(e)}"
    
    def unhide_word_for_user(self, user_id: int, word_id: int) -> Tuple[bool, str]:
        """Unhide a word for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE vocabulary 
                    SET is_hidden = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Word restored to your vocabulary"
                else:
                    return False, "Word not found"
                    
        except Exception as e:
            return False, f"Error unhiding word: {str(e)}"

    def add_user_word(self, user_id: int, word: str, word_type: str, definition: str, example: str) -> Tuple[bool, str]:
        """Add a new word for a specific user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vocabulary (user_id, word, word_type, definition, example)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, word.strip(), word_type.strip(), definition.strip(), example.strip()))
                conn.commit()
                return True, "Word added successfully"
        except IntegrityError:
            return False, "Word already exists in your vocabulary"
        except Exception as e:
            return False, f"Error adding word: {str(e)}"
    
    def remove_user_word(self, user_id: int, word_id: int) -> Tuple[bool, str]:
        """Remove a word for a specific user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM vocabulary 
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Word removed successfully"
                else:
                    return False, "Word not found or not owned by user"
        except Exception as e:
            return False, f"Error removing word: {str(e)}"
    
    def update_user_word(self, user_id: int, word_id: int, word: str, word_type: str, definition: str, example: str) -> Tuple[bool, str]:
        """Update an existing word for a specific user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First verify the word belongs to the user
                cursor.execute('''
                    SELECT id FROM vocabulary WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                if not cursor.fetchone():
                    return False, "Word not found or not owned by user"
                
                # Check if another word with the same text already exists for this user (excluding current word)
                cursor.execute('''
                    SELECT id FROM vocabulary 
                    WHERE user_id = ? AND LOWER(word) = LOWER(?) AND id != ?
                ''', (user_id, word.strip(), word_id))
                
                if cursor.fetchone():
                    return False, "Another word with this name already exists in your vocabulary"
                
                # Update the word
                cursor.execute('''
                    UPDATE vocabulary 
                    SET word = ?, word_type = ?, definition = ?, example = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (word.strip(), word_type.strip(), definition.strip(), example.strip(), word_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Word updated successfully"
                else:
                    return False, "Word not found or not owned by user"
        except Exception as e:
            return False, f"Error updating word: {str(e)}"
    
    def record_word_review(self, user_id: int, word_id: int, correct: bool) -> Tuple[bool, str]:
        """Record a word review (correct/incorrect) for a specific user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, check if the word belongs to the user
                cursor.execute('''
                    SELECT times_reviewed, times_correct FROM vocabulary 
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                result = cursor.fetchone()
                if not result:
                    return False, "Word not found or not owned by user"
                
                current_times_reviewed = result['times_reviewed']
                current_times_correct = result['times_correct']
                
                # Update the review statistics
                new_times_reviewed = current_times_reviewed + 1
                new_times_correct = current_times_correct + (1 if correct else 0)
                
                # Calculate new mastery level based on accuracy and review count
                accuracy = (new_times_correct / new_times_reviewed) * 100 if new_times_reviewed > 0 else 0
                
                # Enhanced mastery level calculation with minimum review requirements:
                # Level 0 (needs practice): accuracy < 50% OR very few reviews
                # Level 1 (learning): 50-70% accuracy with 2+ reviews  
                # Level 2 (good): 70-85% accuracy with 3+ reviews
                # Level 3 (mastered): 85%+ accuracy with 4+ reviews
                
                if new_times_reviewed < 2 or accuracy < 50:
                    mastery_level = 0
                elif new_times_reviewed >= 2 and accuracy >= 50 and accuracy < 70:
                    mastery_level = 1
                elif new_times_reviewed >= 3 and accuracy >= 70 and accuracy < 85:
                    mastery_level = 2
                elif new_times_reviewed >= 4 and accuracy >= 85:
                    mastery_level = 3
                else:
                    # Keep current level if not enough data or borderline performance
                    cursor.execute('SELECT mastery_level FROM vocabulary WHERE id = ? AND user_id = ?', (word_id, user_id))
                    current_mastery = cursor.fetchone()['mastery_level']
                    mastery_level = current_mastery
                
                # Update the word statistics
                cursor.execute('''
                    UPDATE vocabulary 
                    SET times_reviewed = ?, 
                        times_correct = ?, 
                        mastery_level = ?,
                        last_reviewed = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (new_times_reviewed, new_times_correct, mastery_level, word_id, user_id))
                
                conn.commit()
                
                result_message = f"Review recorded: {'correct' if correct else 'incorrect'} " \
                               f"(Accuracy: {accuracy:.1f}%, Mastery: {mastery_level})"
                
                return True, result_message
                
        except Exception as e:
            return False, f"Error recording review: {str(e)}"
    
    def update_word_difficulty(self, user_id: int, word_id: int, difficulty: str) -> Tuple[bool, str]:
        """Update the difficulty level of a word for a specific user."""
        try:
            if difficulty not in ['easy', 'medium', 'hard']:
                return False, "Invalid difficulty level. Must be 'easy', 'medium', or 'hard'"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if word exists and belongs to user
                cursor.execute('''
                    SELECT id FROM vocabulary 
                    WHERE id = ? AND user_id = ?
                ''', (word_id, user_id))
                
                if not cursor.fetchone():
                    return False, "Word not found or not owned by user"
                
                # Update the difficulty
                cursor.execute('''
                    UPDATE vocabulary 
                    SET difficulty = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                ''', (difficulty, word_id, user_id))
                
                conn.commit()
                return True, f"Word difficulty updated to {difficulty}"
                
        except Exception as e:
            return False, f"Error updating word difficulty: {str(e)}"
    
    # Study Session Management Methods
    def create_study_session(self, user_id: int, session_type: str = 'review', 
                           word_goal: int = 10, time_limit: int = 0, 
                           difficulty: str = 'all') -> Tuple[bool, str, Optional[int]]:
        """Create a new study session for a user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO study_sessions 
                    (user_id, session_type, session_goal, words_reviewed, words_correct, is_completed)
                    VALUES (?, ?, ?, 0, 0, 0)
                ''', (user_id, session_type, word_goal))
                
                session_id = cursor.lastrowid
                conn.commit()
                
                return True, f"Study session created with ID {session_id}", session_id
                
        except Exception as e:
            return False, f"Error creating study session: {str(e)}", None
    
    def update_study_session(self, user_id: int, session_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update a study session with final results."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if session exists and belongs to user
                cursor.execute('''
                    SELECT id FROM study_sessions 
                    WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
                
                if not cursor.fetchone():
                    return False, "Study session not found or not owned by user"
                
                # Update session with final data
                words_reviewed = data.get('words_reviewed', 0)
                words_correct = data.get('words_correct', 0)
                duration_seconds = data.get('duration_seconds', 0)
                accuracy = (words_correct / words_reviewed * 100) if words_reviewed > 0 else 0
                
                cursor.execute('''
                    UPDATE study_sessions 
                    SET end_time = CURRENT_TIMESTAMP,
                        words_reviewed = ?,
                        words_correct = ?,
                        duration_seconds = ?,
                        accuracy_percentage = ?,
                        is_completed = 1
                    WHERE id = ? AND user_id = ?
                ''', (words_reviewed, words_correct, duration_seconds, accuracy, session_id, user_id))
                
                conn.commit()
                return True, "Study session updated successfully"
                
        except Exception as e:
            return False, f"Error updating study session: {str(e)}"
    
    def update_session_progress(self, user_id: int, session_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update study session progress (called during session)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if session exists and belongs to user
                cursor.execute('''
                    SELECT id FROM study_sessions 
                    WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
                
                if not cursor.fetchone():
                    return False, "Study session not found or not owned by user"
                
                # Update progress
                words_reviewed = data.get('words_reviewed', 0)
                words_correct = data.get('words_correct', 0)
                accuracy = data.get('accuracy', 0)
                time_elapsed = data.get('time_elapsed', 0)
                
                cursor.execute('''
                    UPDATE study_sessions 
                    SET words_reviewed = ?,
                        words_correct = ?,
                        accuracy_percentage = ?,
                        duration_seconds = ?
                    WHERE id = ? AND user_id = ?
                ''', (words_reviewed, words_correct, accuracy, time_elapsed, session_id, user_id))
                
                conn.commit()
                return True, "Session progress updated"
                
        except Exception as e:
            return False, f"Error updating session progress: {str(e)}"
    
    def reset_study_session(self, user_id: int, session_id: int) -> Tuple[bool, str]:
        """Reset a study session to start over."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if session exists and belongs to user
                cursor.execute('''
                    SELECT id FROM study_sessions 
                    WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
                
                if not cursor.fetchone():
                    return False, "Study session not found or not owned by user"
                
                # Reset session statistics
                cursor.execute('''
                    UPDATE study_sessions 
                    SET words_reviewed = 0,
                        words_correct = 0,
                        accuracy_percentage = 0,
                        duration_seconds = 0,
                        start_time = CURRENT_TIMESTAMP,
                        end_time = NULL,
                        is_completed = 0
                    WHERE id = ? AND user_id = ?
                ''', (session_id, user_id))
                
                # Also delete any existing session words for this session
                cursor.execute('''
                    DELETE FROM study_session_words 
                    WHERE session_id = ?
                ''', (session_id,))
                
                conn.commit()
                return True, "Study session reset successfully"
                
        except Exception as e:
            return False, f"Error resetting study session: {str(e)}"
    
    def search_user_words(self, user_id: int, search_query: str) -> List[Dict[str, Any]]:
        """Search vocabulary words for a specific user."""
        if not search_query.strip():
            return self.get_user_words(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{search_query.strip()}%"
            cursor.execute('''
                SELECT * FROM vocabulary 
                WHERE user_id = ? AND (
                    word LIKE ? OR 
                    definition LIKE ? OR 
                    example LIKE ?
                )
                ORDER BY LOWER(word)
            ''', (user_id, search_pattern, search_pattern, search_pattern))
            
            words = []
            for row in cursor.fetchall():
                word = VocabularyWord(
                    word_id=row['id'],
                    user_id=row['user_id'],
                    word=row['word'],
                    word_type=row['word_type'],
                    definition=row['definition'],
                    example=row['example'],
                    difficulty=row['difficulty'],
                    times_reviewed=row['times_reviewed'],
                    times_correct=row['times_correct'],
                    mastery_level=row['mastery_level'],
                    created_at=row['created_at'],
                    last_reviewed=row['last_reviewed']
                )
                words.append(word.to_dict())
            
            return words

    # Admin Methods
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users for admin management."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT u.id, u.email, u.username, u.is_admin, u.created_at,
                           COUNT(v.id) as word_count
                    FROM users u
                    LEFT JOIN vocabulary v ON u.id = v.user_id
                    GROUP BY u.id, u.email, u.username, u.is_admin, u.created_at
                    ORDER BY u.created_at DESC
                ''')
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'id': row['id'],
                        'email': row['email'],
                        'username': row['username'],
                        'is_admin': bool(row['is_admin']),
                        'created_at': row['created_at'],
                        'word_count': row['word_count']
                    })
                
                return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []

    def update_user(self, user_id: int, email: Optional[str] = None, username: Optional[str] = None, 
                   is_admin: Optional[bool] = None) -> Tuple[bool, str]:
        """Update user details (admin only)."""
        try:
            updates = []
            values = []
            
            if email is not None:
                # Check if email already exists for different user
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (email, user_id))
                    if cursor.fetchone():
                        return False, "Email already exists"
                updates.append("email = ?")
                values.append(email)
            
            if username is not None:
                # Check if username already exists for different user
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id))
                    if cursor.fetchone():
                        return False, "Username already exists"
                updates.append("username = ?")
                values.append(username)
            
            if is_admin is not None:
                updates.append("is_admin = ?")
                values.append(1 if is_admin else 0)
            
            if not updates:
                return False, "No updates provided"
            
            values.append(user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE users 
                    SET {", ".join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', values)
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "User updated successfully"
                else:
                    return False, "User not found"
                    
        except Exception as e:
            return False, f"Error updating user: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """Delete a user and all their data (admin only)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False, "User not found"
                
                # Don't allow deleting the first admin user (ID = 1)
                if user_id == 1:
                    return False, "Cannot delete the primary admin user"
                
                # Delete user's vocabulary
                cursor.execute('DELETE FROM vocabulary WHERE user_id = ?', (user_id,))
                
                # Delete user's word likes
                cursor.execute('DELETE FROM word_likes WHERE user_id = ?', (user_id,))
                
                # Delete user's preferences
                cursor.execute('DELETE FROM user_preferences WHERE user_id = ?', (user_id,))
                
                # Delete user's sessions
                cursor.execute('DELETE FROM user_sessions WHERE user_id = ?', (user_id,))
                
                # Delete password reset tokens
                cursor.execute('DELETE FROM password_reset_tokens WHERE user_id = ?', (user_id,))
                
                # Finally delete the user
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                
                conn.commit()
                return True, f"User '{user['username']}' and all associated data deleted successfully"
                
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"

    def reload_base_vocabulary_for_user(self, user_id: int) -> Tuple[bool, str, int]:
        """Reload base vocabulary for a specific user (admin only)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False, "User not found", 0
                
                # Delete existing vocabulary for user (only base vocabulary words)
                cursor.execute('''
                    DELETE FROM vocabulary 
                    WHERE user_id = ? AND source = "base"
                ''', (user_id,))
                deleted_count = cursor.rowcount
                
                # Copy base vocabulary to user directly within this connection
                cursor.execute('''
                    SELECT id, word, word_type, definition, example, difficulty, category
                    FROM base_vocabulary 
                    WHERE is_active = 1
                ''')
                
                base_words = cursor.fetchall()
                copied_count = 0
                skipped_count = 0
                
                for base_word in base_words:
                    try:
                        cursor.execute('''
                            INSERT INTO vocabulary 
                            (user_id, word, word_type, definition, example, difficulty, source, base_word_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            user_id,
                            base_word['word'],
                            base_word['word_type'],
                            base_word['definition'],
                            base_word['example'],
                            base_word['difficulty'],
                            'base_vocabulary',
                            base_word['id']
                        ))
                        copied_count += 1
                    except IntegrityError:
                        # Word already exists for this user
                        skipped_count += 1
                
                conn.commit()
                
                print(f"✅ Copied {copied_count} base words to user {user_id}")
                if skipped_count > 0:
                    print(f"⚠️  Skipped {skipped_count} words already in user's vocabulary")
                
                return True, f"Reloaded {copied_count} base words for user '{user['username']}' (removed {deleted_count} old base words)", copied_count
                
        except Exception as e:
            return False, f"Error reloading base vocabulary: {str(e)}", 0

    def is_user_admin(self, user_id: int) -> bool:
        """Check if a user is an admin."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
                result = cursor.fetchone()
                return bool(result['is_admin']) if result else False
        except Exception as e:
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics for admin dashboard."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # User stats
                cursor.execute('SELECT COUNT(*) as total_users FROM users')
                total_users = cursor.fetchone()['total_users']
                
                cursor.execute('SELECT COUNT(*) as admin_users FROM users WHERE is_admin = 1')
                admin_users = cursor.fetchone()['admin_users']
                
                # Word stats
                cursor.execute('SELECT COUNT(*) as total_words FROM vocabulary')
                total_words = cursor.fetchone()['total_words']
                
                cursor.execute('SELECT COUNT(*) as base_words FROM base_vocabulary WHERE is_active = 1')
                base_words = cursor.fetchone()['base_words']
                
                # Activity stats
                cursor.execute('SELECT COUNT(*) as total_likes FROM word_likes')
                total_likes = cursor.fetchone()['total_likes']
                
                cursor.execute('''
                    SELECT COUNT(*) as active_sessions 
                    FROM user_sessions 
                    WHERE expires_at > CURRENT_TIMESTAMP
                ''')
                active_sessions = cursor.fetchone()['active_sessions']
                
                return {
                    'users': {
                        'total': total_users,
                        'admins': admin_users,
                        'regular': total_users - admin_users
                    },
                    'words': {
                        'total': total_words,
                        'base_vocabulary': base_words
                    },
                    'activity': {
                        'total_likes': total_likes,
                        'active_sessions': active_sessions
                    }
                }
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return {
                'users': {'total': 0, 'admins': 0, 'regular': 0},
                'words': {'total': 0, 'base_vocabulary': 0},
                'activity': {'total_likes': 0, 'active_sessions': 0}
            }

    def analyze_user_learning_patterns(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze user's learning patterns to provide insights for AI suggestions.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dict containing analysis results
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get user's words with review statistics
            cursor.execute('''
                SELECT word, word_type, difficulty, times_reviewed, 
                       times_correct, mastery_level, last_reviewed
                FROM vocabulary
                WHERE user_id = ? AND (is_hidden = 0 OR is_hidden IS NULL)
                ORDER BY last_reviewed DESC
            ''', (user_id,))
            
            user_words = cursor.fetchall()
            
            if not user_words:
                return {
                    "total_words": 0,
                    "words_mastered": 0,
                    "average_accuracy": 0,
                    "difficult_words": [],
                    "easy_words": [],
                    "common_word_types": [],
                    "suggested_level": "Beginner",
                    "last_session_date": None
                }
            
            # Calculate statistics
            total_words = len(user_words)
            total_reviews = sum(row['times_reviewed'] for row in user_words if row['times_reviewed'])
            total_correct = sum(row['times_correct'] for row in user_words if row['times_correct'])
            
            # Calculate words mastered (mastery_level >= 3)
            words_mastered = sum(1 for row in user_words if row['mastery_level'] >= 3)
            
            # Calculate average accuracy
            average_accuracy = (total_correct / total_reviews * 100) if total_reviews > 0 else 50
            
            # Categorize words by difficulty
            easy_words = [row['word'] for row in user_words if row['difficulty'] == 'easy']
            difficult_words = [row['word'] for row in user_words if row['difficulty'] == 'hard']
            
            # Find common word types
            word_type_counts = {}
            for row in user_words:
                word_type = row['word_type']
                word_type_counts[word_type] = word_type_counts.get(word_type, 0) + 1
            
            common_word_types = sorted(word_type_counts.keys(), 
                                     key=lambda x: word_type_counts[x], 
                                     reverse=True)[:3]
            
            # Determine suggested level based on accuracy and word count
            if average_accuracy >= 80 and total_words >= 50:
                suggested_level = "Advanced"
            elif average_accuracy >= 60 and total_words >= 20:
                suggested_level = "Intermediate"
            else:
                suggested_level = "Beginner"
            
            # Get last session date
            last_session_date = None
            if user_words:
                last_reviewed = max((row['last_reviewed'] for row in user_words if row['last_reviewed']), default=None)
                if last_reviewed:
                    last_session_date = last_reviewed
            
            return {
                "total_words": total_words,
                "words_mastered": words_mastered,
                "average_accuracy": round(average_accuracy, 1),
                "difficult_words": difficult_words[:5],  # Top 5 difficult words
                "easy_words": easy_words[:5],  # Top 5 easy words
                "common_word_types": common_word_types,
                "suggested_level": suggested_level,
                "last_session_date": last_session_date,
                "total_reviews": total_reviews,
                "total_correct": total_correct
            }
            
        except SQLAlchemyError as e:
            print(f"Database error in analyze_user_learning_patterns: {e}")
            return {
                "total_words": 0,
                "words_mastered": 0,
                "average_accuracy": 0,
                "difficult_words": [],
                "easy_words": [],
                "common_word_types": [],
                "suggested_level": "Beginner",
                "last_session_date": None
            }
        finally:
            if 'conn' in locals():
                conn.close()
    
    def record_ai_suggestion_feedback(self, user_id: int, word: str, difficulty: str, added_to_vocab: bool) -> bool:
        """
        Record user feedback on AI word suggestions for future improvements.
        
        Args:
            user_id: The user's ID
            word: The suggested word
            difficulty: User's difficulty rating (easy/medium/hard)
            added_to_vocab: Whether user added the word to their vocabulary
            
        Returns:
            bool: Success status
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Table created by ORM models in init_tables()
            cursor.execute('''
                INSERT INTO ai_suggestion_feedback 
                (user_id, word, difficulty, added_to_vocab)
                VALUES (?, ?, ?, ?)
            ''', (user_id, word, difficulty, added_to_vocab))
            
            conn.commit()
            return True
            
        except SQLAlchemyError as e:
            print(f"Database error in record_ai_suggestion_feedback: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    # AI Learning Session Methods
    def create_ai_learning_session(self, user_id: int, target_words: int) -> Optional[int]:
        """Create a new AI learning session."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ai_learning_sessions (user_id, target_words)
                    VALUES (?, ?)
                ''', (user_id, target_words))
                session_id = cursor.lastrowid
                conn.commit()
                return session_id
        except SQLAlchemyError as e:
            print(f"Database error creating AI learning session: {e}")
            return None

    def get_ai_learning_session(self, session_id: int) -> Optional[Dict]:
        """Get AI learning session details."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM ai_learning_sessions WHERE id = ?
                ''', (session_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except SQLAlchemyError as e:
            print(f"Database error getting AI learning session: {e}")
            return None

    def update_ai_learning_session_progress(self, session_id: int, words_completed: int, 
                                          words_correct: int, current_difficulty: str) -> bool:
        """Update AI learning session progress."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ai_learning_sessions 
                    SET words_completed = ?, words_correct = ?, current_difficulty = ?
                    WHERE id = ?
                ''', (words_completed, words_correct, current_difficulty, session_id))
                conn.commit()
                return True
        except SQLAlchemyError as e:
            print(f"Database error updating AI learning session: {e}")
            return False

    def complete_ai_learning_session(self, session_id: int, total_time_seconds: int) -> bool:
        """Complete an AI learning session."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE ai_learning_sessions 
                    SET is_completed = 1, session_ended_at = CURRENT_TIMESTAMP, 
                        total_time_seconds = ?
                    WHERE id = ?
                ''', (total_time_seconds, session_id))
                conn.commit()
                return True
        except SQLAlchemyError as e:
            print(f"Database error completing AI learning session: {e}")
            return False

    def add_word_to_ai_session(self, session_id: int, word_text: str, word_id: Optional[int] = None,
                              base_word_id: Optional[int] = None, difficulty_level: str = 'medium',
                              word_order: int = 0) -> bool:
        """Add a word to an AI learning session."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ai_learning_session_words 
                    (session_id, word_id, base_word_id, word_text, difficulty_level, word_order)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (session_id, word_id, base_word_id, word_text, difficulty_level, word_order))
                conn.commit()
                return True
        except SQLAlchemyError as e:
            print(f"Database error adding word to AI session: {e}")
            return False

    def record_ai_session_response(self, session_id: int, word_text: str, user_response: str,
                                 is_correct: bool, response_time_ms: int = 0) -> bool:
        """Record user response for a word in AI learning session and update vocabulary mastery."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, get the session to find the user
                cursor.execute('SELECT user_id FROM ai_learning_sessions WHERE id = ?', (session_id,))
                session_result = cursor.fetchone()
                if not session_result:
                    print(f"No session found with id {session_id}")
                    return False
                
                user_id = session_result['user_id']
                
                # Record response in AI session
                cursor.execute('''
                    UPDATE ai_learning_session_words 
                    SET user_response = ?, is_correct = ?, response_time_ms = ?
                    WHERE session_id = ? AND word_text = ?
                ''', (user_response, is_correct, response_time_ms, session_id, word_text))
                
                # Update user's vocabulary mastery if this word exists in their vocabulary
                cursor.execute('''
                    SELECT id, times_reviewed, times_correct, mastery_level 
                    FROM vocabulary 
                    WHERE user_id = ? AND LOWER(word) = LOWER(?)
                ''', (user_id, word_text))
                
                vocab_result = cursor.fetchone()
                if vocab_result:
                    # Word exists in user's vocabulary - update mastery
                    word_id = vocab_result['id']
                    current_times_reviewed = vocab_result['times_reviewed'] or 0
                    current_times_correct = vocab_result['times_correct'] or 0
                    
                    # Update review statistics
                    new_times_reviewed = current_times_reviewed + 1
                    new_times_correct = current_times_correct + (1 if is_correct else 0)
                    
                    # Calculate new mastery level based on accuracy and review count
                    accuracy = (new_times_correct / new_times_reviewed) * 100 if new_times_reviewed > 0 else 0
                    
                    # Enhanced mastery level calculation:
                    # Level 0 (needs practice): accuracy < 50% OR very few reviews
                    # Level 1 (learning): 50-70% accuracy with 2+ reviews  
                    # Level 2 (good): 70-85% accuracy with 3+ reviews
                    # Level 3 (mastered): 85%+ accuracy with 4+ reviews
                    
                    if new_times_reviewed < 2 or accuracy < 50:
                        mastery_level = 0
                    elif new_times_reviewed >= 2 and accuracy >= 50 and accuracy < 70:
                        mastery_level = 1
                    elif new_times_reviewed >= 3 and accuracy >= 70 and accuracy < 85:
                        mastery_level = 2
                    elif new_times_reviewed >= 4 and accuracy >= 85:
                        mastery_level = 3
                    else:
                        # Keep current level if not enough data or borderline performance
                        mastery_level = vocab_result['mastery_level']
                    
                    # Update the word statistics
                    cursor.execute('''
                        UPDATE vocabulary 
                        SET times_reviewed = ?, 
                            times_correct = ?, 
                            mastery_level = ?,
                            last_reviewed = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    ''', (new_times_reviewed, new_times_correct, mastery_level, word_id, user_id))
                    
                    print(f"Updated vocabulary word '{word_text}' for user {user_id}: "
                          f"accuracy={accuracy:.1f}%, mastery={mastery_level}")
                else:
                    print(f"Word '{word_text}' not found in user {user_id}'s vocabulary - AI session only")
                
                conn.commit()
                return True
        except SQLAlchemyError as e:
            print(f"Database error recording AI session response: {e}")
            return False

    def get_ai_session_summary(self, session_id: int) -> Optional[Dict]:
        """Get summary statistics for an AI learning session."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get session details
                cursor.execute('''
                    SELECT s.*, 
                           COUNT(w.id) as total_words_attempted,
                           SUM(CASE WHEN w.is_correct = 1 THEN 1 ELSE 0 END) as words_correct,
                           AVG(w.response_time_ms) as avg_response_time
                    FROM ai_learning_sessions s
                    LEFT JOIN ai_learning_session_words w ON s.id = w.session_id
                    WHERE s.id = ?
                    GROUP BY s.id
                ''', (session_id,))
                
                row = cursor.fetchone()
                if row:
                    summary = dict(row)
                    
                    # Get word-by-word breakdown
                    cursor.execute('''
                        SELECT word_text, difficulty_level, is_correct, user_response, response_time_ms
                        FROM ai_learning_session_words 
                        WHERE session_id = ?
                        ORDER BY word_order
                    ''', (session_id,))
                    
                    summary['words_breakdown'] = [dict(row) for row in cursor.fetchall()]
                    return summary
                return None
        except SQLAlchemyError as e:
            print(f"Database error getting AI session summary: {e}")
            return None

    def get_words_for_ai_learning(self, user_id: int, difficulty: str = 'medium', 
                                 limit: int = 20, exclude_mastered_words: bool = True) -> List[Dict]:
        """Get words from user's vocabulary for AI learning sessions, excluding already known words."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check how many words user has in their vocabulary
                cursor.execute('SELECT COUNT(*) as count FROM vocabulary WHERE user_id = ?', (user_id,))
                user_word_count = cursor.fetchone()['count']
                print(f"Debug: User {user_id} has {user_word_count} words in their vocabulary")
                
                # Check what difficulty values exist in user's vocabulary
                cursor.execute('SELECT DISTINCT difficulty FROM vocabulary WHERE user_id = ?', (user_id,))
                available_difficulties = [row['difficulty'] for row in cursor.fetchall()]
                print(f"Debug: Available difficulties in user vocabulary: {available_difficulties}")
                
                if exclude_mastered_words:
                    # Count words that are not mastered (mastery_level < 3 means not "already know")
                    cursor.execute('''
                        SELECT COUNT(*) as count FROM vocabulary 
                        WHERE user_id = ? AND mastery_level < 3
                    ''', (user_id,))
                    available_words = cursor.fetchone()['count']
                    print(f"Debug: {available_words} words available for learning (excluding mastered)")
                
                # Determine target difficulty
                if difficulty in available_difficulties:
                    target_difficulty = difficulty
                elif available_difficulties:
                    target_difficulty = available_difficulties[0]  # Use first available
                    print(f"Debug: Requested difficulty '{difficulty}' not found, using '{target_difficulty}'")
                else:
                    print("Debug: No words found in user vocabulary")
                    return []
                
                # Build the query to get words from user's vocabulary
                if exclude_mastered_words:
                    # Exclude words with mastery_level 3 (considered "already know")
                    query = '''
                        SELECT * FROM vocabulary 
                        WHERE user_id = ? AND difficulty = ? AND mastery_level < 3
                        ORDER BY RANDOM()
                        LIMIT ?
                    '''
                    params = (user_id, target_difficulty, limit)
                else:
                    # Include all words regardless of mastery level
                    query = '''
                        SELECT * FROM vocabulary 
                        WHERE user_id = ? AND difficulty = ?
                        ORDER BY RANDOM()
                        LIMIT ?
                    '''
                    params = (user_id, target_difficulty, limit)
                
                print(f"Debug: Querying user vocabulary for difficulty '{target_difficulty}', excluding mastered: {exclude_mastered_words}")
                cursor.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]
                print(f"Debug: Found {len(results)} words for difficulty '{target_difficulty}'")
                
                # If no words found for specific difficulty, try getting any available words from user vocabulary
                if not results and exclude_mastered_words:
                    print(f"Debug: No words found for difficulty '{target_difficulty}', trying any difficulty (excluding mastered)")
                    query = '''
                        SELECT * FROM vocabulary 
                        WHERE user_id = ? AND mastery_level < 3
                        ORDER BY RANDOM()
                        LIMIT ?
                    '''
                    params = (user_id, limit)
                    cursor.execute(query, params)
                    results = [dict(row) for row in cursor.fetchall()]
                    print(f"Debug: Found {len(results)} words when trying any difficulty (excluding mastered)")
                elif not results and not exclude_mastered_words:
                    print(f"Debug: No words found for difficulty '{target_difficulty}', trying any difficulty (including mastered)")
                    query = '''
                        SELECT * FROM vocabulary 
                        WHERE user_id = ?
                        ORDER BY RANDOM()
                        LIMIT ?
                    '''
                    params = (user_id, limit)
                    cursor.execute(query, params)
                    results = [dict(row) for row in cursor.fetchall()]
                    print(f"Debug: Found {len(results)} words when trying any difficulty (including mastered)")
                
                return results
                
        except SQLAlchemyError as e:
            print(f"Database error getting words for AI learning: {e}")
            return []
    
    def check_and_award_achievements(self, user_id: int) -> List[str]:
        """Check for new achievements and return list of earned ones"""
        achievements = []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get vocabulary stats
                cursor.execute('SELECT COUNT(*) as total FROM vocabulary WHERE user_id = ?', (user_id,))
                total_words = cursor.fetchone()['total']
                
                cursor.execute('SELECT COUNT(*) as mastered FROM vocabulary WHERE user_id = ? AND mastery_level = 3', (user_id,))
                mastered_words = cursor.fetchone()['mastered']
                
                cursor.execute('SELECT COUNT(*) as sessions FROM study_sessions WHERE user_id = ?', (user_id,))
                total_sessions = cursor.fetchone()['sessions']
                
                cursor.execute('''
                    SELECT COUNT(*) as perfect_sessions FROM study_sessions 
                    WHERE user_id = ? AND accuracy_percentage = 100 AND words_reviewed > 0
                ''', (user_id,))
                perfect_sessions = cursor.fetchone()['perfect_sessions']
                
                cursor.execute('SELECT COUNT(*) as ai_sessions FROM ai_learning_sessions WHERE user_id = ?', (user_id,))
                ai_sessions = cursor.fetchone()['ai_sessions']
                
                # Achievement logic - milestone based
                achievements_earned = []
                if total_words >= 50: achievements_earned.append("📚 Vocabulary Builder - 50 words learned!")
                if total_words >= 100: achievements_earned.append("📖 Word Collector - 100 words in library!")
                if total_words >= 250: achievements_earned.append("🏛️ Lexicon Master - 250 words strong!")
                
                if mastered_words >= 10: achievements_earned.append("🎯 First Mastery - 10 words mastered!")
                if mastered_words >= 25: achievements_earned.append("⭐ Word Expert - 25 words mastered!")
                if mastered_words >= 50: achievements_earned.append("🏆 Vocabulary Champion - 50 words mastered!")
                
                if total_sessions >= 5: achievements_earned.append("🔥 Study Starter - 5 study sessions!")
                if total_sessions >= 15: achievements_earned.append("📈 Consistent Learner - 15 sessions!")
                if total_sessions >= 30: achievements_earned.append("💪 Study Master - 30 sessions completed!")
                
                if perfect_sessions >= 1: achievements_earned.append("🎯 Perfect Score - 100% accuracy session!")
                if perfect_sessions >= 3: achievements_earned.append("🌟 Accuracy Expert - 3 perfect sessions!")
                
                if ai_sessions >= 3: achievements_earned.append("🤖 AI Learning Explorer - 3 AI sessions!")
                if ai_sessions >= 10: achievements_earned.append("🧠 AI Study Master - 10 AI sessions!")
                
                return achievements_earned
                
        except Exception as e:
            print(f"Error checking achievements: {e}")
            return []
    
    def get_recent_words(self, user_id: int, days: int = 7) -> List[Dict]:
        """Get words studied in last N days"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT *, 
                           EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_reviewed)) / 86400.0 as days_ago,
                           ROUND((times_correct * 1.0 / NULLIF(times_reviewed, 0)) * 100, 1) as accuracy_percent
                    FROM vocabulary 
                    WHERE user_id = ? 
                      AND last_reviewed IS NOT NULL 
                      AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_reviewed)) / 86400.0 <= ?
                    ORDER BY last_reviewed DESC
                    LIMIT 50
                ''', (user_id, days))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting recent words: {e}")
            return []
    
    def get_study_insights(self, user_id: int) -> Dict:
        """Get actionable study insights from existing data"""
        insights = {
            'struggling_words': [],
            'daily_progress': [],
            'needs_review_count': 0,
            'total_mastered': 0,
            'accuracy_trend': 'stable'
        }
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Words that need attention (low accuracy with multiple reviews)
                cursor.execute('''
                    SELECT word, definition, times_reviewed, times_correct, mastery_level,
                           ROUND((times_correct * 1.0 / NULLIF(times_reviewed, 0)) * 100, 1) as accuracy
                    FROM vocabulary 
                    WHERE user_id = ? 
                      AND times_reviewed >= 2 
                      AND (times_correct * 1.0 / times_reviewed) < 0.6
                    ORDER BY times_reviewed DESC, accuracy ASC
                    LIMIT 10
                ''', (user_id,))
                insights['struggling_words'] = [dict(row) for row in cursor.fetchall()]
                insights['needs_review_count'] = len(insights['struggling_words'])
                
                # Progress over time (study sessions)
                cursor.execute('''
                    SELECT DATE(start_time) as date, 
                           AVG(accuracy_percentage) as avg_accuracy,
                           SUM(words_reviewed) as total_reviewed
                    FROM study_sessions 
                    WHERE user_id = ? 
                      AND start_time >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                      AND is_completed = 1
                    GROUP BY DATE(start_time)
                    ORDER BY date DESC
                    LIMIT 14
                ''', (user_id,))
                insights['daily_progress'] = [dict(row) for row in cursor.fetchall()]
                
                # Total mastered words
                cursor.execute('SELECT COUNT(*) as mastered FROM vocabulary WHERE user_id = ? AND mastery_level = 3', (user_id,))
                insights['total_mastered'] = cursor.fetchone()['mastered']
                
                # Calculate accuracy trend
                if len(insights['daily_progress']) >= 3:
                    recent_avg = sum(day['avg_accuracy'] or 0 for day in insights['daily_progress'][:3]) / 3
                    older_avg = sum(day['avg_accuracy'] or 0 for day in insights['daily_progress'][-3:]) / 3
                    
                    if recent_avg > older_avg + 5:
                        insights['accuracy_trend'] = 'improving'
                    elif recent_avg < older_avg - 5:
                        insights['accuracy_trend'] = 'declining'
                
        except Exception as e:
            print(f"Error getting study insights: {e}")
        
        return insights
    
    def get_smart_words_for_ai_learning(self, user_id: int, difficulty: str = 'medium', limit: int = 20) -> List[Dict]:
        """Get words intelligently for AI learning - prioritize struggling words and new words"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Prioritize words user struggles with, then new words, then general review
                cursor.execute('''
                    SELECT *, 
                           (times_correct * 1.0 / NULLIF(times_reviewed, 0)) as accuracy,
                           COALESCE(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_reviewed)) / 86400.0, 999) as days_since_review,
                           CASE 
                               WHEN times_reviewed = 0 THEN 1  -- New words first
                               WHEN (times_correct * 1.0 / NULLIF(times_reviewed, 0)) < 0.6 AND times_reviewed >= 2 THEN 2  -- Struggling words  
                               WHEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_reviewed)) / 86400.0 > 7 THEN 3  -- Haven't seen in a week
                               WHEN mastery_level < 2 THEN 4  -- Still learning
                               ELSE 5
                           END as priority
                    FROM vocabulary 
                    WHERE user_id = ? 
                      AND mastery_level < 3  -- Exclude fully mastered words
                      AND (difficulty = ? OR difficulty = '')
                    ORDER BY priority ASC, RANDOM()
                    LIMIT ?
                ''', (user_id, difficulty, limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting smart words for AI learning: {e}")
            return []



if __name__ == '__main__':
    # Test the database
    db_manager = DatabaseManager()
    
    # Create a test user
    success, message, user_id = db_manager.create_user("test@example.com", "testuser", "Password123")
    print(f"User creation: {message} (ID: {user_id})")
    
    # Test authentication
    success, message, user = db_manager.authenticate_user("test@example.com", "Password123")
    print(f"Authentication: {message}")
    if user:
        print(f"Authenticated user: {user.to_dict()}")
