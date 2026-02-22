# Vocabulary Flashcard Application - Startup Guide

## Quick Start

```bash
./start_app.sh
```

- **Framework**: FastAPI with Uvicorn
- **URL**: http://localhost:5001
- **API Docs**: http://localhost:5001/docs (automatic OpenAPI documentation)

## Features

- Async/await support for high performance
- Automatic API documentation (OpenAPI/Swagger)
- Python type hints with Pydantic validation
- Multi-user authentication and session management
- AI-powered vocabulary search via Azure OpenAI

## Requirements

- Python 3.8+
- Virtual environment (`.venv`) activated
- SQLite database (auto-created on first run)
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

The app uses SQLite (`data/vocabulary.db`) with auto-initialization on first run.
