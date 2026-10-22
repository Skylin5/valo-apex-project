"""Parsing d'un match HenrikDev v4 : fonctions pures, sans réseau ni base de données."""

from collections import Counter
from datetime import datetime, timezone

from config import ROLES_AGENTS

# Un kill est "tradé" si le tueur est abattu par un coéquipier de la victime dans ce délai
TRADE_WINDOW_MS = 5000

# Libellés de rang attendus par le modèle ML (voir init_db/01_schema_and_seed.sql)
RANG_DEBUTANT = "1 - Débutant (Niv 1-20)"
RANGS_PAR_PALIER = [
    (3, RANG_DEBUTANT),   # Unranked / non classé
    (6, "2 - Fer"),       # Iron 1-3  (tiers 3-5)
    (9, "3 - Bronze"),    # Bronze 1-3 (tiers 6-8)
    (12, "4 - Argent"),   # Silver 1-3 (tiers 9-11)
    (15, "5 - Or"),       # Gold 1-3 (tiers 12-14)
]
RANG_MAX = "6 - Platine"  # Platinum et au-dessus (comme dans le jeu d'entraînement)


def riot_id_of(player: dict) -> str:
    """Retourne le Riot ID `Nom#Tag` d'un joueur du lobby."""
    return f"{player['name']}#{player['tag']}"


def rank_label(tier_id: int | None) -> str:
    """Convertit l'id de rang Riot (0 à 27) en libellé du modèle ML."""
    if tier_id is None:
        return RANG_DEBUTANT
    for upper_bound, label in RANGS_PAR_PALIER:
        if tier_id < upper_bound:
            return label
    return RANG_MAX


def parse_started_at(value: str | None) -> datetime | None:
    """Date ISO 8601 -> datetime UTC sans fuseau (colonne TIMESTAMP), None si absente ou invalide."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def match_context(match: dict) -> dict:
    """Extrait les métadonnées communes à tous les joueurs d'un match."""
    meta = match["metadata"]
    queue = meta.get("queue") or {}
    rounds = match.get("rounds", [])
    return {
        "match_id": meta["match_id"],
        "carte": (meta.get("map") or {}).get("name") or "Unknown",
        "mode_jeu": (queue.get("name") or queue.get("mode_type") or queue.get("id") or "Unknown")[:30],
        "saison": ((meta.get("season") or {}).get("short") or "")[:10] or None,
        "date_match": parse_started_at(meta.get("started_at")),
        "nb_rounds": max(1, len(rounds)),
        # team_id est opaque : on joint toujours équipes et joueurs par cet identifiant
        "teams": {t["team_id"]: t for t in match.get("teams", [])},
    }


def extract_weapon_kills(match: dict) -> dict[str, Counter]:
    """Compte les kills par arme pour chaque joueur du match.

    Retourne {riot_id_minuscule: Counter({arme: nb_kills})}. Les kills sans arme
    (capacités, ultimes) sont ignorés. L'API ne fournit ni arme par dégât ni
    headshot par kill : on ne peut donc pas en déduire de précision par arme.
    """
    riot_by_puuid = {p["puuid"]: riot_id_of(p).lower() for p in match.get("players", [])}
    kills_by_player: dict[str, Counter] = {}

    for kill in match.get("kills", []):
        weapon = (kill.get("weapon") or {}).get("name")
        riot_id = riot_by_puuid.get((kill.get("killer") or {}).get("puuid"))
        if weapon and riot_id:
            kills_by_player.setdefault(riot_id, Counter())[weapon] += 1

    return kills_by_player


def _puuid(who: dict | None) -> str | None:
    """puuid d'un joueur d'un événement de kill (killer, victim, assistant)."""
    return (who or {}).get("puuid")


