# Utilisation d'une image Python légère mais complète
FROM python:3.10-slim

# Configuration des variables d'environnement pour Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Installation des dépendances système nécessaires
# Chromium et Chromium-driver sont requis pour Selenium en mode headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    chromium \
    chromium-driver \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances (racine du projet pour récupérer requirements.txt)
# On suppose que le Dockerfile est dans ./backend/ et qu'on build depuis la racine
COPY requirements.txt .

# Installation des dépendances Python
# Ajout des librairies backend spécifiques
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg2-binary celery[redis] pydantic-settings python-multipart httpx

# Copie du code source
# On copie tout le dossier backend dans /app
COPY backend/ .
# On copie aussi les scripts sources (src et daily) car le backend doit les exécuter
COPY src/ /app/src/
COPY daily/ /app/daily/

# Création des dossiers de données pour la persistance
RUN mkdir -p /app/data/raw /app/data/processed /app/data/daily /app/models

# Exposition du port API
EXPOSE 8000

# Commande par défaut (sera surchargée par docker-compose pour le worker)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]