#!/usr/bin/env python3
"""
Script to convert words-list.txt to words-list.json
"""

import re
import json
import os

def parse_word_entry(line):
    """Parse a single word entry from the text format"""
    # Skip comment lines and empty lines
    if line.startswith('#') or not line.strip():
        return None
    
    # Pattern to match: Word (Type) - Definition - Example
    pattern = r'^([A-Za-z]+)\s*\(([^)]+)\)\s*-\s*([^-]+?)\s*-\s*(.+)$'
    match = re.match(pattern, line.strip())
    
    if match:
        word = match.group(1).strip()
        word_type = match.group(2).strip()
        definition = match.group(3).strip()
        example = match.group(4).strip()
        
        return {
            "word": word,
            "type": word_type,
            "definition": definition,
            "example": example
        }
    else:
        print(f"Warning: Could not parse line: {line.strip()}")
        return None

def convert_words_file():
    """Convert words-list.txt to words-list.json"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, '..', 'seed-data', 'words-list.txt')
    output_file = os.path.join(script_dir, '..', 'seed-data', 'words-list.json')
    
    words_list = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                parsed_word = parse_word_entry(line)
                if parsed_word:
                    words_list.append(parsed_word)
        
        # Write to JSON file with proper formatting
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(words_list, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted {len(words_list)} words to {output_file}")
        return True
        
    except FileNotFoundError:
        print(f"Error: Could not find input file {input_file}")
        return False
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    convert_words_file()
