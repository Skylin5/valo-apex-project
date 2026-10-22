"""Utilitaires partagés pour les scripts du dossier data/.

Fournit une fonction de connexion Oracle centralisée qui lit les
credentials depuis les variables d'environnement (avec fallback local).
"""

import os
import oracledb


def get_db_connection() -> oracledb.Connection:
    """Crée et retourne une connexion Oracle à partir des variables d'env."""
    return oracledb.connect(
        user=os.getenv("DB_USER", "valo_app"),
        password=os.getenv("DB_PASSWORD", "ValoPassword123"),
        dsn=os.getenv("DB_DSN", "localhost:1521/FREEPDB1"),
    )
