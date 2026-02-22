#!/usr/bin/env python3
"""
Script to load vocabulary words from seed-data/words-list.json into the base_vocabulary table.

This script reads the JSON file and inserts words into the base_vocabulary table,
avoiding duplicates and handling the JSON structure properly.

Usage:
    python load_json_to_base_vocabulary.py
"""

import json
import sys
import os
from typing import Dict, List, Any, Optional

# Add the app directory to the Python path to import the DatabaseManager
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.database_manager import DatabaseManager
except ImportError as e:
    print(f"❌ Error importing DatabaseManager: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)


def load_json_to_base_vocabulary(json_file_path: str = None, created_by_user_id: Optional[int] = None) -> bool:
    """
    Load vocabulary words from JSON file into base_vocabulary table.
    
    Args:
        json_file_path: Path to the JSON file (default: seed-data/words-list.json)
        created_by_user_id: User ID to set as creator (optional)
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Set default path if not provided
    if json_file_path is None:
        json_file_path = os.path.join('seed-data', 'words-list.json')
    
    # Check if file exists
    if not os.path.exists(json_file_path):
        print(f"❌ JSON file not found: {json_file_path}")
        return False
    
    print(f"📖 Loading vocabulary from: {json_file_path}")
    
    # Load JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            words_data = json.load(file)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Validate JSON structure
    if not isinstance(words_data, list):
        print("❌ Invalid JSON structure: Expected a list of words")
        return False
    
    print(f"✅ Loaded {len(words_data)} words from JSON file")
    
    # Filter out words with "To be added" placeholders (incomplete words)
    valid_words = []
    skipped_incomplete = 0
    
    for word_data in words_data:
        if not isinstance(word_data, dict):
            continue
            
        word = word_data.get('word', '').strip()
        word_type = word_data.get('type', '').strip()
        definition = word_data.get('definition', '').strip()
        example = word_data.get('example', '').strip()
        
        # Skip words with missing required fields or "To be added" placeholders
        if (not word or not word_type or not definition or not example or
            definition.lower() == 'to be added' or example.lower() == 'to be added' or
            word_type.lower() == 'to be added'):
            skipped_incomplete += 1
            continue
            
        valid_words.append(word_data)
    
    print(f"📝 Found {len(valid_words)} complete words to load")
    if skipped_incomplete > 0:
        print(f"⏭️  Skipped {skipped_incomplete} incomplete words (with 'To be added' placeholders)")
    
    if not valid_words:
        print("❌ No valid words found to load")
        return False
    
    # Initialize database manager
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        print(f"❌ Error initializing database manager: {e}")
        return False
    
    # Load words into database
    loaded_count = 0
    skipped_duplicates = 0
    
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            for word_data in valid_words:
                word = word_data.get('word', '').strip()
                word_type = word_data.get('type', '').strip()
                definition = word_data.get('definition', '').strip()
                example = word_data.get('example', '').strip()
                difficulty = word_data.get('difficulty', 'medium').strip()
                category = word_data.get('category', 'general').strip()
                
                try:
                    cursor.execute('''
                        INSERT INTO base_vocabulary (word, word_type, definition, example, difficulty, category, created_by, approved_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (word, word_type, definition, example, difficulty, category, created_by_user_id, created_by_user_id))
                    loaded_count += 1
                    
                    if loaded_count % 50 == 0:  # Progress indicator
                        print(f"📊 Progress: {loaded_count}/{len(valid_words)} words loaded...")
                        
                except Exception as e:
                    # Check if it's a duplicate word error
                    if "UNIQUE constraint failed" in str(e) or "word" in str(e).lower():
                        skipped_duplicates += 1
                        if skipped_duplicates <= 10:  # Show first 10 duplicates
                            print(f"⚠️  Skipping duplicate word: {word}")
                    else:
                        print(f"❌ Error inserting word '{word}': {e}")
            
            conn.commit()
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    # Print summary
    print("\n" + "="*60)
    print("🎉 JSON to Database Load Complete!")
    print("="*60)
    print(f"📊 Summary:")
    print(f"   • Total words in JSON: {len(words_data)}")
    print(f"   • Complete words found: {len(valid_words)}")
    print(f"   • Successfully loaded: {loaded_count}")
    print(f"   • Skipped duplicates: {skipped_duplicates}")
    print(f"   • Skipped incomplete: {skipped_incomplete}")
    print(f"   • Success rate: {loaded_count/len(valid_words)*100:.1f}%")
    
    if loaded_count > 0:
        print(f"\n✅ Successfully loaded {loaded_count} words into base_vocabulary table!")
        
        # Show some examples
        print(f"\n📝 Sample of loaded words:")
        sample_count = min(5, len(valid_words))
        for i, word_data in enumerate(valid_words[:sample_count]):
            word = word_data.get('word', '')
            word_type = word_data.get('type', '')
            difficulty = word_data.get('difficulty', 'medium')
            print(f"   • {word} ({word_type}) - {difficulty}")
        
        if len(valid_words) > sample_count:
            print(f"   ... and {len(valid_words) - sample_count} more")
    
    return True


def main():
    """Main function to handle script execution."""
    print("🚀 JSON to Base Vocabulary Loader")
    print("=" * 50)
    
    # Check if custom file path provided
    json_file = None
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    
    # Ask for confirmation
    json_path = json_file or 'seed-data/words-list.json'
    print(f"📁 Source file: {json_path}")
    print(f"🎯 Target table: base_vocabulary")
    print(f"\n⚠️  This will load words from the JSON file into the database.")
    print(f"   Duplicate words will be skipped automatically.")
    
    response = input("\nDo you want to continue? (y/N): ").lower().strip()
    if response != 'y' and response != 'yes':
        print("❌ Operation cancelled by user.")
        return
    
    # Load the data
    success = load_json_to_base_vocabulary(json_file)
    
    if success:
        print(f"\n🎊 All done! Words are now available in the base_vocabulary table.")
    else:
        print(f"\n💥 Loading failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()