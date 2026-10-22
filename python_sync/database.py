"""Gestion du pool de connexions Oracle."""

import oracledb

from config import DB_USER, DB_PASSWORD, DB_DSN

# ---------------------------------------------------------------------------
# Pool de connexions (réutilisé par tous les modules)
# ---------------------------------------------------------------------------
_pool: oracledb.ConnectionPool | None = None


def get_pool() -> oracledb.ConnectionPool:
    """Retourne le pool singleton (créé au premier appel)."""
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            min=1,
            max=5,
            increment=1,
        )
    return _pool


def get_db_conn() -> oracledb.Connection:
    """Acquiert une connexion depuis le pool."""
    return get_pool().acquire()
