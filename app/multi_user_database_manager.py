#!/usr/bin/env python3
"""
Multi-User Database Manager for VCE Vocabulary Flashcard Application

This module handles all database operations using SQLite with multi-user support.
It manages users, vocabulary words, study sessions, and user preferences.

Author: Vocabulary Multi-User DB Manager
Date: August 2025
"""

import sqlite3
import os
import re
import hashlib
import secrets
from datetime import datetime, timedelta
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# bcrypt removed - using hashlib instead for password hashing


class User:
    """Class to represent a user."""
    
    def __init__(self, user_id: int, email: str, username: str, created_at: str, 
                 last_login: Optional[str] = None, is_active: bool = True):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.created_at = created_at
        self.last_login = last_login
        self.is_active = is_active
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for JSON serialization."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'username': self.username,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'is_active': self.is_active
        }


class VocabularyWord:
    """Class to represent a vocabulary word with its definition and example."""
    
    def __init__(self, word: str, word_type: str, definition: str, example: str, 
                 word_id: Optional[int] = None, user_id: Optional[int] = None,
                 difficulty: str = 'medium', times_reviewed: int = 0, 
                 times_correct: int = 0, mastery_level: int = 0,
                 created_at: Optional[str] = None, last_reviewed: Optional[str] = None):
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
            'accuracy': round((self.times_correct / self.times_reviewed * 100) if self.times_reviewed > 0 else 0, 1)
        }


