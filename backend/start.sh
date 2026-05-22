#!/bin/sh
set -e
cd /app

echo "=== Running Alembic migrations ==="
alembic upgrade head

echo "=== Running seed ==="
python -c "from seed import seed; seed()"

echo "=== Starting uvicorn ==="
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
