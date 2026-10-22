"""Service HenrikDev : matchs v4 et historique MMR v2.

Chaque appel coûte 1 au quota de la clé, plus 1 par match absent du cache serveur
(voir https://docs.henrikdev.xyz/general/rate-limiting). D'où le cache local court,
l'attente sur les réponses 429 et la lecture de X-RateLimit-Remaining.
"""

import time
import urllib.parse

import requests

from config import HENRIKDEV_API_KEY

BASE_URL = "https://api.henrikdev.xyz/valorant"
MAX_MATCHES_PER_CALL = 10  # plafond imposé par l'API sur `size`
CACHE_TTL_SECONDS = 60
MAX_RETRIES_ON_429 = 2
MAX_WAIT_SECONDS = 15

_cache: dict[str, tuple[float, dict]] = {}


class HenrikError(Exception):
    """Erreur d'appel à l'API HenrikDev. `status` est le code HTTP à renvoyer à l'appelant."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _api_key_missing() -> bool:
    return not HENRIKDEV_API_KEY or HENRIKDEV_API_KEY.startswith("HDEV-REMPLACE")


def _retry_delay(resp: requests.Response) -> float:
    """Délai d'attente demandé par l'API (Retry-After, sinon X-RateLimit-Reset), borné."""
    for header in ("Retry-After", "X-RateLimit-Reset"):
        try:
            return min(float(resp.headers[header]), MAX_WAIT_SECONDS)
        except (KeyError, ValueError):
            continue
    return 1.0


def _get(path: str, params: dict | None = None):
    """GET authentifié avec cache court, attente sur 429 et erreurs typées."""
    if _api_key_missing():
        raise HenrikError(503, "Clé API HenrikDev absente : renseigner HENRIKDEV_API_KEY.")

    clean_params = {k: v for k, v in (params or {}).items() if v is not None}
    cache_key = f"{path}?{urllib.parse.urlencode(sorted(clean_params.items()))}"
    cached = _cache.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    headers = {"Authorization": HENRIKDEV_API_KEY}
    resp = None
    for attempt in range(MAX_RETRIES_ON_429 + 1):
        try:
            resp = requests.get(f"{BASE_URL}{path}", params=clean_params, headers=headers, timeout=15)
        except requests.RequestException as exc:
            raise HenrikError(502, f"API HenrikDev injoignable : {exc}") from exc

        if resp.status_code != 429:
            break
        if attempt < MAX_RETRIES_ON_429:
            time.sleep(_retry_delay(resp))

    if resp.status_code == 429:
        raise HenrikError(429, "Limite de requêtes HenrikDev atteinte, réessayer plus tard.")
    if resp.status_code == 404:
        raise HenrikError(404, "Compte ou ressource introuvable.")
    if resp.status_code >= 400:
        raise HenrikError(resp.status_code, f"Erreur HenrikDev ({resp.status_code}).")

    data = resp.json().get("data")
    _cache[cache_key] = (time.monotonic() + CACHE_TTL_SECONDS, data)

    # Ralentit proactivement quand le quota est épuisé pour ne pas enchaîner des 429
    if resp.headers.get("X-RateLimit-Remaining") == "0":
        time.sleep(_retry_delay(resp))
    return data


def fetch_matches(
    region: str,
    pseudo: str,
    tag: str,
    size: int = MAX_MATCHES_PER_CALL,
    platform: str = "pc",
    mode: str | None = None,
    map_name: str | None = None,
) -> list[dict]:
    """Retourne les matchs récents (détail complet : rounds, kills, joueurs) via v4/matches."""
    path = f"/v4/matches/{region}/{platform}/{urllib.parse.quote(pseudo)}/{urllib.parse.quote(tag)}"
    return _get(path, {"size": min(size, MAX_MATCHES_PER_CALL), "mode": mode, "map": map_name}) or []


def fetch_mmr_history(region: str, pseudo: str, tag: str, platform: str = "pc") -> list[dict]:
    """Retourne l'historique MMR (rang, elo, RR gagnés ou perdus par match) via v2/mmr-history."""
    path = f"/v2/mmr-history/{region}/{platform}/{urllib.parse.quote(pseudo)}/{urllib.parse.quote(tag)}"
    return (_get(path) or {}).get("history", [])
