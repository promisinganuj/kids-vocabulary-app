#!/usr/bin/env python3
"""
Test script for OpenAI integration.
Tests the search_word_with_openai function with a sample word.
"""

import os
from app.openai_search import search_word_with_openai
from dotenv import load_dotenv

def test_openai_integration():
    """Test the OpenAI integration with a sample word."""
    
    print("🧪 Testing OpenAI Integration")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Check configuration
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") 
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    
    print("📋 Configuration Check:")
    print(f"   API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"   Endpoint: {'✅ Set' if endpoint else '❌ Missing'}")
    print(f"   Deployment: {'✅ Set' if deployment else '❌ Missing'}")
    
    if not all([api_key, endpoint, deployment]):
        print("\n❌ Configuration incomplete. Please set up your .env file.")
        print("See VOCABULARY_POPULATOR_README.md for setup instructions.")
        return False
    
    # Test with a sample word
    test_word = "serendipity"
    print(f"\n🤖 Testing with word: '{test_word}'")
    print("Making API call...")
    
    try:
        result = search_word_with_openai(test_word)
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
            return False
        
        print("✅ Success! Response received:")
        print(f"   Word: {result.get('word')}")
        print(f"   Type: {result.get('type')}")
        print(f"   Definition: {result.get('definition')}")
        print(f"   Example: {result.get('example')}")
        
        print("\n🎉 OpenAI integration is working correctly!")
        print("You can now run the vocabulary populator script.")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = test_openai_integration()
    exit(0 if success else 1)
