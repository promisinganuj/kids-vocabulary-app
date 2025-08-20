#!/usr/bin/env python3
"""
Backup Words as JSON Script

This script dumps all vocabulary words from the database to a JSON file
in the seed-data directory with a timestamp.

Usage:
    python backup-words-as-json.py [options]

Options:
    --all-users     Export all user vocabulary words (default: only base vocabulary)
    --user-id ID    Export words for specific user ID
    --unique        Export only unique words (removes duplicates based on word text)
    --output PATH   Custom output file path (default: seed-data/words-list-YYYYMMDDHHMMSS.json)
    --help          Show this help message

Author: Vocabulary Backup Tool
Date: August 2025
"""

import sqlite3
import json
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional


def get_database_path() -> str:
    """Get the path to the database file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    db_path = os.path.join(project_root, 'app', 'data', 'vocabulary_multiuser.db')
    
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at: {db_path}")
    
    return db_path


def get_output_path(custom_path: Optional[str] = None) -> str:
    """Get the output file path with timestamp."""
    if custom_path:
        return custom_path
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    seed_data_dir = os.path.join(project_root, 'seed-data')
    
    # Create seed-data directory if it doesn't exist
    os.makedirs(seed_data_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename = f'words-list-{timestamp}.json'
    
    return os.path.join(seed_data_dir, filename)


def export_base_vocabulary(db_path: str) -> List[Dict[str, Any]]:
    """Export all words from base_vocabulary table."""
    words = []
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT word, word_type, definition, example, difficulty, category
            FROM base_vocabulary 
            WHERE is_active = 1
            ORDER BY word COLLATE NOCASE
        ''')
        
        for row in cursor.fetchall():
            word_data = {
                'word': row['word'],
                'type': row['word_type'],
                'definition': row['definition'],
                'example': row['example']
            }
            
            # Add optional fields if they exist and are not default
            if row['difficulty'] and row['difficulty'] != 'medium':
                word_data['difficulty'] = row['difficulty']
            if row['category'] and row['category'] != 'general':
                word_data['category'] = row['category']
                
            words.append(word_data)
    
    return words


def export_user_vocabulary(db_path: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Export vocabulary words from user tables."""
    words = []
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            # Export words for specific user
            cursor.execute('''
                SELECT word, word_type, definition, example, difficulty, 
                       user_id, times_reviewed, times_correct, mastery_level
                FROM vocabulary 
                WHERE user_id = ? AND is_hidden = 0
                ORDER BY word COLLATE NOCASE
            ''', (user_id,))
        else:
            # Export all user words
            cursor.execute('''
                SELECT word, word_type, definition, example, difficulty,
                       user_id, times_reviewed, times_correct, mastery_level
                FROM vocabulary 
                WHERE is_hidden = 0
                ORDER BY word COLLATE NOCASE
            ''')
        
        for row in cursor.fetchall():
            word_data = {
                'word': row['word'],
                'type': row['word_type'],
                'definition': row['definition'],
                'example': row['example']
            }
            
            # Add optional fields if they exist and are not default
            if row['difficulty'] and row['difficulty'] != 'medium':
                word_data['difficulty'] = row['difficulty']
            if user_id is None:  # Include user info when exporting all users
                word_data['user_id'] = row['user_id']
            if row['times_reviewed'] > 0:
                word_data['times_reviewed'] = row['times_reviewed']
                word_data['times_correct'] = row['times_correct']
                word_data['mastery_level'] = row['mastery_level']
                word_data['accuracy'] = round((row['times_correct'] / row['times_reviewed'] * 100), 1)
                
            words.append(word_data)
    
    return words


def export_unique_words(db_path: str, include_user_words: bool = True) -> List[Dict[str, Any]]:
    """Export unique words from both base and user vocabulary tables."""
    unique_words = {}  # Use dict to track unique words by word text (case-insensitive)
    
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # First, get base vocabulary words
        cursor.execute('''
            SELECT word, word_type, definition, example, difficulty, category
            FROM base_vocabulary 
            WHERE is_active = 1
            ORDER BY word COLLATE NOCASE
        ''')
        
        for row in cursor.fetchall():
            word_key = row['word'].lower()
            if word_key not in unique_words:
                word_data = {
                    'word': row['word'],
                    'type': row['word_type'],
                    'definition': row['definition'],
                    'example': row['example'],
                    'source': 'base'
                }
                
                # Add optional fields if they exist and are not default
                if row['difficulty'] and row['difficulty'] != 'medium':
                    word_data['difficulty'] = row['difficulty']
                if row['category'] and row['category'] != 'general':
                    word_data['category'] = row['category']
                    
                unique_words[word_key] = word_data
        
        # Then, get user vocabulary words (if requested)
        if include_user_words:
            cursor.execute('''
                SELECT word, word_type, definition, example, difficulty,
                       user_id, times_reviewed, times_correct, mastery_level
                FROM vocabulary 
                WHERE is_hidden = 0
                ORDER BY word COLLATE NOCASE
            ''')
            
            for row in cursor.fetchall():
                word_key = row['word'].lower()
                if word_key not in unique_words:
                    word_data = {
                        'word': row['word'],
                        'type': row['word_type'],
                        'definition': row['definition'],
                        'example': row['example'],
                        'source': 'user',
                        'user_id': row['user_id']
                    }
                    
                    # Add optional fields if they exist and are not default
                    if row['difficulty'] and row['difficulty'] != 'medium':
                        word_data['difficulty'] = row['difficulty']
                    if row['times_reviewed'] > 0:
                        word_data['times_reviewed'] = row['times_reviewed']
                        word_data['times_correct'] = row['times_correct']
                        word_data['mastery_level'] = row['mastery_level']
                        word_data['accuracy'] = round((row['times_correct'] / row['times_reviewed'] * 100), 1)
                        
                    unique_words[word_key] = word_data
                else:
                    # Word already exists, but add user info if this is from user vocabulary
                    if 'source' in unique_words[word_key] and unique_words[word_key]['source'] == 'base':
                        unique_words[word_key]['also_in_user_vocab'] = True
    
    # Convert dict values to list and sort by word
    words_list = list(unique_words.values())
    words_list.sort(key=lambda x: x['word'].lower())
    
    return words_list


