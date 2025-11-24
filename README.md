# NBA Betting Dashboard

Système complet de prédiction et d'analyse de paris NBA avec architecture microservices.

## Architecture

```
NBA_Betting_Dashboard/
├── docker-compose.yml        # Orchestration (DB, Redis, API, Worker, Front)
├── requirements.txt          # Dépendances Python
│
├── backend/                  # API FastAPI + Celery
│   ├── main.py              # Point d'entrée FastAPI
│   ├── celery_worker.py     # Tâches asynchrones
│   ├── config.py            # Configuration
│   ├── database.py          # SQLAlchemy
│   ├── models.py            # Tables PostgreSQL
│   ├── schemas.py           # Modèles Pydantic
│   └── routers/             # Endpoints API
│
├── frontend/                # Dashboard React
│
├── data/                    # Données NBA
│   ├── raw/                 # Historique brut
│   ├── processed/           # Features calculées
│   └── daily/               # Cotes & prédictions du jour
│
├── models/                  # Modèles XGBoost
│
├── src/                     # Moteur de calcul
│   ├── data_fetcher.py     # Récupération données NBA
│   ├── data_processor.py   # Feature engineering
│   └── train_xgb.py        # Entraînement modèle
│
└── daily/                   # Scripts quotidiens
    ├── scraper_fdj.py      # Scraping cotes
    ├── daily_predict.py    # Génération prédictions
    └── update_model.py     # Mise à jour modèle
```

## Installation

### Avec Docker (Recommandé)

```bash
# Lancer tous les services
docker-compose up -d

# Accéder au dashboard
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Sans Docker

```bash
# Installer les dépendances Python
pip install -r requirements.txt

# Lancer l'API
cd backend
uvicorn main:app --reload

# Lancer le worker Celery
celery -A celery_worker worker --loglevel=info

# Lancer le frontend
cd frontend
npm install
npm start
```

## Configuration

Copier `.env.example` vers `.env` et ajuster les variables d'environnement.

## Workflow

1. **Entraînement initial** (une fois)
   ```bash
   python src/data_fetcher.py      # Récupération historique
   python src/data_processor.py    # Calcul features
   python src/train_xgb.py         # Entraînement modèle
   ```

2. **Utilisation quotidienne**
   ```bash
   python daily/scraper_fdj.py     # Scraper les cotes FDJ
   python daily/daily_predict.py   # Générer prédictions
   ```

3. **Dashboard**
   - Visualiser les prédictions du jour
   - Analyser les performances historiques
   - Gérer les paris

## Technologies

- **Backend**: FastAPI, Celery, SQLAlchemy
- **Frontend**: React, Recharts
- **Database**: PostgreSQL
- **Cache**: Redis
- **ML**: XGBoost, scikit-learn
- **Scraping**: Selenium
- **Data**: NBA API, pandas

## License

MIT