def compute_round_stats(match: dict) -> dict[str, dict]:
    """Calcule first bloods, aces, flawless et KAST de chaque joueur à partir des rounds et des kills.

    Retourne {puuid: {"first_bloods", "aces", "flawless_rounds", "kast_rounds"}}.
    - first blood : premier kill du round ;
    - ace : 5 kills du même joueur dans un round ;
    - flawless : round gagné par l'équipe du joueur sans aucun mort dans l'équipe ;
    - KAST : round où le joueur a fait un Kill, une Assist, a Survécu ou a été Tradé
      (son tueur est abattu par un coéquipier dans les TRADE_WINDOW_MS suivantes).
    """
    team_of = {p["puuid"]: p.get("team_id") for p in match.get("players", [])}
    result = {
        puuid: {"first_bloods": 0, "aces": 0, "flawless_rounds": 0, "kast_rounds": 0}
        for puuid in team_of
    }

    kills_by_round: dict[int, list[dict]] = {}
    for kill in match.get("kills", []):
        kills_by_round.setdefault(kill.get("round"), []).append(kill)

    for rnd in match.get("rounds", []):
        kills = sorted(
            kills_by_round.get(rnd.get("id"), []),
            key=lambda k: k.get("time_in_round_in_ms", 0),
        )
        if kills and _puuid(kills[0].get("killer")) in result:
            result[_puuid(kills[0]["killer"])]["first_bloods"] += 1

        kills_count = Counter(
            _puuid(k.get("killer")) for k in kills
            if _puuid(k.get("killer")) != _puuid(k.get("victim"))
        )
        for puuid, nb in kills_count.items():
            if nb >= 5 and puuid in result:
                result[puuid]["aces"] += 1

        dead = {_puuid(k.get("victim")) for k in kills}
        dead_by_team = Counter(team_of.get(p) for p in dead)
        assisted = {_puuid(a) for k in kills for a in k.get("assistants", [])}

        for puuid, team in team_of.items():
            if team == rnd.get("winning_team") and dead_by_team[team] == 0:
                result[puuid]["flawless_rounds"] += 1

            got_kill = any(
                _puuid(k.get("killer")) == puuid and team_of.get(_puuid(k.get("victim"))) != team
                for k in kills
            )
            survived = puuid not in dead
            traded = False
            if not survived:
                death = next(k for k in kills if _puuid(k.get("victim")) == puuid)
                killer = _puuid(death.get("killer"))
                traded = any(
                    _puuid(k.get("victim")) == killer
                    and team_of.get(_puuid(k.get("killer"))) == team
                    and 0 <= k.get("time_in_round_in_ms", 0) - death.get("time_in_round_in_ms", 0) <= TRADE_WINDOW_MS
                    for k in kills
                )
            if got_kill or puuid in assisted or survived or traded:
                result[puuid]["kast_rounds"] += 1

    return result


def build_match_row(ctx: dict, player: dict, round_stats: dict) -> dict:
    """Construit les paramètres SQL de `valo_matchs_stats` pour un joueur du match."""
    stats = player["stats"]
    damage = stats.get("damage") or {}
    nb_rounds = ctx["nb_rounds"]
    team = ctx["teams"].get(player.get("team_id"), {})
    extra = round_stats.get(player["puuid"], {})

    kills = stats.get("kills", 0)
    deaths = stats.get("deaths", 0)
    assists = stats.get("assists", 0)
    head = stats.get("headshots", 0)
    body = stats.get("bodyshots", 0)
    leg = stats.get("legshots", 0)
    tot_hits = max(1, head + body + leg)

    damage_made = damage.get("dealt", 0)
    damage_received = damage.get("received", 0)
    agent = (player.get("agent") or {}).get("name") or "Unknown"

    return {
        "m_id": ctx["match_id"], "r_id": riot_id_of(player),
        "date_match": ctx["date_match"], "saison": ctx["saison"],
        "m_jeu": ctx["mode_jeu"], "carte": ctx["carte"],
        "agent": agent, "role": ROLES_AGENTS.get(agent, "Sentinel"),
        "s_eq": (team.get("rounds") or {}).get("won", 0),
        "s_en": (team.get("rounds") or {}).get("lost", 0),
        "won": 1 if team.get("won") else 0,
        "kills": kills, "deaths": deaths, "assists": assists,
        "kd": round(kills / max(1, deaths), 2),
        "kad": round((kills + assists) / max(1, deaths), 2),
        "adr": round(damage_made / nb_rounds, 1),
        "acs": round(stats.get("score", 0) / nb_rounds, 1),
        "dd": round((damage_made - damage_received) / nb_rounds),
        "kpr": round(kills / nb_rounds, 2),
        "kast": round(extra.get("kast_rounds", 0) / nb_rounds * 100, 1),
        "fb": extra.get("first_bloods", 0),
        "flawless": extra.get("flawless_rounds", 0),
        "aces": extra.get("aces", 0),
        "head": head, "body": body, "leg": leg,
        "hp": round(head / tot_hits * 100, 1),
        "bp": round(body / tot_hits * 100, 1),
        "lp": round(leg / tot_hits * 100, 1),
        "rang": rank_label((player.get("tier") or {}).get("id")),
    }
