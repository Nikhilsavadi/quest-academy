FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for Pillow / psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Static dirs (Railway volume mounts overlay these at runtime)
RUN mkdir -p /app/static/matrices /app/static/scans

# Make the startup script executable
RUN chmod +x start.sh

ENV PORT=8000
EXPOSE 8000

# start.sh runs: alembic upgrade head -> seed -> uvicorn
CMD ["./start.sh"]
