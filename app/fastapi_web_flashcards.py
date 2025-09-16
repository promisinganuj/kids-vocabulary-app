#!/usr/bin/env python3
"""
Vocabulary Flashcard Web Application

A FastAPI-based web application for managing vocabulary flashcards with multi-user support.
Features:
- User authentication and registration
- User-specific vocabulary libraries
- View flashcards with flip functionality
- Add new vocabulary words
- Remove learned words
- Study session tracking
- Progress analytics
- Search and filter functionality

Author: Anuj Parashar (Powered by AI Assistant)
Date: September 2025
"""

from fastapi import FastAPI, Request, HTTPException, Depends, Form, Query, Path, Cookie, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import HTTPBearer
import re
import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
import shutil
from database_manager import DatabaseManager, initialize_multiuser_from_text_file, migrate_date_of_birth_to_year_of_birth, User
from fastapi_auth import (
    init_authentication, get_current_user, require_authentication, require_admin, 
    get_session_token, auth_manager, user_preferences, RequestState, request_state
)
from dotenv import load_dotenv
from pydantic import BaseModel
import secrets

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Vocabulary Flashcard Application",
    description="A web application for managing vocabulary flashcards with multi-user support",
    version="2.0.0"
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key=os.environ.get('SECRET_KEY', secrets.token_hex(32)))

# Mount static files (we'll configure this later if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize database
db_path = os.path.join('data', 'vocabulary.db')
db_manager = DatabaseManager(db_path)

# Initialize authentication
init_authentication(db_manager)

# Text file path for initial data loading
text_file = os.path.join('..', 'seed-data', 'words-list.txt')

# OpenAI word search function
def search_word_with_openai(word: str) -> dict:
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
    "word": "The word in Camel case",
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

If the word can be of many types, please return one one which is the most common.

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
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
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

# Pydantic models for request/response
class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    confirm_password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_number: Optional[str] = None
    profile_type: str = "Student"
    class_year: Optional[int] = None
    year_of_birth: Optional[int] = None
    school_name: Optional[str] = None
    preferred_study_time: Optional[str] = None
    learning_goals: Optional[str] = None
    avatar_color: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class WordRequest(BaseModel):
    word: str
    type: str
    definition: str
    example: Optional[str] = None

class WordUpdateRequest(BaseModel):
    word: Optional[str] = None
    type: Optional[str] = None
    definition: Optional[str] = None
    example: Optional[str] = None

class AIFeedbackRequest(BaseModel):
    word: str
    feedback: str
    helpful: bool

class StudySessionRequest(BaseModel):
    session_type: str = "standard"

class AIResponseRequest(BaseModel):
    user_response: str
    time_taken: Optional[int] = None

class UserPreferencesRequest(BaseModel):
    preferences: Dict[str, str]

class UserProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    mobile_number: Optional[str] = None
    profile_type: Optional[str] = None
    class_year: Optional[int] = None
    year_of_birth: Optional[int] = None
    school_name: Optional[str] = None
    preferred_study_time: Optional[str] = None
    learning_goals: Optional[str] = None
    avatar_color: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class AdminUserUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    profile_type: Optional[str] = None

# Middleware to set request state for backwards compatibility
@app.middleware("http")
async def set_request_state(request: Request, call_next):
    """Middleware to store current user in request state for sync functions."""
    global request_state
    request_state = RequestState()
    
    # Try to get current user
    try:
        token = await get_session_token(request)
        if token and auth_manager:
            user = auth_manager.validate_session(token)
            request_state.current_user = user
            request_state.session_token = token
    except:
        pass
    
    response = await call_next(request)
    return response

# Helper functions
def require_admin_sync():
    """Ensure current user is an admin. Returns user_id if admin, raises exception otherwise."""
    if not request_state or not request_state.current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    user_id = request_state.current_user.user_id
    if not db_manager.is_user_admin(user_id):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user_id

def is_admin_sync():
    """Check if current user is an admin."""
    try:
        if request_state and request_state.current_user:
            return db_manager.is_user_admin(request_state.current_user.user_id)
        return False
    except:
        return False

# Template context processor function
def get_template_context(request: Request, current_user: Optional[User] = None):
    """Get common template context."""
    context = {
        "request": request,
        "current_user": current_user,
        "user": current_user,  # Some templates expect 'user' instead of 'current_user'
        "is_admin": is_admin_sync() if current_user else False,
        "words": [],  # Default empty list
        "total_words": 0  # Default count
    }
    return context

