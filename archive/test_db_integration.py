#!/usr/bin/env python3
"""
Test script to verify database integration with Flask app
"""

from database_manager import DatabaseManager

def test_database_integration():
    """Test the database integration."""
    print("🧪 Testing database integration...")
    
    # Initialize database manager
    db_manager = DatabaseManager('data/vocabulary.db')
    
    # Test getting all words
    words = db_manager.get_all_words()
    print(f"📊 Found {len(words)} words in database")
    
    if words:
        print("✅ Sample words:")
        for i, word in enumerate(words[:3]):
            print(f"  {i+1}. {word['word']} ({word['word_type']}) - {word['definition'][:50]}...")
    
    # Test search functionality
    search_results = db_manager.search_words("advocate")
    print(f"🔍 Search for 'advocate' found {len(search_results)} results")
    
    # Test add word (and remove it to keep database clean)
    test_word = "TestWord"
    success, message = db_manager.add_word(test_word, "Noun", "A test definition", "This is a test example.")
    if success:
        print(f"✅ Successfully added test word: {message}")
        
        # Find and remove the test word
        all_words = db_manager.get_all_words()
        test_word_id = None
        for word in all_words:
            if word['word'] == test_word:
                test_word_id = word['id']
                break
        
        if test_word_id:
            success, message = db_manager.remove_word(test_word_id)
            if success:
                print(f"✅ Successfully removed test word: {message}")
            else:
                print(f"❌ Failed to remove test word: {message}")
    else:
        print(f"❌ Failed to add test word: {message}")
    
    print("🎉 Database integration test completed!")

if __name__ == '__main__':
    test_database_integration()
