# Vocabulary Flashcard Application - Startup Scripts

This vocabulary flashcard application now supports both Flask and FastAPI backends. Choose the version that best suits your needs.

## Available Startup Scripts

### 🚀 Quick Start (Recommended)
```bash
./start_app.sh
```
- **Default**: Runs FastAPI version (recommended)
- **Features**: Modern async framework, better performance, automatic API documentation
- **URL**: http://localhost:5001
- **API Docs**: http://localhost:5001/docs (automatic OpenAPI documentation)

### ⚡ FastAPI Version (Modern)
```bash
./fastapi_start_app.sh
```
- **Framework**: FastAPI with Uvicorn
- **Port**: 5001
- **Features**: 
  - Async/await support
  - Automatic API documentation
  - Better performance
  - Modern Python type hints
  - Enhanced error handling

### 🐍 Flask Version (Legacy)
```bash
./flask_start_app.sh
```
- **Framework**: Flask with built-in server
- **Port**: 5000  
- **Features**:
  - Traditional Python web framework
  - Proven stability
  - Original implementation
  - Synchronous operation

## Feature Comparison

| Feature | FastAPI | Flask |
|---------|---------|--------|
| **Performance** | ⚡ High (async) | 🟡 Standard |
| **API Documentation** | ✅ Auto-generated | ❌ Manual |
| **Type Safety** | ✅ Full support | 🟡 Limited |
| **Modern Python** | ✅ 3.7+ features | 🟡 Traditional |
| **Async Support** | ✅ Native | ❌ No |
| **Memory Usage** | ✅ Lower | 🟡 Higher |
| **Startup Time** | ✅ Faster | 🟡 Slower |

## Migration Status

The FastAPI version includes all features from the Flask version:

- ✅ **User Authentication** - Complete multi-user support
- ✅ **Vocabulary Management** - Add, edit, delete words  
- ✅ **Word Interactions** - Like, hide, review, difficulty settings
- ✅ **AI-Powered Search** - Azure OpenAI integration for word definitions
- ✅ **AI Learning Sessions** - Adaptive learning with session tracking
- ✅ **Admin Interface** - User and vocabulary management
- ✅ **Recent Words** - Activity tracking and analytics
- ✅ **Profile Management** - User preferences and settings

## Requirements

Both versions require:
- Python 3.8+
- Virtual environment (`.venv`) activated
- SQLite database
- Environment variables for Azure OpenAI (optional for AI features)

## Environment Variables (Optional)

For AI-powered features, set these environment variables:
```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="your-endpoint"
export AZURE_OPENAI_DEPLOYMENT="your-deployment"
export AZURE_OPENAI_API_VERSION="2024-02-15-preview"
```

## Database

Both versions share the same SQLite database (`data/vocabulary.db`), so you can switch between them without losing data.

## Recommendation

**Use FastAPI version** (`./fastapi_start_app.sh`) for:
- New deployments
- Better performance needs
- Modern development practices
- API documentation requirements

**Use Flask version** (`./flask_start_app.sh`) for:
- Legacy compatibility
- Testing comparisons
- Familiarity with Flask ecosystem

---

The FastAPI migration maintains 100% feature parity with the original Flask application while providing improved performance and modern development benefits.