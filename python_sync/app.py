"""Point d'entrée FastAPI — Valorant Tracker & Oracle ML Sync API.

Ce fichier ne contient que l'initialisation de l'application et l'enregistrement
des routeurs. Toute la logique métier est dans les sous-modules :
  - config.py       : variables d'environnement et constantes
  - database.py     : pool de connexions Oracle
  - henrikdev.py    : client API HenrikDev
  - youtube.py      : recherche YouTube (scraping léger)
  - routes/sync.py  : endpoint /sync/{region}/{pseudo}/{tag}
  - routes/coach.py : endpoint /coach/ask
  - services/       : logique de synchronisation et parsing des matchs
  - repositories/   : requêtes SQL Oracle
"""

from fastapi import FastAPI

from routes.sync import router as sync_router
from routes.coach import router as coach_router

app = FastAPI(
    title="Valorant Tracker & Oracle ML Sync API",
    description="Pipeline d'ingestion de matchs Valorant et coaching IA basé sur Oracle ML.",
    version="1.0.0",
)

app.include_router(sync_router)
app.include_router(coach_router)


@app.get("/health")
def health_check():
    """Endpoint de vérification de santé du service."""
    return {"status": "ok"}