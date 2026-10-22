"""Route /sync — synchronisation d'un joueur et de son lobby."""

from fastapi import APIRouter, HTTPException, Query

from henrikdev import MAX_MATCHES_PER_CALL, HenrikError
from services.sync_service import sync_player_and_lobby

router = APIRouter()


@router.get("/sync/{region}/{pseudo}/{tag}")
def sync_endpoint(
    region: str,
    pseudo: str,
    tag: str,
    playlist: str = "competitive",
    platform: str = Query("pc", pattern="^(pc|console)$"),
    size: int = Query(MAX_MATCHES_PER_CALL, ge=1, le=MAX_MATCHES_PER_CALL),
):
    """Synchronise un joueur et tous les participants de ses matchs récents.

    `playlist` filtre le mode de jeu (competitive, unrated...) ; `size` est plafonné à 10 par l'API.
    """
    try:
        return sync_player_and_lobby(region, pseudo, tag, platform=platform, mode=playlist, size=size)
    except HenrikError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
