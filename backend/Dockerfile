FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    chromium \
    chromium-driver \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg2-binary celery[redis] pydantic-settings python-multipart httpx

# CORRECTION ICI : On copie dans des sous-dossiers explicites
COPY backend/ /app/backend/
COPY src/ /app/src/
COPY daily/ /app/daily/

RUN mkdir -p /app/data/raw /app/data/processed /app/data/daily /app/models

EXPOSE 8000

# CORRECTION ICI : On lance via le module backend.main
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]