def get_ai_word_suggestion_based_on_patterns(user_id: int) -> dict:
    """
    Generate AI word suggestions based on user's learning patterns and current vocabulary level.
    
    Args:
        user_id: The user's ID
        
    Returns:
        dict: Response in the format {word, type, definition, example, error, reasoning}
    """
    try:
        # Get Azure OpenAI configuration and validate
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        if not all([api_key, endpoint, deployment]):
            return {
                "word": None,
                "type": None,
                "definition": None,
                "example": None,
                "error": "Azure OpenAI not properly configured",
                "reasoning": None
            }
        
        # Analyze user's learning patterns
        analysis = db_manager.analyze_user_learning_patterns(user_id)
        user_words = db_manager.get_user_words(user_id)
        
        # Get user profile for context
        user = db_manager.get_user_by_id(user_id)
        
        # Create comprehensive list of words to avoid (both visible and hidden words)
        words_to_avoid = set()
        
        # Get all user words (including hidden ones)
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT LOWER(TRIM(word)) as word FROM vocabulary 
                    WHERE user_id = ?
                ''', (user_id,))
                user_vocabulary = [row['word'] for row in cursor.fetchall()]
                words_to_avoid.update(user_vocabulary)
        except Exception as e:
            print(f"Warning: Could not fetch complete user vocabulary: {e}")
            # Fallback to regular method
            user_vocabulary = [w.get("word", "").lower().strip() for w in user_words if w.get("word")]
            words_to_avoid.update(user_vocabulary)
        
        # Get words from AI feedback history (words user has already seen)
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT LOWER(TRIM(word)) as word FROM ai_suggestions_feedback 
                    WHERE user_id = ?
                ''', (user_id,))
                seen_words = [row['word'] for row in cursor.fetchall()]
                words_to_avoid.update(seen_words)
        except Exception as e:
            print(f"Warning: Could not fetch AI feedback history: {e}")
        
        # Add common word variations to be extra safe
        words_with_variations = set(words_to_avoid)
        for word in list(words_to_avoid):
            # Add plural forms
            if not word.endswith('s'):
                words_with_variations.add(word + 's')
            # Add common suffixes
            if len(word) > 4:
                words_with_variations.add(word + 'ing')
                words_with_variations.add(word + 'ed')
                words_with_variations.add(word + 'er')
                words_with_variations.add(word + 'ly')
        
        words_to_avoid = words_with_variations
        print(f"📝 Words to avoid for user {user_id}: {len(words_to_avoid)} total (including variations)")
        
        # Build context for AI
        user_context = {
            "total_words": len(user_words),
            "average_accuracy": analysis.get("average_accuracy", 50),
            "difficult_words": analysis.get("difficult_words", []),
            "easy_words": analysis.get("easy_words", []),
            "common_word_types": analysis.get("common_word_types", []),
            "class_year": user.class_year if user else None,
            "learning_goals": user.learning_goals if user else None,
            "recent_words": [w.get("word", "") for w in user_words[-5:]] if user_words else []
        }
        
        # Create list of words to explicitly avoid in the prompt (limit to avoid prompt being too long)
        avoid_words_sample = sorted(list(words_to_avoid))[:150]  # Increased from 100 to 150
        avoid_words_list = ", ".join(avoid_words_sample)
        
        # Additional words list for emphasis (most recent words)
        recent_avoided_words = sorted(list(words_to_avoid))[-50:] if len(words_to_avoid) > 50 else []
        recent_words_emphasis = ", ".join(recent_avoided_words) if recent_avoided_words else ""
        
        # Create the prompt for AI word suggestion
        prompt = f"""You are an AI tutor helping a student learn vocabulary. Based on their learning patterns, suggest ONE new vocabulary word that would be perfect for their next learning session.

Student Profile:
- Total vocabulary words learned: {user_context['total_words']}
- Average accuracy: {user_context['average_accuracy']}%
- Class year: {user_context['class_year'] or 'Not specified'}
- Learning goals: {user_context['learning_goals'] or 'General vocabulary improvement'}
- Recent words they've studied: {', '.join(user_context['recent_words'][:3]) if user_context['recent_words'] else 'None yet'}

Learning Pattern Analysis:
- Words they find easy: {', '.join(user_context['easy_words'][:3]) if user_context['easy_words'] else 'Building baseline'}
- Words they find challenging: {', '.join(user_context['difficult_words'][:3]) if user_context['difficult_words'] else 'None identified yet'}
- Common word types they study: {', '.join(user_context['common_word_types'][:3]) if user_context['common_word_types'] else 'Various'}

❌ CRITICAL: DO NOT SUGGEST ANY OF THESE WORDS - THEY ALREADY KNOW THEM:
{avoid_words_list}

❌ ESPECIALLY AVOID THESE RECENT WORDS:
{recent_words_emphasis}

🚨 ABSOLUTE REQUIREMENTS:
1. The word MUST NOT appear in the forbidden lists above
2. The word must be completely NEW and UNKNOWN to this student
3. Do not suggest ANY variations, forms, or derivatives of forbidden words
4. If unsure whether a word is in their vocabulary, choose a different word
5. Check your suggestion against the forbidden lists before responding

Instructions for the perfect word:
1. Suggest a word that is appropriately challenging (not too easy, not too hard)
2. Choose a word that complements their existing vocabulary
3. Consider their class level and learning goals
4. Provide a clear, student-friendly definition
5. Give a practical example sentence
6. Explain why this word is perfect for this student

Respond ONLY with valid JSON in this exact format:
{{
    "word": "Word in proper case",
    "type": "Part of speech (Noun, Verb, Adjective, etc.)",
    "definition": "Clear, concise definition appropriate for their level",
    "example": "A practical example sentence using the word",
    "reasoning": "Brief explanation of why this word is perfect for this student",
    "error": null
}}

If you cannot suggest a word that meets ALL requirements, respond with:
{{
    "word": null,
    "type": null,
    "definition": null,
    "example": null,
    "reasoning": null,
    "error": "Could not find a suitable new word that meets all requirements"
}}"""

        # Retry mechanism for getting unique words
        max_retries = 3
        retry_count = 0
        failed_words = []  # Track words that failed
        
        while retry_count < max_retries:
            # Ensure endpoint ends with a slash
            if endpoint and not endpoint.endswith('/'):
                endpoint += '/'
            
            # Prepare Azure OpenAI HTTP request
            url = f"{endpoint}openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
            
            # Increase temperature for variety on retries
            temperature = 0.7 + (retry_count * 0.15)
            
            # Modify prompt for retries to include failed words
            current_prompt = prompt
            if failed_words:
                failed_words_text = ", ".join(failed_words)
                current_prompt += f"\n\n🚨 URGENT: You already suggested these words which they know: {failed_words_text}\nDo NOT suggest these or similar words again!"
            
            data = {
                "messages": [
                    {"role": "system", "content": "You are an expert vocabulary tutor who provides personalized word suggestions based on learning patterns. Always respond with valid JSON only. Never suggest words the student already knows or has seen."},
                    {"role": "user", "content": current_prompt}
                ],
                "max_tokens": 400,
                "temperature": temperature
            }
            
            print(f"🤖 AI request attempt {retry_count + 1}/{max_retries} with temperature {temperature}")
            
            try:
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                ai_response = response.json()
                content = ai_response['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                try:
                    result = json.loads(content)
                    suggested_word = result.get('word', '').lower().strip()
                    
                    # Validate that the word is not in the forbidden list
                    if suggested_word and suggested_word not in words_to_avoid:
                        print(f"✅ AI suggested new word: {suggested_word}")
                        return result
                    else:
                        if suggested_word:
                            failed_words.append(suggested_word)
                            print(f"❌ AI suggested word '{suggested_word}' is already known by user")
                        retry_count += 1
                        continue
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing error: {e}")
                    print(f"Raw content: {content}")
                    retry_count += 1
                    continue
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request error: {e}")
                retry_count += 1
                continue
        
        # If all retries failed
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": f"Unable to generate unique word after {max_retries} attempts",
            "reasoning": None
        }
        
    except Exception as e:
        print(f"❌ Unexpected error in get_ai_word_suggestion_based_on_patterns: {e}")
        return {
            "word": None,
            "type": None,
            "definition": None,
            "example": None,
            "error": f"Error generating AI suggestion: {str(e)}",
            "reasoning": None
        }