class MultiUserDatabaseManager:
    """Main database manager for multi-user vocabulary operations."""
    
    def __init__(self, db_path: Optional[str] = None, data_dir: Optional[str] = None):
        """Initialize database manager."""
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_dir = data_dir or os.path.join(script_dir, 'data')
            self.db_path = os.path.join(self.data_dir, 'vocabulary_multiuser.db')
        else:
            self.db_path = db_path
            self.data_dir = os.path.dirname(db_path)
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.init_database()
        
        # Update schema if needed for existing databases
        self.update_schema_if_needed()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
        return conn
    
    def init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0,
                    email_verified BOOLEAN DEFAULT 0,
                    verification_token TEXT,
                    reset_token TEXT,
                    reset_token_expires TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_count INTEGER DEFAULT 0
                )
            ''')
            
            # Create user sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create vocabulary table (updated for multi-user with word sources and likes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word TEXT NOT NULL COLLATE NOCASE,
                    word_type TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    example TEXT NOT NULL,
                    difficulty TEXT DEFAULT 'medium',
                    times_reviewed INTEGER DEFAULT 0,
                    times_correct INTEGER DEFAULT 0,
                    last_reviewed TIMESTAMP,
                    mastery_level INTEGER DEFAULT 0,
                    is_favorite BOOLEAN DEFAULT 0,
                    is_hidden BOOLEAN DEFAULT 0,
                    tags TEXT DEFAULT '',
                    source TEXT DEFAULT 'manual',
                    base_word_id INTEGER DEFAULT NULL,
                    like_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (base_word_id) REFERENCES base_vocabulary (id) ON DELETE SET NULL,
                    UNIQUE(user_id, word)
                )
            ''')
            
            # Create base vocabulary table (system-wide word collection)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS base_vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    word_type TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    example TEXT NOT NULL,
                    difficulty TEXT DEFAULT 'medium',
                    category TEXT DEFAULT 'general',
                    total_likes INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    approved_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL,
                    FOREIGN KEY (approved_by) REFERENCES users (id) ON DELETE SET NULL
                )
            ''')
            
            # Create word likes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS word_likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (word_id) REFERENCES vocabulary (id) ON DELETE CASCADE,
                    UNIQUE(user_id, word_id)
                )
            ''')
            
            # Create password reset tokens table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create study sessions table (updated for multi-user)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_type TEXT DEFAULT 'review',
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    words_reviewed INTEGER DEFAULT 0,
                    words_correct INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    session_goal INTEGER DEFAULT 10,
                    accuracy_percentage REAL DEFAULT 0,
                    is_completed BOOLEAN DEFAULT 0,
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create study session words table (tracks which words were studied in each session)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS study_session_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    word_id INTEGER NOT NULL,
                    was_correct BOOLEAN NOT NULL,
                    response_time_ms INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES study_sessions (id) ON DELETE CASCADE,
                    FOREIGN KEY (word_id) REFERENCES vocabulary (id) ON DELETE CASCADE
                )
            ''')
            
            # Create user preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, preference_key)
                )
            ''')
            
            # Create vocabulary lists table (for organizing words)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vocabulary_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    is_public BOOLEAN DEFAULT 0,
                    is_system BOOLEAN DEFAULT 0,
                    color TEXT DEFAULT '#3498db',
                    word_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create vocabulary list words table (many-to-many relationship)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vocabulary_list_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    list_id INTEGER NOT NULL,
                    word_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (list_id) REFERENCES vocabulary_lists (id) ON DELETE CASCADE,
                    FOREIGN KEY (word_id) REFERENCES vocabulary (id) ON DELETE CASCADE,
                    UNIQUE(list_id, word_id)
                )
            ''')
            
            # Create user achievements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    achievement_type TEXT NOT NULL,
                    achievement_name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    points INTEGER DEFAULT 0,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Create daily stats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    words_studied INTEGER DEFAULT 0,
                    words_mastered INTEGER DEFAULT 0,
                    study_time_seconds INTEGER DEFAULT 0,
                    sessions_completed INTEGER DEFAULT 0,
                    accuracy_percentage REAL DEFAULT 0,
                    streak_days INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, date)
                )
            ''')
            
            # Create indexes for better performance (only for columns that should exist)
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vocab_user ON vocabulary(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vocab_word ON vocabulary(user_id, word)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vocab_difficulty ON vocabulary(user_id, difficulty)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_study_sessions_user ON study_sessions(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_preferences_user ON user_preferences(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date)')
            
            # Note: Additional indexes for new columns will be created in update_schema_if_needed()
            
            # Create triggers for automatic updates
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_vocabulary_timestamp 
                AFTER UPDATE ON vocabulary
                BEGIN
                    UPDATE vocabulary SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_user_timestamp 
                AFTER UPDATE ON users
                BEGIN
                    UPDATE users SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_list_word_count 
                AFTER INSERT ON vocabulary_list_words
                BEGIN
                    UPDATE vocabulary_lists 
                    SET word_count = (
                        SELECT COUNT(*) FROM vocabulary_list_words 
                        WHERE list_id = NEW.list_id
                    )
                    WHERE id = NEW.list_id;
                END
            ''')
            
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_list_word_count_delete 
                AFTER DELETE ON vocabulary_list_words
                BEGIN
                    UPDATE vocabulary_lists 
                    SET word_count = (
                        SELECT COUNT(*) FROM vocabulary_list_words 
                        WHERE list_id = OLD.list_id
                    )
                    WHERE id = OLD.list_id;
                END
            ''')
            
            conn.commit()
            print(f"✅ Multi-user database initialized: {self.db_path}")
    
    def update_schema_if_needed(self):
        """Update existing database schema to add new columns if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if new columns exist and add them if not
            try:
                # Check vocabulary table for new columns
                cursor.execute("PRAGMA table_info(vocabulary)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'base_word_id' not in columns:
                    cursor.execute('ALTER TABLE vocabulary ADD COLUMN base_word_id INTEGER REFERENCES base_vocabulary(id)')
                    print("✅ Added base_word_id column to vocabulary table")
                
                if 'like_count' not in columns:
                    cursor.execute('ALTER TABLE vocabulary ADD COLUMN like_count INTEGER DEFAULT 0')
                    print("✅ Added like_count column to vocabulary table")
                
                if 'is_hidden' not in columns:
                    cursor.execute('ALTER TABLE vocabulary ADD COLUMN is_hidden INTEGER DEFAULT 0')
                    print("✅ Added is_hidden column to vocabulary table")
                
                if 'source' not in columns:
                    cursor.execute('ALTER TABLE vocabulary ADD COLUMN source TEXT DEFAULT "user"')
                    print("✅ Added source column to vocabulary table")
                
                # Try to create new indexes that might not exist
                try:
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vocab_base_word ON vocabulary(base_word_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_base_vocab_word ON base_vocabulary(word)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_word_likes_user ON word_likes(user_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_word_likes_word ON word_likes(word_id)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens(token)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_reset_tokens_user ON password_reset_tokens(user_id)')
                except sqlite3.OperationalError as e:
                    # Ignore errors for tables that don't exist yet
                    if "no such table" not in str(e).lower():
                        print(f"Warning: Could not create some indexes: {e}")
                
                conn.commit()
                print("✅ Schema update completed")
                
            except Exception as e:
                print(f"⚠️  Schema update warning: {e}")

    # User Authentication Methods
    def create_user(self, email: str, username: str, password: str) -> Tuple[bool, str, Optional[int]]:
        """Create a new user account."""
        try:
            # Validate input
            if not email or not username or not password:
                return False, "Email, username, and password are required", None
            
            if len(password) < 6:
                return False, "Password must be at least 6 characters long", None
            
            # Generate salt and hash password
            salt = secrets.token_hex(32)
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                               salt.encode('utf-8'), 100000).hex()
            
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
                
        except sqlite3.IntegrityError as e:
            if 'email' in str(e):
                return False, "Email already exists", None
            elif 'username' in str(e):
                return False, "Username already exists", None
            else:
                return False, "User creation failed", None
        except Exception as e:
            return False, f"Error creating user: {str(e)}", None
    
    def authenticate_user(self, email_or_username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """Authenticate user with email/username and password."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find user by email or username
                cursor.execute('''
                    SELECT id, email, username, password_hash, salt, is_active, created_at, last_login
                    FROM users 
                    WHERE (email = ? OR username = ?) AND is_active = 1
                ''', (email_or_username.lower().strip(), email_or_username.strip()))
                
                user_row = cursor.fetchone()
                
                if not user_row:
                    return False, "Invalid credentials", None
                
                # Verify password
                stored_hash = user_row['password_hash']
                salt = user_row['salt']
                
                password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), 
                                                   salt.encode('utf-8'), 100000).hex()
                
                if password_hash != stored_hash:
                    return False, "Invalid credentials", None
                
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
                    is_active=bool(user_row['is_active'])
                )
                
                return True, "Authentication successful", user
                
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
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
                cursor.execute('''
                    INSERT OR REPLACE INTO user_preferences (user_id, preference_key, preference_value)
                    VALUES (?, ?, ?)
                ''', (user_id, key, value))
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
                except sqlite3.IntegrityError:
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
                except sqlite3.IntegrityError:
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
                except sqlite3.IntegrityError:
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
                ORDER BY word COLLATE NOCASE
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
                    last_reviewed=row['last_reviewed']
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
                
        except sqlite3.IntegrityError:
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
                ORDER BY total_likes DESC, word COLLATE NOCASE
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
            
            if len(new_password) < 6:
                return False, "Password must be at least 6 characters long"
            
            # Generate new password hash
            salt = secrets.token_hex(32)
            password_hash = hashlib.pbkdf2_hmac('sha256', new_password.encode('utf-8'), 
                                               salt.encode('utf-8'), 100000).hex()
            
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
        except sqlite3.IntegrityError:
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
                
                # Calculate new mastery level based on accuracy
                accuracy = (new_times_correct / new_times_reviewed) * 100 if new_times_reviewed > 0 else 0
                
                # Simple mastery level calculation:
                # 0-30%: mastery_level = 0 (needs practice)
                # 31-60%: mastery_level = 1 (learning)
                # 61-80%: mastery_level = 2 (good)
                # 81-100%: mastery_level = 3 (mastered)
                if accuracy <= 30:
                    mastery_level = 0
                elif accuracy <= 60:
                    mastery_level = 1
                elif accuracy <= 80:
                    mastery_level = 2
                else:
                    mastery_level = 3
                
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
                ORDER BY word COLLATE NOCASE
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
                
                # Copy base vocabulary to user
                copied_count = self.copy_base_vocabulary_to_user(user_id)
                
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


