#!/bin/sh
set -e

echo "⏳ Running database initialization..."
python -c "
import time, sys
from database_manager import DatabaseManager
# Retry up to 3 times in case of transient SQLite lock (e.g. leftover WAL)
for attempt in range(3):
    try:
        db = DatabaseManager()
        print('✅ Database init complete')
        break
    except Exception as e:
        if attempt < 2:
            print(f'⚠️  DB init attempt {attempt+1} failed: {e}, retrying in 2s...')
            time.sleep(2)
        else:
            print(f'❌ DB init failed after 3 attempts: {e}')
            sys.exit(1)
"

# Export so gunicorn worker(s) skip re-init on import
export _DB_INITIALIZED=1

echo "🚀 Starting gunicorn..."
exec gunicorn fastapi_web_flashcards:app \
    --bind 0.0.0.0:5001 \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