# Routes

# Favicon route to prevent 404 errors
@app.get('/favicon.ico')
async def favicon():
    """Return empty response for favicon to prevent 404 errors."""
    return Response(status_code=204)

# Authentication Routes
@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Login page."""
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", get_template_context(request, current_user))

@app.get('/register', response_class=HTMLResponse)
async def register_page(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Registration page."""
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("register.html", get_template_context(request, current_user))

@app.post('/api/auth/register')
async def register(
    request: Request,
    email: str = Form(None),
    username: str = Form(None),
    password: str = Form(None),
    confirm_password: str = Form(None),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None)
):
    """API endpoint to register a new user."""
    # Try to get data from form first, then JSON
    if not email or not username or not password:
        try:
            json_data = await request.json()
            email = json_data.get('email')
            username = json_data.get('username')
            password = json_data.get('password')
            confirm_password = json_data.get('confirm_password')
            first_name = json_data.get('first_name')
            last_name = json_data.get('last_name')
        except:
            pass
    
    # Validation
    if not email or not username or not password:
        raise HTTPException(status_code=400, detail='Email, username, and password are required')
    
    if password != confirm_password:
        raise HTTPException(status_code=400, detail='Passwords do not match')
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail='Password must be at least 6 characters long')
    
    # Email validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email.lower()):
        raise HTTPException(status_code=400, detail='Invalid email format')
    
    # Create user
    success, message, user_id = db_manager.create_user(
        email=email.strip().lower(),
        username=username.strip(),
        password=password
    )
    
    if success and user_id:
        # Note: Additional user profile fields would need to be updated separately
        # as the create_user method only accepts basic fields
        return JSONResponse(content={'success': True, 'message': message, 'user_id': user_id})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post('/api/auth/login')
