#!/usr/bin/env python3
"""
Database Manager for VCE Vocabulary Flashcard Application

This module handles all database operations using SQLite.
It manages the vocabulary words table and provides methods for CRUD operations.

Author: Vocabulary DB Manager
Date: 2025
"""

import sqlite3
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import shutil


class VocabularyWord:
    """Class to represent a vocabulary word with its definition and example."""
    
    def __init__(self, word: str, word_type: str, definition: str, example: str, word_id: Optional[int] = None):
        self.word = word.strip()
        self.word_type = word_type.strip()
        self.definition = definition.strip()
        self.example = example.strip()
        self.word_id = word_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert word to dictionary for JSON serialization."""
        return {
            'id': self.word_id,
            'word': self.word,
            'word_type': self.word_type,
            'definition': self.definition,
            'example': self.example
        }
    
    def __repr__(self):
        return f"VocabularyWord(id={self.word_id}, word='{self.word}', type='{self.word_type}')"


class DatabaseManager:
    """Main database manager for vocabulary operations."""
    
    def __init__(self, db_path: Optional[str] = None, data_dir: Optional[str] = None):
        """Initialize database manager."""
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_dir = data_dir or os.path.join(script_dir, 'data')
            self.db_path = os.path.join(self.data_dir, 'vocabulary.db')
        else:
            self.db_path = db_path
            self.data_dir = os.path.dirname(db_path)
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
        return conn
    
    def init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create vocabulary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_vocab (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    word_type TEXT NOT NULL,
                    definition TEXT NOT NULL,
                    example TEXT NOT NULL,
                    difficulty TEXT DEFAULT 'medium',
                    times_reviewed INTEGER DEFAULT 0,
                    times_correct INTEGER DEFAULT 0,
                    last_reviewed TIMESTAMP,
                    mastery_level INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create study sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_study_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    words_reviewed INTEGER DEFAULT 0,
                    words_correct INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    session_type TEXT DEFAULT 'review'
                )
            ''')
            
            # Create user settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_user_settings (
                    id INTEGER PRIMARY KEY,
                    setting_name TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for faster searches
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_vocab_word 
                ON tbl_vocab(word COLLATE NOCASE)
            ''')
            
            # Create trigger to update updated_at timestamp
            cursor.execute('''
                CREATE TRIGGER IF NOT EXISTS update_vocab_timestamp 
                AFTER UPDATE ON tbl_vocab
                BEGIN
                    UPDATE tbl_vocab SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            ''')
            
            conn.commit()
            print(f"✅ Database initialized: {self.db_path}")
    
    def load_from_text_file(self, text_file_path: str) -> int:
        """Load vocabulary words from text file into database."""
        if not os.path.exists(text_file_path):
            print(f"❌ Text file not found: {text_file_path}")
            return 0
        
        print(f"📖 Loading vocabulary from: {text_file_path}")
        
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
                        INSERT INTO tbl_vocab (word, word_type, definition, example)
                        VALUES (?, ?, ?, ?)
                    ''', (word.strip(), word_type.strip(), definition.strip(), example.strip()))
                    loaded_count += 1
                except sqlite3.IntegrityError:
                    # Word already exists (duplicate)
                    skipped_count += 1
                    print(f"⚠️  Skipping duplicate: {word.strip()}")
            
            conn.commit()
        
        print(f"✅ Loaded {loaded_count} words into database")
        if skipped_count > 0:
            print(f"⚠️  Skipped {skipped_count} duplicate entries")
        
        return loaded_count
    
    def export_to_text_file(self, output_file_path: str) -> bool:
        """Export vocabulary words from database to text file."""
        try:
            words = self.get_all_words()
            
            # Create backup if file exists
            if os.path.exists(output_file_path):
                backup_file = f"{output_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(output_file_path, backup_file)
                print(f"💾 Created backup: {backup_file}")
            
            with open(output_file_path, 'w', encoding='utf-8') as file:
                file.write("# VCE Vocabulary Words\n")
                file.write("# Format: Word (Type) - Definition - Example.\n")
                file.write(f"# Exported from database on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                for word_dict in words:
                    file.write(f"{word_dict['word']} ({word_dict['word_type']}) - {word_dict['definition']} - {word_dict['example']}\n")
            
            print(f"📤 Exported {len(words)} words to: {output_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error exporting to file: {str(e)}")
            return False
    
    def add_word(self, word: str, word_type: str, definition: str, example: str) -> Tuple[bool, str]:
        """Add a new vocabulary word to database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tbl_vocab (word, word_type, definition, example)
                    VALUES (?, ?, ?, ?)
                ''', (word.strip(), word_type.strip(), definition.strip(), example.strip()))
                conn.commit()
                
                return True, "Word added successfully!"
                
        except sqlite3.IntegrityError:
            return False, f"Word '{word}' already exists in your vocabulary."
        except Exception as e:
            print(f"Error adding word: {e}")
            return False, f"Database error: {str(e)}"
    
    def remove_word(self, word_id: int) -> Tuple[bool, str]:
        """Remove a vocabulary word from database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM tbl_vocab WHERE id = ?', (word_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Word removed successfully!"
                else:
                    return False, "Word not found."
                    
        except Exception as e:
            print(f"Error removing word: {e}")
            return False, f"Database error: {str(e)}"
    
    def update_word(self, word_id: int, word: str, word_type: str, definition: str, example: str) -> Tuple[bool, str]:
        """Update an existing vocabulary word."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tbl_vocab 
                    SET word = ?, word_type = ?, definition = ?, example = ?
                    WHERE id = ?
                ''', (word.strip(), word_type.strip(), definition.strip(), example.strip(), word_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Word updated successfully!"
                else:
                    return False, "Word not found."
                    
        except sqlite3.IntegrityError:
            return False, f"Word '{word}' already exists in your vocabulary."
        except Exception as e:
            print(f"Error updating word: {e}")
            return False, f"Database error: {str(e)}"
    
    def get_word_by_id(self, word_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific word by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tbl_vocab WHERE id = ?', (word_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            print(f"Error getting word: {e}")
            return None
    
    def get_all_words(self) -> List[Dict[str, Any]]:
        """Get all vocabulary words from database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, word, word_type, definition, example, created_at, updated_at
                    FROM tbl_vocab 
                    ORDER BY word COLLATE NOCASE
                ''')
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"Error getting words: {e}")
            return []
    
    def search_words(self, query: str) -> List[Dict[str, Any]]:
        """Search words by query string."""
        if not query.strip():
            return self.get_all_words()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                search_term = f"%{query.lower()}%"
                
                cursor.execute('''
                    SELECT id, word, word_type, definition, example, created_at, updated_at
                    FROM tbl_vocab 
                    WHERE LOWER(word) LIKE ? 
                       OR LOWER(word_type) LIKE ? 
                       OR LOWER(definition) LIKE ? 
                       OR LOWER(example) LIKE ?
                    ORDER BY word COLLATE NOCASE
                ''', (search_term, search_term, search_term, search_term))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"Error searching words: {e}")
            return []
    
    def get_word_count(self) -> int:
        """Get total number of words in database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM tbl_vocab')
                return cursor.fetchone()[0]
                
        except Exception as e:
            print(f"Error getting word count: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total count
                cursor.execute('SELECT COUNT(*) FROM tbl_vocab')
                total_words = cursor.fetchone()[0]
                
                # Get word types distribution
                cursor.execute('''
                    SELECT word_type, COUNT(*) as count 
                    FROM tbl_vocab 
                    GROUP BY word_type 
                    ORDER BY count DESC
                ''')
                word_types = [dict(row) for row in cursor.fetchall()]
                
                # Get recent additions (last 7 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM tbl_vocab 
                    WHERE created_at >= date('now', '-7 days')
                ''')
                recent_additions = cursor.fetchone()[0]
                
                return {
                    'total_words': total_words,
                    'word_types': word_types,
                    'recent_additions': recent_additions,
                    'database_path': self.db_path
                }
                
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {
                'total_words': 0,
                'word_types': [],
                'recent_additions': 0,
                'database_path': self.db_path
            }
    
    def update_word_difficulty(self, word_id: int, difficulty: str) -> Tuple[bool, str]:
        """Update the difficulty level of a word."""
        try:
            if difficulty not in ['easy', 'medium', 'hard']:
                return False, "Invalid difficulty level. Must be 'easy', 'medium', or 'hard'."
                
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tbl_vocab 
                    SET difficulty = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (difficulty, word_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, f"Word difficulty updated to {difficulty}!"
                else:
                    return False, "Word not found."
                    
        except Exception as e:
            print(f"Error updating word difficulty: {e}")
            return False, f"Database error: {str(e)}"
    
    def record_word_review(self, word_id: int, correct: bool) -> Tuple[bool, str]:
        """Record a word review (for study tracking)."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update word review stats
                if correct:
                    cursor.execute('''
                        UPDATE tbl_vocab 
                        SET times_reviewed = times_reviewed + 1,
                            times_correct = times_correct + 1,
                            last_reviewed = CURRENT_TIMESTAMP,
                            mastery_level = CASE 
                                WHEN (times_correct + 1) >= 3 THEN 2
                                WHEN (times_correct + 1) >= 1 THEN 1
                                ELSE 0
                            END,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (word_id,))
                else:
                    cursor.execute('''
                        UPDATE tbl_vocab 
                        SET times_reviewed = times_reviewed + 1,
                            last_reviewed = CURRENT_TIMESTAMP,
                            mastery_level = 0,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (word_id,))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    return True, "Review recorded successfully!"
                else:
                    return False, "Word not found."
                    
        except Exception as e:
            print(f"Error recording word review: {e}")
            return False, f"Database error: {str(e)}"
    
    def start_study_session(self, session_type: str = 'review') -> Optional[int]:
        """Start a new study session and return session ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tbl_study_sessions (session_type)
                    VALUES (?)
                ''', (session_type,))
                
                session_id = cursor.lastrowid
                conn.commit()
                return session_id
                
        except Exception as e:
            print(f"Error starting study session: {e}")
            return None
    
    def end_study_session(self, session_id: int, words_reviewed: int, words_correct: int, duration_seconds: int) -> bool:
        """End a study session with statistics."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE tbl_study_sessions 
                    SET end_time = CURRENT_TIMESTAMP,
                        words_reviewed = ?,
                        words_correct = ?,
                        duration_seconds = ?
                    WHERE id = ?
                ''', (words_reviewed, words_correct, duration_seconds, session_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error ending study session: {e}")
            return False
    
    def get_words_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        """Get words filtered by difficulty level."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, word, word_type, definition, example, difficulty, 
                           times_reviewed, times_correct, mastery_level, last_reviewed,
                           created_at
                    FROM tbl_vocab 
                    WHERE difficulty = ?
                    ORDER BY word COLLATE NOCASE
                ''', (difficulty,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            print(f"Error getting words by difficulty: {e}")
            return []
    
    def get_study_stats(self) -> Dict[str, Any]:
        """Get comprehensive study statistics."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Overall stats
                cursor.execute('SELECT COUNT(*) FROM tbl_vocab')
                total_words = cursor.fetchone()[0]
                
                # Difficulty breakdown
                cursor.execute('''
                    SELECT difficulty, COUNT(*) as count 
                    FROM tbl_vocab 
                    GROUP BY difficulty
                ''')
                difficulty_stats = {row['difficulty']: row['count'] for row in cursor.fetchall()}
                
                # Mastery breakdown
                cursor.execute('''
                    SELECT 
                        CASE 
                            WHEN mastery_level = 0 THEN 'new'
                            WHEN mastery_level = 1 THEN 'learning'
                            WHEN mastery_level = 2 THEN 'mastered'
                        END as mastery,
                        COUNT(*) as count
                    FROM tbl_vocab 
                    GROUP BY mastery_level
                ''')
                mastery_stats = {row['mastery']: row['count'] for row in cursor.fetchall()}
                
                # Recent session stats
                cursor.execute('''
                    SELECT 
                        COUNT(*) as sessions_today,
                        COALESCE(SUM(words_reviewed), 0) as words_today,
                        COALESCE(SUM(duration_seconds), 0) as time_today
                    FROM tbl_study_sessions 
                    WHERE date(start_time) = date('now')
                ''')
                today_stats = dict(cursor.fetchone())
                
                return {
                    'total_words': total_words,
                    'difficulty_stats': difficulty_stats,
                    'mastery_stats': mastery_stats,
                    'today_stats': today_stats
                }
                
        except Exception as e:
            print(f"Error getting study stats: {e}")
            return {
                'total_words': 0,
                'difficulty_stats': {},
                'mastery_stats': {},
                'today_stats': {}
            }


def initialize_from_text_file(text_file_path: str, db_path: Optional[str] = None) -> DatabaseManager:
    """Initialize database and load data from text file."""
    print("🚀 Initializing vocabulary database...")
    
    db_manager = DatabaseManager(db_path)
    
    if os.path.exists(text_file_path):
        db_manager.load_from_text_file(text_file_path)
    else:
        print(f"⚠️  Text file not found: {text_file_path}")
        print("📝 Starting with empty database")
    
    return db_manager


if __name__ == "__main__":
    # Test the database manager
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    text_file = os.path.join(data_dir, 'new-words.txt')
    
    print("=" * 60)
    print("    VOCABULARY DATABASE MANAGER TEST")
    print("=" * 60)
    
    # Initialize database
    db_manager = initialize_from_text_file(text_file)
    
    # Show stats
    stats = db_manager.get_database_stats()
    print(f"\n📊 Database Statistics:")
    print(f"   Total words: {stats['total_words']}")
    print(f"   Recent additions: {stats['recent_additions']}")
    print(f"   Database location: {stats['database_path']}")
    
    if stats['word_types']:
        print(f"\n📝 Word Types:")
        for word_type in stats['word_types'][:5]:  # Show top 5
            print(f"   {word_type['word_type']}: {word_type['count']} words")
    
    print("\n" + "=" * 60)
    print("🎉 Database initialization completed!")
    print("=" * 60)