# Migration function to move existing data to multi-user schema
def migrate_single_user_to_multiuser(old_db_path: str, new_db_path: str, default_user_email: str = "admin@vocabulary.app") -> bool:
    """Migrate existing single-user database to multi-user schema."""
    try:
        if not os.path.exists(old_db_path):
            print(f"❌ Old database not found: {old_db_path}")
            return False
        
        # Create new multi-user database
        new_db = MultiUserDatabaseManager(new_db_path)
        
        # Create default admin user
        admin_password = os.getenv('ADMIN_DEFAULT_PASSWORD', 'admin123')  # Fallback to admin123 if not set
        success, message, user_id = new_db.create_user(
            email=default_user_email,
            username="admin",
            password=admin_password
        )
        
        if not success:
            print(f"❌ Failed to create default user: {message}")
            return False
        
        print(f"✅ Created default user: {default_user_email} (Password: {admin_password})")
        
        # Connect to old database and migrate data
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        
        with old_conn:
            # Migrate vocabulary words
            old_cursor = old_conn.cursor()
            old_cursor.execute('SELECT * FROM tbl_vocab')
            old_words = old_cursor.fetchall()
            
            with new_db.get_connection() as new_conn:
                new_cursor = new_conn.cursor()
                
                migrated_count = 0
                for word_row in old_words:
                    new_cursor.execute('''
                        INSERT INTO vocabulary 
                        (user_id, word, word_type, definition, example, difficulty, 
                         times_reviewed, times_correct, last_reviewed, mastery_level, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        word_row['word'],
                        word_row['word_type'],
                        word_row['definition'],
                        word_row['example'],
                        word_row['difficulty'] if 'difficulty' in word_row.keys() else 'medium',
                        word_row['times_reviewed'] if 'times_reviewed' in word_row.keys() else 0,
                        word_row['times_correct'] if 'times_correct' in word_row.keys() else 0,
                        word_row['last_reviewed'] if 'last_reviewed' in word_row.keys() else None,
                        word_row['mastery_level'] if 'mastery_level' in word_row.keys() else 0,
                        word_row['created_at'] if 'created_at' in word_row.keys() else None
                    ))
                    migrated_count += 1
                
                new_conn.commit()
                print(f"✅ Migrated {migrated_count} vocabulary words")
                
                # Migrate study sessions if they exist
                try:
                    old_cursor.execute('SELECT * FROM tbl_study_sessions')
                    old_sessions = old_cursor.fetchall()
                    
                    session_count = 0
                    for session_row in old_sessions:
                        new_cursor.execute('''
                            INSERT INTO study_sessions 
                            (user_id, session_type, start_time, end_time, words_reviewed, 
                             words_correct, duration_seconds)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            user_id,
                            session_row['session_type'] if 'session_type' in session_row.keys() else 'review',
                            session_row['start_time'],
                            session_row['end_time'] if 'end_time' in session_row.keys() else None,
                            session_row['words_reviewed'] if 'words_reviewed' in session_row.keys() else 0,
                            session_row['words_correct'] if 'words_correct' in session_row.keys() else 0,
                            session_row['duration_seconds'] if 'duration_seconds' in session_row.keys() else 0
                        ))
                        session_count += 1
                    
                    new_conn.commit()
                    print(f"✅ Migrated {session_count} study sessions")
                    
                except sqlite3.OperationalError:
                    print("ℹ️  No study sessions table found in old database")
        
        old_conn.close()
        
        # Create backup of old database
        backup_path = f"{old_db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(old_db_path, backup_path)
        print(f"💾 Created backup of old database: {backup_path}")
        
        print("✅ Migration completed successfully!")
        print(f"🔑 Default login credentials:")
        print(f"   Email: {default_user_email}")
        print(f"   Password: admin123")
        print(f"   ⚠️  Please change the password immediately after first login!")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False


def initialize_multiuser_from_text_file(text_file: str, user_id: int, db_manager: MultiUserDatabaseManager) -> int:
    """Initialize multi-user database from text file for a specific user."""
    return db_manager.load_vocabulary_from_text_file(text_file, user_id)


if __name__ == '__main__':
    # Test the multi-user database
    db_manager = MultiUserDatabaseManager('data/vocabulary_multiuser_test.db')
    
    # Create a test user
    success, message, user_id = db_manager.create_user("test@example.com", "testuser", "password123")
    print(f"User creation: {message} (ID: {user_id})")
    
    # Test authentication
    success, message, user = db_manager.authenticate_user("test@example.com", "password123")
    print(f"Authentication: {message}")
    if user:
        print(f"Authenticated user: {user.to_dict()}")