async def login(
    request: Request, 
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    email_or_username: Optional[str] = Form(None)
):
    """API endpoint to authenticate a user."""
    # Try to get data from form first, then JSON
    if not email and not email_or_username:
        try:
            json_data = await request.json()
            email = json_data.get('email')
            email_or_username = json_data.get('email_or_username')
            password = json_data.get('password')
        except:
            pass
    
    # Use email_or_username if email is not provided
    login_identifier = email or email_or_username
    
    if not login_identifier or not password:
        raise HTTPException(status_code=400, detail='Email/username and password are required')
    
    # Authenticate user
    success, message, user = db_manager.authenticate_user(login_identifier.strip().lower(), password)
    
    if success and user and auth_manager:
        # Create session
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent')
        session_token = auth_manager.create_session(user, ip_address, user_agent)
        
        # Update last login
        # db_manager.update_last_login(user.user_id)  # Method may not exist, commenting out
        
        response = JSONResponse(content={
            'success': True, 
            'message': 'Login successful',
            'user': user.to_dict(),
            'session_token': session_token
        })
        
        # Set session cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax"
        )
        
        return response
    else:
        raise HTTPException(status_code=401, detail=message)

@app.post('/api/auth/logout')
async def logout(request: Request, session_token: Optional[str] = Depends(get_session_token)):
    """API endpoint to logout user."""
    if session_token and auth_manager:
        auth_manager.delete_session(session_token)
    
    response = JSONResponse(content={'success': True, 'message': 'Logged out successfully'})
    response.delete_cookie("session_token")
    return response

@app.get('/logout')
async def logout_redirect(request: Request, session_token: Optional[str] = Depends(get_session_token)):
    """Logout and redirect to login page."""
    if session_token and auth_manager:
        auth_manager.delete_session(session_token)
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_token")
    return response

