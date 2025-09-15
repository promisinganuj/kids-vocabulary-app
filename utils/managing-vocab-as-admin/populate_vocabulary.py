#!/usr/bin/env python3
"""
Vocabulary JSON Populator Script

This script populates missing word details (definitions and examples) in the words-list.json file
using the search_word_with_openai function from the web application.

Features:
- Loads the words-list.json file
- Identifies words with "To be added" placeholders
- Uses Azure OpenAI to fetch missing definitions and examples
- Implements rate limiting to avoid API limits
- Creates backups before making changes
- Provides progress tracking and logging

Author: AI Assistant
Date: August 2025
"""

import json
import sys
import os
import time
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the current directory to the Python path to import the OpenAI function
sys.path.append(os.path.dirname(__file__))

try:
    from app.openai_search import search_word_with_openai
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)

# Load environment variables
load_dotenv()

class VocabularyPopulator:
    """Class to handle vocabulary JSON file population."""
    
    def __init__(self, json_file_path: str, rate_limit_seconds: float = 5.0):
        """
        Initialize the populator.
        
        Args:
            json_file_path: Path to the words-list.json file
            rate_limit_seconds: Seconds to wait between API calls (default: 8 seconds)
        """
        self.json_file_path = json_file_path
        self.rate_limit_seconds = rate_limit_seconds
        self.backup_file_path = f"{json_file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.words_data: List[Dict[str, Any]] = []
        self.total_words = 0
        self.words_needing_update = 0
        self.processed_count = 0
        self.successful_updates = 0
        self.failed_updates = 0
        
    def load_json_file(self) -> bool:
        """Load the JSON file and validate its structure."""
        try:
            print(f"📖 Loading vocabulary file: {self.json_file_path}")
            
            if not os.path.exists(self.json_file_path):
                print(f"❌ File not found: {self.json_file_path}")
                return False
            
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                self.words_data = json.load(file)
            
            if not isinstance(self.words_data, list):
                print("❌ Invalid JSON structure: Expected a list of words")
                return False
            
            self.total_words = len(self.words_data)
            print(f"✅ Loaded {self.total_words} words from vocabulary file")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON format: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading file: {e}")
            return False
    
    def create_backup(self) -> bool:
        """Create a backup of the original file."""
        try:
            print(f"💾 Creating backup: {self.backup_file_path}")
            shutil.copy2(self.json_file_path, self.backup_file_path)
            print(f"✅ Backup created successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
    
    def identify_incomplete_words(self) -> List[Dict[str, Any]]:
        """Identify words that need updates (have 'To be added' placeholders)."""
        incomplete_words = []
        
        for i, word_entry in enumerate(self.words_data):
            if not isinstance(word_entry, dict):
                continue
                
            word = word_entry.get('word', '')
            definition = word_entry.get('definition', '')
            example = word_entry.get('example', '')
            word_type = word_entry.get('type', '')
            
            needs_update = False
            missing_fields = []
            
            if definition == "To be added" or not definition.strip():
                needs_update = True
                missing_fields.append('definition')
            
            if example == "To be added" or not example.strip():
                needs_update = True
                missing_fields.append('example')
            
            # Also check if type is missing or placeholder
            if word_type == "To be added" or not word_type.strip():
                needs_update = True
                missing_fields.append('type')
            
            if needs_update and word.strip():
                incomplete_words.append({
                    'index': i,
                    'word': word,
                    'current_type': word_type,
                    'current_definition': definition,
                    'current_example': example,
                    'missing_fields': missing_fields
                })
        
        self.words_needing_update = len(incomplete_words)
        print(f"🔍 Found {self.words_needing_update} words needing updates")
        
        if incomplete_words:
            print("📝 Sample words to be updated:")
            for word_info in incomplete_words[:5]:  # Show first 5 as sample
                missing = ", ".join(word_info['missing_fields'])
                print(f"   • {word_info['word']} (missing: {missing})")
            if len(incomplete_words) > 5:
                print(f"   ... and {len(incomplete_words) - 5} more")
        
        return incomplete_words
    
    def update_word_with_ai(self, word_info: Dict[str, Any]) -> bool:
        """
        Update a single word using the OpenAI function.
        
        Args:
            word_info: Dictionary containing word information and missing fields
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        word = word_info['word']
        index = word_info['index']
        missing_fields = word_info['missing_fields']
        
        print(f"\n🤖 Processing: {word} (missing: {', '.join(missing_fields)})")
        
        try:
            # Call the OpenAI function
            result = search_word_with_openai(word)
            
            if result.get('error'):
                print(f"   ❌ AI Error: {result['error']}")
                return False
            
            # Extract the results
            ai_word = result.get('word')
            ai_type = result.get('type')
            ai_definition = result.get('definition')
            ai_example = result.get('example')
            
            if not ai_word or not ai_definition or not ai_example:
                print(f"   ❌ Incomplete response from AI")
                return False
            
            # Update the word entry with new information
            word_entry = self.words_data[index]
            updated_fields = []
            
            # Update type if missing
            if 'type' in missing_fields and ai_type:
                word_entry['type'] = ai_type
                updated_fields.append('type')
            
            # Update definition if missing
            if 'definition' in missing_fields and ai_definition:
                word_entry['definition'] = ai_definition
                updated_fields.append('definition')
            
            # Update example if missing
            if 'example' in missing_fields and ai_example:
                word_entry['example'] = ai_example
                updated_fields.append('example')
            
            print(f"   ✅ Updated: {', '.join(updated_fields)}")
            print(f"   📝 Type: {ai_type}")
            print(f"   📝 Definition: {ai_definition[:80]}{'...' if len(ai_definition) > 80 else ''}")
            print(f"   📝 Example: {ai_example[:80]}{'...' if len(ai_example) > 80 else ''}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing {word}: {e}")
            return False
    
    def save_json_file(self) -> bool:
        """Save the updated JSON file."""
        try:
            print(f"\n💾 Saving updated vocabulary file...")
            
            with open(self.json_file_path, 'w', encoding='utf-8') as file:
                json.dump(self.words_data, file, indent=2, ensure_ascii=False)
            
            print(f"✅ Successfully saved {self.total_words} words to {self.json_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            return False
    
    def populate_vocabulary(self, max_words: Optional[int] = None, start_from: int = 0) -> bool:
        """
        Main method to populate the vocabulary file.
        
        Args:
            max_words: Maximum number of words to process (None for all)
            start_from: Index to start processing from (for resuming)
            
        Returns:
            bool: True if operation completed successfully
        """
        print("🚀 Starting Vocabulary JSON Populator")
        print("=" * 50)
        
        # Load the JSON file
        if not self.load_json_file():
            return False
        
        # Create backup
        if not self.create_backup():
            print("⚠️  Warning: Could not create backup. Continue anyway? (y/N): ", end="")
            if input().lower() != 'y':
                return False
        
        # Identify incomplete words
        incomplete_words = self.identify_incomplete_words()
        
        if not incomplete_words:
            print("🎉 All words are already complete! No updates needed.")
            return True
        
        # Apply start_from and max_words limits
        if start_from > 0:
            incomplete_words = incomplete_words[start_from:]
            print(f"📍 Starting from word #{start_from + 1}")
        
        if max_words:
            incomplete_words = incomplete_words[:max_words]
            print(f"🔢 Processing maximum {max_words} words")
        
        # Check API configuration
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        if not api_key or not endpoint or not deployment:
            print("❌ Azure OpenAI configuration missing!")
            print("\n🔧 Setup Instructions:")
            print("1. Copy the environment file:")
            print("   cp app/.env.example .env")
            print("2. Edit .env and add your Azure OpenAI credentials:")
            print("   AZURE_OPENAI_API_KEY=\"your_api_key_here\"")
            print("   AZURE_OPENAI_ENDPOINT=\"https://your-resource.openai.azure.com/\"")
            print("   AZURE_OPENAI_DEPLOYMENT=\"your_deployment_name\"")
            print("\n📖 See VOCABULARY_POPULATOR_README.md for detailed setup instructions.")
            return False
        
        print(f"\n🔧 Configuration:")
        print(f"   • Rate limit: {self.rate_limit_seconds} seconds between requests")
        print(f"   • Words to process: {len(incomplete_words)}")
        print(f"   • Estimated time: {len(incomplete_words) * self.rate_limit_seconds / 60:.1f} minutes")
        
        # Confirm before starting
        print(f"\n⚠️  This will make {len(incomplete_words)} API calls to Azure OpenAI.")
        print("Continue? (y/N): ", end="")
        if input().lower() != 'y':
            print("Operation cancelled.")
            return False
        
        # Process each incomplete word
        print(f"\n🔄 Processing {len(incomplete_words)} words...")
        start_time = time.time()
        
        for i, word_info in enumerate(incomplete_words):
            self.processed_count += 1
            
            # Show progress
            progress = (i + 1) / len(incomplete_words) * 100
            elapsed = time.time() - start_time
            eta = (elapsed / (i + 1)) * (len(incomplete_words) - i - 1) if i > 0 else 0
            
            print(f"\n📊 Progress: {i + 1}/{len(incomplete_words)} ({progress:.1f}%) | "
                  f"ETA: {eta/60:.1f}m | Success: {self.successful_updates} | "
                  f"Failed: {self.failed_updates}")
            
            # Update the word
            success = self.update_word_with_ai(word_info)
            
            if success:
                self.successful_updates += 1
            else:
                self.failed_updates += 1
            
            # Rate limiting (skip for the last item)
            if i < len(incomplete_words) - 1:
                print(f"   ⏳ Waiting {self.rate_limit_seconds} seconds...")
                time.sleep(self.rate_limit_seconds)
        
        # Save the updated file
        if not self.save_json_file():
            return False
        
        # Print summary
        total_time = time.time() - start_time
        print(f"\n🎉 Vocabulary population completed!")
        print("=" * 50)
        print(f"📊 Summary:")
        print(f"   • Total words processed: {self.processed_count}")
        print(f"   • Successful updates: {self.successful_updates}")
        print(f"   • Failed updates: {self.failed_updates}")
        print(f"   • Success rate: {self.successful_updates/self.processed_count*100:.1f}%")
        print(f"   • Total time: {total_time/60:.1f} minutes")
        print(f"   • Backup saved as: {self.backup_file_path}")
        
        if self.failed_updates > 0:
            print(f"\n⚠️  {self.failed_updates} words failed to update. You may want to:")
            print("   1. Check your API configuration")
            print("   2. Re-run the script to retry failed words")
            print("   3. Manually review the failed words")
        
        return True


def main():
    """Main function to run the vocabulary populator."""
    
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, 'seed-data', 'words-list.json')
    
    # Parse command line arguments
    max_words = None
    start_from = 0
    rate_limit = 5.0  # Default rate limit
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help' or sys.argv[1] == '-h':
            print("Vocabulary JSON Populator")
            print("=" * 30)
            print("Usage: python populate_vocabulary.py [max_words] [start_from] [rate_limit]")
            print()
            print("Arguments:")
            print("  max_words   : Maximum number of words to process (default: all)")
            print("  start_from  : Index to start from (default: 0)")
            print("  rate_limit  : Seconds between API calls (default: 8.0)")
            print()
            print("Examples:")
            print("  python populate_vocabulary.py           # Process all words")
            print("  python populate_vocabulary.py 10        # Process first 10 incomplete words")
            print("  python populate_vocabulary.py 10 5      # Process 10 words starting from index 5")
            print("  python populate_vocabulary.py 10 5 5.0  # Process 10 words, start from 5, 5s delay")
            return
        
        try:
            max_words = int(sys.argv[1]) if sys.argv[1] != 'all' else None
        except ValueError:
            print("❌ Invalid max_words argument. Use a number or 'all'.")
            return
    
    if len(sys.argv) > 2:
        try:
            start_from = int(sys.argv[2])
        except ValueError:
            print("❌ Invalid start_from argument. Use a number.")
            return
    
    if len(sys.argv) > 3:
        try:
            rate_limit = float(sys.argv[3])
        except ValueError:
            print("❌ Invalid rate_limit argument. Use a number (seconds).")
            return
    
    # Create and run the populator
    populator = VocabularyPopulator(json_file_path, rate_limit)
    success = populator.populate_vocabulary(max_words, start_from)
    
    if success:
        print("\n✅ Script completed successfully!")
    else:
        print("\n❌ Script failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
