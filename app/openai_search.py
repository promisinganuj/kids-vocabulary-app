#!/usr/bin/env python3
"""
OpenAI Word Search Module

This module contains the search_word_with_openai function extracted from web_flashcards.py
for use in standalone scripts without Flask dependencies.
"""

import os
import json
import requests
from typing import Dict, Union, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def search_word_with_openai(word: str) -> Dict[str, Optional[str]]:
    """
    Search for word definition using Azure OpenAI LLM via HTTP requests.
    
    Args:
        word: The word to search for
        
    Returns:
        dict: Response in the format {word, type, definition, example, error}
    """
    try:
        # Get Azure OpenAI configuration and validate
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        if not api_key:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI API key not configured. Please set AZURE_OPENAI_API_KEY environment variable."
            }
        
        if not endpoint:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI endpoint not configured. Please set AZURE_OPENAI_ENDPOINT environment variable."
            }
            
        if not deployment:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI deployment not configured. Please set AZURE_OPENAI_DEPLOYMENT environment variable."
            }
        
        # Create the prompt for word definition
        prompt = f"""Please provide information about the word "{word}" in the following JSON format:

{{
    "word": "The word in proper case",
    "type": "Part of speech (Noun, Verb, Adjective, Adverb, etc.)",
    "definition": "Clear and concise definition",
    "example": "A sentence example using the word",
    "error": null
}}

If the word is not a valid English word or you cannot provide information about it, respond with:
{{
    "word": null,
    "type": null,
    "definition": null,
    "example": null,
    "error": "not a valid word" or appropriate error message
}}

If the word can be of many types, please return the one which is the most common.

Only respond with valid JSON, no additional text."""

        # Ensure endpoint ends with a slash
        if not endpoint.endswith('/'):
            endpoint += '/'
        
        # Prepare Azure OpenAI HTTP request
        url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {
            "api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": [
                {"role": "system", "content": "You are a helpful dictionary assistant. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        
        # Make the HTTP request
        print (data)
        print(url)
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print(response.text)
        
        if response.status_code == 200:
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].strip()
            
            # Parse the JSON response
            try:
                result = json.loads(content)
                
                # Validate the response format
                required_keys = ["word", "type", "definition", "example", "error"]
                if not all(key in result for key in required_keys):
                    return {
                        "word": None,
                        "type": None,
                        "definition": None,
                        "example": None,
                        "error": "Invalid response format from AI"
                    }
                
                return result
                
            except json.JSONDecodeError:
                return {
                    "word": None,
                    "type": None,
                    "definition": None,
                    "example": None,
                    "error": "Failed to parse AI response"
                }
        else:
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": f"Azure OpenAI API error: {response.status_code} - {response.text[:100]}"
            }
            
    except requests.exceptions.Timeout:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": "Azure OpenAI request timed out. Please try again."
        }
    except requests.exceptions.ConnectionError:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": "Unable to connect to Azure OpenAI service. Please check your internet connection and endpoint."
        }
    except requests.exceptions.RequestException as e:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": f"Azure OpenAI service error: {str(e)}"
        }