# Main application routes
@app.get('/', response_class=HTMLResponse)
async def index(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Main flashcards page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    # Get user's words for the template
    words = db_manager.get_user_words(current_user.user_id)
    is_user_admin = is_admin_sync()
    
    context = get_template_context(request, current_user)
    context.update({
        "words": words,
        "total_words": len(words),
        "is_admin": is_user_admin
    })
    
    return templates.TemplateResponse("flashcards.html", context)

@app.get('/api/words')
async def get_words(
    current_user: User = Depends(require_authentication),
    search: Optional[str] = Query(None),
    word_type: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(0),
    include_hidden: bool = Query(False)
):
    """API endpoint to get user's vocabulary words."""
    words = db_manager.get_user_words(current_user.user_id)
    
    # Apply filtering manually since the method doesn't support these parameters
    if search:
        words = [w for w in words if search.lower() in w.get('word', '').lower()]
    
    if word_type:
        words = [w for w in words if w.get('word_type', '').lower() == word_type.lower()]
    
    if not include_hidden:
        words = [w for w in words if not w.get('is_hidden', False)]
    
    # Apply pagination
    if offset:
        words = words[offset:]
    if limit:
        words = words[:limit]
    
    return JSONResponse(content={'success': True, 'words': words})

@app.post('/api/words')
async def add_word(data: WordRequest, current_user: User = Depends(require_authentication)):
    """API endpoint to add a new word."""
    if not data.word or not data.type or not data.definition:
        raise HTTPException(status_code=400, detail='Word, type, and definition are required')
    
    # Clean and validate input
    word = data.word.strip()
    word_type = data.type.strip()
    definition = data.definition.strip()
    example = data.example.strip() if data.example else ""
    
    if len(word) > 100:
        raise HTTPException(status_code=400, detail='Word is too long (max 100 characters)')
    
    if len(definition) > 500:
        raise HTTPException(status_code=400, detail='Definition is too long (max 500 characters)')
    
    if example and len(example) > 500:
        raise HTTPException(status_code=400, detail='Example is too long (max 500 characters)')
    
    # Check if word already exists for this user
    existing_words = db_manager.get_user_words(current_user.user_id)
    if existing_words and any(w['word'].lower() == word.lower() for w in existing_words):
        raise HTTPException(status_code=400, detail='Word already exists in your vocabulary')
    
    # Add word
    success, message = db_manager.add_user_word(current_user.user_id, word, word_type, definition, example)
    
    if success:
        return JSONResponse(content={'success': True, 'message': 'Word added successfully'})
    else:
        raise HTTPException(status_code=500, detail='Failed to add word')

@app.delete('/api/words/{word_id}')
async def delete_word(word_id: int, current_user: User = Depends(require_authentication)):
    """API endpoint to delete a word."""
    success, message = db_manager.remove_user_word(current_user.user_id, word_id)
    
    if success:
        return JSONResponse(content={'success': True, 'message': 'Word deleted successfully'})
    else:
        raise HTTPException(status_code=404, detail=message)

@app.put('/api/words/{word_id}')
async def update_word(word_id: int, data: WordUpdateRequest, current_user: User = Depends(require_authentication)):
    """API endpoint to update a word."""
    # Get current word to verify ownership
    words = db_manager.get_user_words(current_user.user_id)
    word = next((w for w in words if w['id'] == word_id), None)
    
    if not word:
        raise HTTPException(status_code=404, detail='Word not found')
    
    # Use provided values or keep existing ones
    new_word = data.word.strip() if data.word is not None else word['word']
    new_type = data.type.strip() if data.type is not None else word['word_type']
    new_definition = data.definition.strip() if data.definition is not None else word['definition']
    new_example = data.example.strip() if data.example is not None else word['example']
    
    success, message = db_manager.update_user_word(current_user.user_id, word_id, new_word, new_type, new_definition, new_example)
    
    if success:
        return JSONResponse(content={'success': True, 'message': 'Word updated successfully'})
    else:
        raise HTTPException(status_code=500, detail=message)

# Word interaction routes
@app.post('/api/words/{word_id}/like')
async def like_word(word_id: int, current_user: User = Depends(require_authentication)):
    """Like a word."""
    success, message = db_manager.like_word(current_user.user_id, word_id)
    
    if success:
        return JSONResponse(content={'success': True, 'message': message})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post('/api/words/{word_id}/unlike')
async def unlike_word(word_id: int, current_user: User = Depends(require_authentication)):
    """Unlike a word."""
    success, message = db_manager.unlike_word(current_user.user_id, word_id)
    
    if success:
        return JSONResponse(content={'success': True, 'message': message})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post('/api/words/{word_id}/hide')
async def hide_word(word_id: int, current_user: User = Depends(require_authentication)):
    """Hide a word from user's vocabulary."""
    success, message = db_manager.hide_word_for_user(current_user.user_id, word_id)
    
    if success:
        return JSONResponse(content={'success': True, 'message': message})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post('/api/words/{word_id}/unhide')
async def unhide_word(word_id: int, current_user: User = Depends(require_authentication)):
    """Unhide a word in user's vocabulary."""
    success, message = db_manager.unhide_word_for_user(current_user.user_id, word_id)
    
    if success:
        return JSONResponse(content={'success': True, 'message': message})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post('/api/words/{word_id}/review')
async def review_word(word_id: int, request: Request, current_user: User = Depends(require_authentication)):
    """Record a word review (correct/incorrect) for the user."""
    try:
        json_data = await request.json()
    except:
        raise HTTPException(status_code=400, detail='Missing "correct" parameter')
    
    if 'correct' not in json_data:
        raise HTTPException(status_code=400, detail='Missing "correct" parameter')
    
    correct = bool(json_data['correct'])
    auto = bool(json_data.get('auto', True))

    success, message = db_manager.record_word_review(current_user.user_id, word_id, correct)

    actions = []
    if success and auto:
        try:
            if correct:
                # Correct answer: ease the difficulty and hide from active queue
                db_manager.update_word_difficulty(current_user.user_id, word_id, 'easy')
                db_manager.hide_word_for_user(current_user.user_id, word_id)
                actions.extend(['set_easy', 'hidden'])
            else:
                # Incorrect answer: raise difficulty and keep visible
                db_manager.update_word_difficulty(current_user.user_id, word_id, 'hard')
                db_manager.unhide_word_for_user(current_user.user_id, word_id)
                actions.extend(['set_hard', 'unhidden'])
        except Exception:
            # Don't fail the review if adjustments encounter issues
            pass
    
    if success:
        return JSONResponse(content={'success': True, 'message': message, 'actions': actions, 'correct': correct})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.post('/api/words/{word_id}/know')
async def mark_word_known(word_id: int, current_user: User = Depends(require_authentication)):
    """Mark a word as known: set difficulty to easy and hide it."""
    ok_diff, msg_diff = db_manager.update_word_difficulty(current_user.user_id, word_id, 'easy')
    ok_hide, msg_hide = db_manager.hide_word_for_user(current_user.user_id, word_id)

    if ok_diff and ok_hide:
        return JSONResponse(content={'success': True, 'message': 'Marked as known (easy) and hidden'})

    errors = []
    if not ok_diff and msg_diff:
        errors.append(msg_diff)
    if not ok_hide and msg_hide:
        errors.append(msg_hide)
    raise HTTPException(status_code=400, detail='; '.join(errors) or 'Failed to mark as known')

@app.put('/api/words/{word_id}/difficulty')
async def update_word_difficulty_api(word_id: int, request: Request, current_user: User = Depends(require_authentication)):
    """Update the difficulty level of a word for the user."""
    try:
        json_data = await request.json()
    except:
        raise HTTPException(status_code=400, detail='Missing "difficulty" parameter')
    
    if 'difficulty' not in json_data:
        raise HTTPException(status_code=400, detail='Missing "difficulty" parameter')
    
    difficulty = json_data['difficulty']
    if difficulty not in ['easy', 'medium', 'hard']:
        raise HTTPException(status_code=400, detail='Invalid difficulty level')
    
    success, message = db_manager.update_word_difficulty(current_user.user_id, word_id, difficulty)
    
    if success:
        return JSONResponse(content={'success': True, 'message': message})
    else:
        raise HTTPException(status_code=400, detail=message)

@app.get('/api/user/liked-words')
async def get_user_liked_words(current_user: User = Depends(require_authentication)):
    """Get list of word IDs that the user has liked."""
    liked_word_ids = db_manager.get_user_word_likes(current_user.user_id)
    return JSONResponse(content={'liked_words': liked_word_ids})

@app.get('/api/most-liked-words')
async def get_most_liked_words(current_user: User = Depends(require_authentication), limit: int = Query(50)):
    """Get the most liked words across all users."""
    words = db_manager.get_most_liked_words(limit)
    return JSONResponse(content={'words': words})

@app.get('/api/user/recent-words')
async def get_recent_words(current_user: User = Depends(require_authentication), days: int = Query(7)):
    """API endpoint to get recently studied words."""
    recent_words = db_manager.get_recent_words(current_user.user_id, days)
    return JSONResponse(content={'success': True, 'recent_words': recent_words})

# Search and AI routes
@app.get('/api/search/word/{word}')
async def search_word(word: str, current_user: User = Depends(require_authentication)):
    """API endpoint to search for word definition using OpenAI LLM."""
    try:
        # Use OpenAI to search for word definition
        result = search_word_with_openai(word)
        
        # Check if there was an error
        if result.get("error"):
            return JSONResponse(content={
                'success': False, 
                'error': result["error"]
            }, status_code=400)
        
        # If successful, return the word data
        if result.get("word"):
            word_data = {
                'word': result["word"],
                'type': result["type"] or 'unknown',
                'definition': result["definition"] or 'No definition available',
                'example': result["example"] or f"The word '{word}' can be used in a sentence."
            }
            
            return JSONResponse(content={
                'success': True, 
                'data': word_data
            })
        else:
            return JSONResponse(content={
                'success': False, 
                'error': 'Word not found or invalid'
            }, status_code=404)
            
    except Exception as e:
        return JSONResponse(content={
            'success': False, 
            'error': 'An unexpected error occurred while searching'
        }, status_code=500)

@app.get('/ai-learning', response_class=HTMLResponse)
async def ai_learning_page(request: Request, current_user: User = Depends(require_authentication)):
    """AI Learning page."""
    # Get user analysis data for the template
    analysis = db_manager.analyze_user_learning_patterns(current_user.user_id)
    is_user_admin = is_admin_sync()
    
    context = get_template_context(request, current_user)
    context.update({
        "user": current_user,
        "analysis": analysis,
        "is_admin": is_user_admin
    })
    
    return templates.TemplateResponse("ai_learning.html", context)

@app.get('/api/ai/suggest-word')
async def ai_suggest_word(current_user: User = Depends(require_authentication)):
    """API endpoint to get AI word suggestion."""
    try:
        suggestion = get_ai_word_suggestion_based_on_patterns(current_user.user_id)
        return JSONResponse(content={
            'success': True,
            'suggestion': suggestion
        })
    except Exception as e:
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)

