#!/usr/bin/env python3
"""
Database Migration Script for Enhanced Features

This script adds new columns to the existing vocabulary database
to support the enhanced study features.
"""

import sqlite3
import os

def migrate_database():
    """Migrate the existing database to support new features."""
    db_path = 'data/vocabulary.db'
    
    if not os.path.exists(db_path):
        print("❌ Database not found. Please run the main application first.")
        return False
    
    print("🚀 Starting database migration...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(tbl_vocab)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Existing columns: {existing_columns}")
        
        # Add new columns if they don't exist
        new_columns = [
            ('difficulty', 'TEXT DEFAULT "medium"'),
            ('times_reviewed', 'INTEGER DEFAULT 0'),
            ('times_correct', 'INTEGER DEFAULT 0'),
            ('last_reviewed', 'TIMESTAMP'),
            ('mastery_level', 'INTEGER DEFAULT 0')
        ]
        
        for column_name, column_def in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE tbl_vocab ADD COLUMN {column_name} {column_def}')
                    print(f"✅ Added column: {column_name}")
                except sqlite3.Error as e:
                    print(f"⚠️  Column {column_name} might already exist: {e}")
        
        # Create new tables
        try:
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
            print("✅ Created study sessions table")
        except sqlite3.Error as e:
            print(f"⚠️  Study sessions table might already exist: {e}")
        
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tbl_user_settings (
                    id INTEGER PRIMARY KEY,
                    setting_name TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("✅ Created user settings table")
        except sqlite3.Error as e:
            print(f"⚠️  User settings table might already exist: {e}")
        
        # Insert default settings
        default_settings = [
            ('daily_goal', '20'),
            ('theme', 'light'),
            ('show_stats', 'true')
        ]
        
        for setting_name, setting_value in default_settings:
            cursor.execute('''
                INSERT OR IGNORE INTO tbl_user_settings (setting_name, setting_value)
                VALUES (?, ?)
            ''', (setting_name, setting_value))
        
        conn.commit()
        print("✅ Default settings added")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM tbl_vocab")
        word_count = cursor.fetchone()[0]
        
        cursor.execute("PRAGMA table_info(tbl_vocab)")
        final_columns = [column[1] for column in cursor.fetchall()]
        
        print(f"\n📊 Migration Summary:")
        print(f"   Words in database: {word_count}")
        print(f"   Final columns: {final_columns}")
        
        conn.close()
        
        print("\n🎉 Database migration completed successfully!")
        print("🔧 You can now use all the enhanced features:")
        print("   • Study session tracking")
        print("   • Difficulty ratings")
        print("   • Progress monitoring")
        print("   • Dark mode preferences")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("    VCE VOCABULARY DATABASE MIGRATION")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n✅ Migration completed! You can now run the web application.")
        print("💡 Run: python web_flashcards.py")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
    
    print("=" * 60)
