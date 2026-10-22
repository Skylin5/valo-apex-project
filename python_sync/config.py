"""Configuration centralisée — variables d'environnement et constantes métier."""

import os

# ---------------------------------------------------------------------------
# Connexion Oracle
# ---------------------------------------------------------------------------
DB_USER = os.getenv("DB_USER", "valo_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "ValoPassword123")
DB_DSN = os.getenv("DB_DSN", "oracle-db:1521/FREEPDB1")

# ---------------------------------------------------------------------------
# API externe
# ---------------------------------------------------------------------------
HENRIKDEV_API_KEY = os.getenv("HENRIKDEV_API_KEY", "").strip()

# ---------------------------------------------------------------------------
# Mapping Agent → Rôle
# ---------------------------------------------------------------------------
ROLES_AGENTS: dict[str, str] = {
    # Sentinels
    "Sage": "Sentinel", "Chamber": "Sentinel", "Cypher": "Sentinel",
    "Killjoy": "Sentinel", "Deadlock": "Sentinel", "Vyse": "Sentinel",
    # Duelists
    "Jett": "Duelist", "Reyna": "Duelist", "Raze": "Duelist",
    "Phoenix": "Duelist", "Neon": "Duelist", "Iso": "Duelist", "Yoru": "Duelist",
    # Controllers
    "Omen": "Controller", "Brimstone": "Controller", "Viper": "Controller",
    "Astra": "Controller", "Clove": "Controller", "Harbor": "Controller",
    # Initiators
    "Sova": "Initiator", "Skye": "Initiator", "Fade": "Initiator",
    "Gekko": "Initiator", "Breach": "Initiator", "KAY/O": "Initiator",
}
