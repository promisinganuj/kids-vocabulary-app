#!/bin/sh
set -e

echo "⏳ Running database initialization..."
python -c "
from database_manager import DatabaseManager
db = DatabaseManager()
print('✅ Database init complete')
"

# Export so forked gunicorn workers inherit it and skip re-init
export _DB_INITIALIZED=1

echo "🚀 Starting gunicorn..."
exec gunicorn fastapi_web_flashcards:app \
    --bind 0.0.0.0:5001 \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