@app.post('/api/ai/feedback')
async def ai_feedback(data: AIFeedbackRequest, current_user: User = Depends(require_authentication)):
    """API endpoint to submit AI feedback."""
    try:
        # Store feedback in database (if method exists)
        # This would need to be implemented based on the actual database schema
        return JSONResponse(content={
            'success': True,
            'message': 'Feedback recorded successfully'
        })
    except Exception as e:
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)

# AI Learning Session routes
@app.post('/api/ai/session/start')
async def start_ai_learning_session(request: Request, current_user: User = Depends(require_authentication)):
    """Start a new AI learning session."""
    try:
        json_data = await request.json()
        target_words = json_data.get('target_words', 10)
        
        if target_words < 5 or target_words > 50:
            raise HTTPException(status_code=400, detail='Target words must be between 5 and 50')
        
        session_id = db_manager.create_ai_learning_session(current_user.user_id, target_words)
        
        if session_id:
            return JSONResponse(content={'success': True, 'session_id': session_id})
        else:
            raise HTTPException(status_code=500, detail='Failed to create session')
    except Exception as e:
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)

@app.get('/api/ai/session/{session_id}/word')
async def get_next_session_word(session_id: int, current_user: User = Depends(require_authentication)):
    """Get next word for AI learning session."""
    try:
        # Get session details
        session = db_manager.get_ai_learning_session(session_id)
        if not session:
            print(f"Debug: Session {session_id} not found")
            raise HTTPException(status_code=404, detail='Session not found')
        
        if session['user_id'] != current_user.user_id:
            print(f"Debug: Session {session_id} belongs to user {session['user_id']}, not {current_user.user_id}")
            raise HTTPException(status_code=404, detail='Session not found')
        
        if session['is_completed']:
            print(f"Debug: Session {session_id} is already completed")
            raise HTTPException(status_code=400, detail='Session already completed')
        
        # Determine current difficulty based on recent performance
        current_difficulty = session.get('current_difficulty', 'medium')
        print(f"Debug: Current difficulty for session {session_id}: {current_difficulty}")
        
        # Use smart word selection for AI learning sessions
        available_words = db_manager.get_smart_words_for_ai_learning(current_user.user_id, limit=5)
        
        if not available_words:
            print(f"Debug: No suitable words found for user {current_user.user_id}")
            raise HTTPException(status_code=404, detail='No vocabulary words found. Please add some words to your vocabulary first.')
        
        # Smart selection already prioritizes words, so pick the first one
        selected_word = available_words[0]
        print(f"Debug: Smart-selected word: {selected_word['word']} (priority score: {selected_word.get('priority_score', 'N/A')})")
        
        # Determine difficulty from the word's metadata or default
        word_difficulty = selected_word.get('difficulty', current_difficulty)
        
        # Add word to session
        word_order = session['words_completed'] + 1
        success = db_manager.add_word_to_ai_session(
            session_id, 
            selected_word['word'],
            base_word_id=selected_word['id'],
            difficulty_level=word_difficulty,
            word_order=word_order
        )
        
        if not success:
            print(f"Debug: Failed to add word to session {session_id}")
            raise HTTPException(status_code=500, detail='Failed to add word to session')
        
        return JSONResponse(content={
            'success': True,
            'word': {
                'word': selected_word['word'],
                'type': selected_word['word_type'],
                'definition': selected_word['definition'],
                'example': selected_word['example'],
                'difficulty': current_difficulty
            },
            'session_progress': {
                'current': session['words_completed'] + 1,
                'total': session['target_words'],
                'correct': session['words_correct']
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting next session word: {e}")
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)

@app.post('/api/ai/session/{session_id}/response')
async def submit_session_response(
    session_id: int, 
    request: Request,
    current_user: User = Depends(require_authentication)
):
    """Submit user response for a word in AI learning session."""
    try:
        json_data = await request.json()
        word = json_data.get('word')
        response = json_data.get('response')  # 'know' or 'learn'
        response_time_ms = json_data.get('response_time_ms', 0)
        
        if not word or not response:
            raise HTTPException(status_code=400, detail='Missing required fields')
        
        # Validate session ownership
        session = db_manager.get_ai_learning_session(session_id)
        if not session or session['user_id'] != current_user.user_id:
            raise HTTPException(status_code=404, detail='Session not found')
        
        is_correct = response == 'know'
        
        # Record the response
        success = db_manager.record_ai_session_response(
            session_id, word, response, is_correct, response_time_ms
        )
        
        if not success:
            raise HTTPException(status_code=500, detail='Failed to record response')
        
        # Update session progress
        words_completed = session['words_completed'] + 1
        words_correct = session['words_correct'] + (1 if is_correct else 0)
        
        # Adjust difficulty based on recent performance
        if words_completed >= 3:  # Only adjust after a few words
            recent_accuracy = words_correct / words_completed
            current_difficulty = session.get('current_difficulty', 'medium')
            
            if recent_accuracy >= 0.8 and current_difficulty != 'hard':
                new_difficulty = 'hard' if current_difficulty == 'medium' else 'medium'
            elif recent_accuracy <= 0.3 and current_difficulty != 'easy':
                new_difficulty = 'easy' if current_difficulty == 'medium' else 'medium'
            else:
                new_difficulty = current_difficulty
        else:
            new_difficulty = session.get('current_difficulty', 'medium')
        
        # Update session
        db_manager.update_ai_learning_session_progress(
            session_id, words_completed, words_correct, new_difficulty
        )
        
        # Check if session is complete
        session_complete = words_completed >= session['target_words']
        
        return JSONResponse(content={
            'success': True,
            'session_complete': session_complete,
            'progress': {
                'current': words_completed,
                'total': session['target_words'],
                'correct': words_correct,
                'accuracy': round((words_correct / words_completed * 100) if words_completed > 0 else 0, 1)
            },
            'difficulty_adjusted': new_difficulty != session.get('current_difficulty', 'medium'),
            'new_difficulty': new_difficulty
        })
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing session response: {e}")
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)

@app.post('/api/ai/session/{session_id}/complete')
async def complete_ai_learning_session(
    session_id: int,
    request: Request,
    current_user: User = Depends(require_authentication)
):
    """Complete an AI learning session."""
    try:
        json_data = await request.json()
        total_time_seconds = json_data.get('total_time_seconds', 0)
        
        # Validate session ownership
        session = db_manager.get_ai_learning_session(session_id)
        if not session or session['user_id'] != current_user.user_id:
            raise HTTPException(status_code=404, detail='Session not found')
        
        # Complete the session
        success = db_manager.complete_ai_learning_session(session_id, total_time_seconds)
        
        if not success:
            raise HTTPException(status_code=500, detail='Failed to complete session')
        
        # Get session summary
        summary = db_manager.get_ai_session_summary(session_id)
        
        if summary:
            return JSONResponse(content={'success': True, 'summary': summary})
        else:
            raise HTTPException(status_code=500, detail='Failed to generate summary')
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error completing session: {e}")
        return JSONResponse(content={
            'success': False,
            'error': str(e)
        }, status_code=500)

# Management and profile routes
@app.get('/manage', response_class=HTMLResponse)
async def manage_page(request: Request, current_user: User = Depends(require_authentication)):
    """Management page."""
    # Get user's words for the template
    words = db_manager.get_user_words(current_user.user_id)
    is_user_admin = is_admin_sync()
    
    context = get_template_context(request, current_user)
    context.update({
        "words": words,
        "total_words": len(words),
        "is_admin": is_user_admin
    })
    
    return templates.TemplateResponse("manage.html", context)

@app.get('/profile', response_class=HTMLResponse)
async def profile_page(request: Request, current_user: User = Depends(require_authentication)):
    """Profile page."""
    return templates.TemplateResponse("profile.html", get_template_context(request, current_user))

@app.get('/api/user/profile')
async def get_user_profile(current_user: User = Depends(require_authentication)):
    """API endpoint to get user profile."""
    return JSONResponse(content={
        'success': True,
        'user': current_user.to_dict()
    })

# Health and info routes
@app.get('/health')
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })

