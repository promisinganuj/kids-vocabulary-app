#!/bin/sh
set -e

echo "⏳ Running database migrations..."
python -c "
import sys, os

db_url = os.environ.get('DATABASE_URL', '')
if not db_url:
    print('❌ DATABASE_URL is not set')
    sys.exit(1)

# Run Alembic migrations for PostgreSQL
print('🐘 Running Alembic migrations...')
import subprocess
result = subprocess.run(
    ['python', '-m', 'alembic', 'upgrade', 'head'],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f'⚠️  Alembic migration output: {result.stdout}')
    print(f'⚠️  Alembic migration errors: {result.stderr}')
    # If alembic fails (e.g. fresh DB), fall back to create_all + stamp
    print('📋 Falling back to create_all + alembic stamp...')
    from database_manager import DatabaseManager
    db = DatabaseManager()
    result2 = subprocess.run(
        ['python', '-m', 'alembic', 'stamp', 'head'],
        capture_output=True, text=True
    )
    if result2.returncode == 0:
        print('✅ Database tables created and Alembic stamped at head')
    else:
        print(f'❌ Alembic stamp failed: {result2.stderr}')
        sys.exit(1)
else:
    print(f'{result.stdout.strip()}')
    print('✅ Alembic migrations complete')
"

# Export so gunicorn worker(s) skip re-init on import
export _DB_INITIALIZED=1

# Use WORKERS env var if set (from Azure/Bicep), default to 1
WORKERS="${WORKERS:-1}"

echo "🚀 Starting gunicorn with $WORKERS worker(s)..."
exec gunicorn fastapi_web_flashcards:app \
    --bind 0.0.0.0:5001 \
    --workers "$WORKERS" \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
