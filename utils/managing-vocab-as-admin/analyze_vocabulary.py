#!/usr/bin/env python3
"""
Quick analysis script to check how many words need updating in the JSON file.
"""

import json
import os

def analyze_vocabulary_file():
    """Analyze the vocabulary file and show statistics."""

    json_file_path = os.path.join('seed-data', 'words-list.json')

    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            words_data = json.load(file)
        
        total_words = len(words_data)
        needs_definition = 0
        needs_example = 0
        needs_type = 0
        needs_any = 0

        for word_entry in words_data:
            if not isinstance(word_entry, dict):
                continue

            word = word_entry.get('word', '')
            definition = word_entry.get('definition', '')
            example = word_entry.get('example', '')
            word_type = word_entry.get('type', '')
            
            has_issues = False
            
            if definition == "To be added" or not definition.strip():
                needs_definition += 1
                has_issues = True
            
            if example == "To be added" or not example.strip():
                needs_example += 1
                has_issues = True
            
            if word_type == "To be added" or not word_type.strip():
                needs_type += 1
                has_issues = True
                
            if has_issues:
                needs_any += 1
        
        print("📊 Vocabulary File Analysis")
        print("=" * 40)
        print(f"Total words: {total_words}")
        print(f"Words needing definition: {needs_definition}")
        print(f"Words needing example: {needs_example}")
        print(f"Words needing type: {needs_type}")
        print(f"Words needing any update: {needs_any}")
        print(f"Complete words: {total_words - needs_any}")
        print(f"Completion rate: {(total_words - needs_any) / total_words * 100:.1f}%")
        
        if needs_any > 0:
            print(f"\n🤖 Estimated API calls needed: {needs_any}")
            print(f"⏱️  Estimated time (8s per call): {needs_any * 8 / 60:.1f} minutes")
            print(f"💰 Estimated cost (rough): ${needs_any * 0.002:.2f} - ${needs_any * 0.01:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    analyze_vocabulary_file()