@app.get('/api/info')
async def app_info():
    """API endpoint to get application information."""
    return JSONResponse(content={
        'success': True,
        'app_name': 'Vocabulary Flashcard Application',
        'version': '2.0.0',
        'framework': 'FastAPI',
        'description': 'A web application for managing vocabulary flashcards with multi-user support'
    })

# Admin routes
@app.get('/admin', response_class=HTMLResponse)
async def admin_page(request: Request, current_user: User = Depends(require_admin)):
    """Admin page."""
    # Get system statistics and users for the template
    stats = db_manager.get_system_stats()
    users = db_manager.get_all_users()
    
    context = get_template_context(request, current_user)
    context.update({
        "stats": stats,
        "users": users
    })
    
    return templates.TemplateResponse("admin.html", context)

# Startup function
def initialize_app():
    """Initialize the application with database and load initial data if needed."""
    # Load initial data if database is empty
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM vocabulary')
        word_count = cursor.fetchone()['count']
    
    if word_count == 0:
        print("Database is empty. Checking for seed data...")
        if os.path.exists(text_file):
            print(f"Seed data found at: {text_file}")
            print("To load seed data, an admin user needs to be created first.")
        else:
            print(f"No seed data found at: {text_file}")
    else:
        print(f"📊 Database contains {word_count} words")
    
    print("🚀 Vocabulary Flashcard Web Application (FastAPI) initialized")
    print("🌐 Access the application at: http://localhost:5001")
    print("🔐 Login required - register a new account or use existing credentials")
    print("🔧 Management interface at: http://localhost:5001/manage")
    print("🤖 AI Learning feature at: http://localhost:5001/ai-learning")

# Run initialization
initialize_app()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("fastapi_web_flashcards:app", host='0.0.0.0', port=5001, reload=True)