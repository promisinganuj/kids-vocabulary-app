#!/usr/bin/env python3
"""
Script to load new words from CSV file and add them to the vocabulary JSON file,
avoiding duplicates and adding "To be added" for missing information.
"""

import json
import csv
import os

def load_new_words_from_csv():
    """Load new words from CSV and add to vocabulary JSON."""
    
    csv_file_path = 'vce_vocabulary_csv.txt'
    json_file_path = os.path.join('seed-data', 'words-list.json')
    
    # Load existing vocabulary data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            existing_words = json.load(file)
    except Exception as e:
        print(f"❌ Error loading existing vocabulary: {e}")
        return
    
    # Create a set of existing words (case-insensitive)
    existing_word_set = {word['word'].lower() for word in existing_words if isinstance(word, dict)}
    
    print(f"📚 Found {len(existing_words)} existing words in vocabulary")
    
    # Load new words from CSV
    new_words = []
    skipped_duplicates = 0
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                # Handle None values safely
                word = (row.get('word') or '').strip()
                word_type = (row.get('word_type') or '').strip()
                difficulty = (row.get('difficulty') or '').strip()
                
                if not word:
                    continue
                
                # Check for duplicates (case-insensitive)
                if word.lower() in existing_word_set:
                    skipped_duplicates += 1
                    continue
                
                # Create new word entry with "To be added" for missing info
                new_word_entry = {
                    "word": word.capitalize(),
                    "type": word_type.capitalize() if word_type else "To be added",
                    "definition": "To be added",
                    "example": "To be added"
                }
                
                # Add difficulty if provided
                if difficulty:
                    new_word_entry["difficulty"] = difficulty.capitalize()
                
                new_words.append(new_word_entry)
                existing_word_set.add(word.lower())  # Add to set to avoid duplicates within new words
    
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return
    
    print(f"✅ Found {len(new_words)} new words to add")
    print(f"⏭️  Skipped {skipped_duplicates} duplicate words")
    
    if new_words:
        # Add new words to existing vocabulary
        updated_vocabulary = existing_words + new_words
        
        # Save updated vocabulary
        try:
            with open(json_file_path, 'w', encoding='utf-8') as file:
                json.dump(updated_vocabulary, file, indent=2, ensure_ascii=False)
            
            print(f"💾 Successfully saved {len(updated_vocabulary)} total words to {json_file_path}")
            print(f"📈 Added {len(new_words)} new words")
            
            # Show some examples of new words added
            if len(new_words) > 0:
                print("\n📝 Sample of new words added:")
                for i, word in enumerate(new_words[:5]):
                    print(f"  • {word['word']} ({word['type']}) - {word.get('difficulty', 'No difficulty')}")
                if len(new_words) > 5:
                    print(f"  ... and {len(new_words) - 5} more")
            
        except Exception as e:
            print(f"❌ Error saving updated vocabulary: {e}")
    else:
        print("ℹ️  No new words to add - all words from CSV already exist in vocabulary")

if __name__ == '__main__':
    load_new_words_from_csv()
