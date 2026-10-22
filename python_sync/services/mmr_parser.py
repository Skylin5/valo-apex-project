"""Parsing de l'historique MMR HenrikDev v2 : fonctions pures."""

from services.match_parser import parse_started_at


def mmr_rows(riot_id: str, history: list[dict]) -> list[dict]:
    """Transforme les entrées `history` en paramètres SQL pour valo_mmr_history.

    `variation` vient de `last_change` : gain ou perte de RR du match (le sens exact
    de `rr` et `last_change` n'est pas détaillé par la doc, `last_change` est le plus probable).
    """
    rows = []
    for entry in history:
        match_id = entry.get("match_id")
        if not match_id:
            continue
        tier = entry.get("tier") or {}
        rows.append({
            "r_id": riot_id,
            "m_id": match_id,
            "date_match": parse_started_at(entry.get("date")),
            "carte": ((entry.get("map") or {}).get("name") or "")[:40] or None,
            "saison": ((entry.get("season") or {}).get("short") or "")[:10] or None,
            "tier_id": tier.get("id"),
            "tier_nom": (tier.get("name") or "")[:30] or None,
            "elo": entry.get("elo"),
            "rr": entry.get("rr"),
            "variation": entry.get("last_change"),
        })
    return rows
