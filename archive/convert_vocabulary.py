#!/usr/bin/env python3
"""
Vocabulary File Format Converter

This script converts old numbered vocabulary files to the new unnumbered format.
It also removes duplicates in the process.

Usage: python convert_vocabulary.py [input_file] [output_file]
"""

import re
import sys
import os
from datetime import datetime


def convert_vocabulary_file(input_file, output_file=None):
    """Convert vocabulary file from numbered to unnumbered format and remove duplicates."""
    
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found.")
        return False
    
    if output_file is None:
        output_file = input_file
    
    print(f"📖 Reading vocabulary from: {input_file}")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Try both patterns
        words = []
        seen_words = set()
        
        # Pattern for numbered format: "Number. Word (Type) - Definition - Example."
        pattern_numbered = r'(\d+)\.\s+([A-Za-z]+)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
        matches_numbered = re.findall(pattern_numbered, content)
        
        # Pattern for unnumbered format: "Word (Type) - Definition - Example."
        pattern_unnumbered = r'([A-Za-z]+)\s+\(([^)]+)\)\s+-\s+([^-]+)\s+-\s+(.+)'
        matches_unnumbered = re.findall(pattern_unnumbered, content)
        
        if matches_numbered:
            print("📝 Found numbered format, converting...")
            for match in matches_numbered:
                number, word, word_type, definition, example = match
                word_key = word.lower().strip()
                if word_key not in seen_words:
                    words.append((word.strip(), word_type.strip(), definition.strip(), example.strip()))
                    seen_words.add(word_key)
                else:
                    print(f"⚠️  Skipping duplicate: {word}")
        elif matches_unnumbered:
            print("📝 Found unnumbered format, checking for duplicates...")
            for match in matches_unnumbered:
                word, word_type, definition, example = match
                word_key = word.lower().strip()
                if word_key not in seen_words:
                    words.append((word.strip(), word_type.strip(), definition.strip(), example.strip()))
                    seen_words.add(word_key)
                else:
                    print(f"⚠️  Skipping duplicate: {word}")
        else:
            print("❌ Error: No vocabulary words found in the expected format.")
            return False
        
        # Create backup if overwriting the same file
        if output_file == input_file:
            backup_file = f"{input_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_file, 'w', encoding='utf-8') as backup:
                backup.write(content)
            print(f"💾 Created backup: {backup_file}")
        
        # Write the converted file
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write("# VCE Vocabulary Words\n")
            file.write("# Format: Word (Type) - Definition - Example.\n\n")
            
            for word, word_type, definition, example in words:
                file.write(f"{word} ({word_type}) - {definition} - {example}\n")
        
        print(f"✅ Successfully converted {len(words)} unique words")
        print(f"📁 Output saved to: {output_file}")
        
        duplicates_removed = len(matches_numbered or matches_unnumbered) - len(words)
        if duplicates_removed > 0:
            print(f"🗑️  Removed {duplicates_removed} duplicate entries")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing file: {str(e)}")
        return False


def main():
    """Main function to handle command line arguments."""
    
    if len(sys.argv) < 2:
        # Use default file if no arguments provided
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        input_file = os.path.join(parent_dir, 'new-words.txt')
        output_file = None
    elif len(sys.argv) == 2:
        input_file = sys.argv[1]
        output_file = None
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    
    print("=" * 60)
    print("    VOCABULARY FILE FORMAT CONVERTER")
    print("=" * 60)
    print(f"📥 Input:  {input_file}")
    print(f"📤 Output: {output_file or input_file}")
    print()
    
    success = convert_vocabulary_file(input_file, output_file)
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 Conversion completed successfully!")
        print("Your vocabulary file is now in the new format and duplicate-free!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Conversion failed. Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
