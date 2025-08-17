# OpenAI Integration Setup Guide

## Overview
The word search functionality has been updated to use OpenAI LLM instead of the dictionary API. This provides more intelligent and context-aware word definitions.

## Setup Instructions

### 1. Install Dependencies
```bash
cd /Users/anuj/002-GitHub/kids-vocabulary-app/app
pip install openai==1.35.0 python-dotenv==1.0.0
```

### 2. Configure OpenAI Credentials
Create a `.env` file in the `app` directory:

```bash
cp .env.example .env
```

Edit the `.env` file and add your OpenAI credentials:

```env
# Your OpenAI API Key
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: Custom OpenAI Base URL (if using Azure OpenAI or other endpoint)
OPENAI_BASE_URL=https://api.openai.com/v1

# Optional: Specify different model (defaults to gpt-3.5-turbo)
OPENAI_MODEL=gpt-3.5-turbo
```

### 3. Required Information from You

Please provide:

1. **OpenAI API Key**: Your OpenAI API key (starts with `sk-...`)
2. **Base URL** (if different): If you're using Azure OpenAI or a custom endpoint
3. **Model** (optional): Which OpenAI model you prefer (gpt-3.5-turbo, gpt-4, etc.)

## How It Works

### OpenAI Prompt
The system sends this prompt to OpenAI:

```
Please provide information about the word "example" in the following JSON format:

{
    "word": "the word in proper case",
    "type": "part of speech (noun, verb, adjective, etc.)",
    "definition": "clear and concise definition", 
    "example": "a sentence example using the word",
    "error": null
}

If the word is not a valid English word or you cannot provide information about it, respond with:
{
    "word": null,
    "type": null,
    "definition": null,
    "example": null,
    "error": "not a valid word" or appropriate error message
}
```

### Expected Response Format
```json
{
    "word": "Example",
    "type": "noun",
    "definition": "A thing characteristic of its kind or illustrating a general rule",
    "example": "This sentence is a good example of proper usage",
    "error": null
}
```

### Error Handling
If there's an error, the response will be:
```json
{
    "word": null,
    "type": null,
    "definition": null,
    "example": null,
    "error": "not a valid word"
}
```

## Benefits of OpenAI Integration

1. **More Intelligent**: Can handle complex words, slang, and context
2. **Better Examples**: Generates more relevant and natural examples
3. **Error Handling**: Can identify and explain when words are invalid
4. **Customizable**: Can adjust prompts for specific needs
5. **Context Aware**: Understands word usage in different contexts

## Testing

Once configured, you can test the functionality:

1. Start the Flask app: `python web_flashcards.py`
2. Go to: `http://localhost:5001/manage`
3. Enter a word and click "🔍 Search"
4. The form should populate with AI-generated definitions

## Error Messages You Might See

- `"OpenAI API key not configured"` - Need to set OPENAI_API_KEY
- `"not a valid word"` - AI determined the word is invalid
- `"AI service error"` - Connection or API issues
- `"Failed to parse AI response"` - AI didn't return valid JSON

## Configuration Options

You can customize the behavior by modifying these in the `.env` file:

- `OPENAI_MODEL`: Change the AI model (gpt-3.5-turbo, gpt-4, etc.)
- `OPENAI_BASE_URL`: Use different endpoints (Azure OpenAI, etc.)

Let me know your OpenAI credentials and I'll help you complete the setup!
