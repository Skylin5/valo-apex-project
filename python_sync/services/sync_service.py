"""Orchestration de la synchronisation d'un joueur et des participants de ses matchs."""

from collections import Counter

from database import get_db_conn
from henrikdev import HenrikError, fetch_matches, fetch_mmr_history
from repositories.matches import insert_match_perf
from repositories.mmr import insert_missing_mmr_rows
from repositories.players import upsert_player
from repositories.weapons import upsert_weapon_kills
from services.match_parser import (
    RANG_DEBUTANT,
    build_match_row,
    compute_round_stats,
    extract_weapon_kills,
    match_context,
    rank_label,
    riot_id_of,
)
from services.mmr_parser import mmr_rows

# Valeurs utilisées si le joueur cible n'apparaît dans aucun match récupéré
DEFAULT_LEVEL = 1


def _find_target(matches: list[dict], riot_id: str) -> dict | None:
    """Retourne l'entrée du joueur cible dans le dernier match où il apparaît."""
    for m in matches:
        for p in m.get("players", []):
            if riot_id_of(p).lower() == riot_id.lower():
                return p
    return None


def sync_player_and_lobby(
    region: str,
    pseudo: str,
    tag: str,
    platform: str = "pc",
    mode: str | None = "competitive",
    size: int = 10,
) -> dict:
    """Ingère les matchs récents du joueur, de tous les participants, leurs kills par arme
    et l'historique MMR du joueur cible.

    Lève HenrikError si l'API ne répond pas correctement pour les matchs. Un échec de
    l'historique MMR n'interrompt pas la synchro : il est signalé dans la réponse.
    """
    riot_id = f"{pseudo}#{tag}"
    matches = fetch_matches(region, pseudo, tag, size=size, platform=platform, mode=mode)

    mmr_warning = None
    try:
        mmr_history = fetch_mmr_history(region, pseudo, tag, platform=platform)
    except HenrikError as exc:
        mmr_history, mmr_warning = [], exc.message

    nb_perfs = 0
    lobby_ids: dict[str, str] = {}  # riot_id en minuscules -> riot_id d'origine
    weapon_kills: dict[str, Counter] = {}

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        target = _find_target(matches, riot_id)
        if target:
            level, rank = target.get("account_level", DEFAULT_LEVEL), rank_label((target.get("tier") or {}).get("id"))
        else:
            level, rank = DEFAULT_LEVEL, RANG_DEBUTANT
        upsert_player(cur, riot_id, level, rank, profile_type="MON_COMPTE")

        for m in matches:
            ctx = match_context(m)
            round_stats = compute_round_stats(m)

            for p in m.get("players", []):
                p_riot_id = riot_id_of(p)
                lobby_ids[p_riot_id.lower()] = p_riot_id
                upsert_player(
                    cur, p_riot_id, p.get("account_level", DEFAULT_LEVEL),
                    rank_label((p.get("tier") or {}).get("id")),
                )
                if insert_match_perf(cur, build_match_row(ctx, p, round_stats)):
                    nb_perfs += 1

            for player_key, kills in extract_weapon_kills(m).items():
                weapon_kills.setdefault(player_key, Counter()).update(kills)

        nb_armes_cible = 0
        for player_key, kills in weapon_kills.items():
            if player_key not in lobby_ids:
                continue
            nb = upsert_weapon_kills(cur, lobby_ids[player_key], kills)
            if player_key == riot_id.lower():
                nb_armes_cible = nb

        nb_mmr = insert_missing_mmr_rows(cur, mmr_rows(lobby_ids.get(riot_id.lower(), riot_id), mmr_history))

        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {
        "statut": "OK",
        "joueur_cible": riot_id,
        "armes_synchronisees": nb_armes_cible,
        "joueurs_avec_armes": len(weapon_kills),
        "matchs_analyses": len(matches),
        "nouvelles_performances_joueurs_inserees": nb_perfs,
        "entrees_mmr_inserees": nb_mmr,
        "avertissement_mmr": mmr_warning,
    }