def get_database_stats(db_path: str) -> Dict[str, int]:
    """Get statistics about the database."""
    stats = {}
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Count base vocabulary words
        cursor.execute('SELECT COUNT(*) as count FROM base_vocabulary WHERE is_active = 1')
        stats['base_words'] = cursor.fetchone()[0]
        
        # Count user vocabulary words
        cursor.execute('SELECT COUNT(*) as count FROM vocabulary WHERE is_hidden = 0')
        stats['user_words'] = cursor.fetchone()[0]
        
        # Count unique users with words
        cursor.execute('SELECT COUNT(DISTINCT user_id) as count FROM vocabulary WHERE is_hidden = 0')
        stats['users_with_words'] = cursor.fetchone()[0]
        
        # Count unique words across all tables
        cursor.execute('''
            SELECT COUNT(DISTINCT LOWER(word)) as count 
            FROM (
                SELECT word FROM base_vocabulary WHERE is_active = 1
                UNION ALL
                SELECT word FROM vocabulary WHERE is_hidden = 0
            )
        ''')
        stats['unique_words_total'] = cursor.fetchone()[0]
    
    return stats


def main():
    """Main function to handle command line arguments and export words."""
    parser = argparse.ArgumentParser(
        description='Export vocabulary words from database to JSON file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python backup-words-as-json.py                    # Export base vocabulary
    python backup-words-as-json.py --all-users        # Export all user words
    python backup-words-as-json.py --user-id 1        # Export words for user ID 1
    python backup-words-as-json.py --unique           # Export unique words only
    python backup-words-as-json.py --output custom.json  # Custom output file
        """
    )
    
    parser.add_argument('--all-users', action='store_true',
                        help='Export all user vocabulary words instead of base vocabulary')
    parser.add_argument('--user-id', type=int,
                        help='Export words for specific user ID')
    parser.add_argument('--unique', action='store_true',
                        help='Export only unique words (removes duplicates based on word text)')
    parser.add_argument('--output', type=str,
                        help='Custom output file path')
    parser.add_argument('--stats-only', action='store_true',
                        help='Show database statistics only, do not export')
    
    args = parser.parse_args()
    
    try:
        # Get database path
        db_path = get_database_path()
        print(f"✓ Found database: {db_path}")
        
        # Show statistics
        stats = get_database_stats(db_path)
        print(f"\nDatabase Statistics:")
        print(f"  Base vocabulary words: {stats['base_words']}")
        print(f"  User vocabulary words: {stats['user_words']}")
        print(f"  Users with words: {stats['users_with_words']}")
        print(f"  Unique words (total): {stats['unique_words_total']}")
        
        if args.stats_only:
            return
        
        # Determine what to export
        if args.unique:
            print(f"\n📤 Exporting unique words only...")
            words = export_unique_words(db_path, include_user_words=True)
            export_type = "unique"
        elif args.user_id:
            print(f"\n📤 Exporting words for user ID {args.user_id}...")
            words = export_user_vocabulary(db_path, args.user_id)
            export_type = f"user-{args.user_id}"
        elif args.all_users:
            print(f"\n📤 Exporting all user vocabulary words...")
            words = export_user_vocabulary(db_path)
            export_type = "all-users"
        else:
            print(f"\n📤 Exporting base vocabulary words...")
            words = export_base_vocabulary(db_path)
            export_type = "base"
        
        if not words:
            print("⚠️  No words found to export.")
            return
        
        # Get output path
        output_path = get_output_path(args.output)
        
        # Add export metadata
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'type': export_type,
                'total_words': len(words),
                'database_path': os.path.basename(db_path)
            },
            'words': words
        }
        
        # Write to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully exported {len(words)} words to: {output_path}")
        print(f"   Export type: {export_type}")
        print(f"   File size: {os.path.getsize(output_path):,} bytes")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()