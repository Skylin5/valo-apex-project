"""Accès Oracle : table valo_matchs_stats."""


def insert_match_perf(cur, row: dict) -> bool:
    """Insère une performance de joueur si elle n'existe pas déjà.

    `row` vient de `services.match_parser.build_match_row`.
    Retourne True si une insertion a eu lieu.
    """
    cur.execute("""
        SELECT COUNT(*) FROM valo_matchs_stats WHERE match_id = :m_id AND LOWER(riot_id) = LOWER(:r_id)
    """, {"m_id": row["m_id"], "r_id": row["r_id"]})

    if cur.fetchone()[0] != 0:
        return False

    cur.execute("""
        INSERT INTO valo_matchs_stats (
            match_id, riot_id, date_match, saison, mode_jeu, carte, agent, role_agent,
            score_equipe, score_ennemi, victoire, kills, deaths, assists,
            kd_ratio, kad_ratio, adr, acs, kast_pct, dd_delta, kills_per_round,
            first_bloods, flawless_rounds, aces, head_hits, body_hits, leg_hits,
            head_pct, body_pct, leg_pct, rang_cible_ml
        ) VALUES (
            :m_id, :r_id, NVL(:date_match, SYSTIMESTAMP), :saison, :m_jeu, :carte, :agent, :role,
            :s_eq, :s_en, :won, :kills, :deaths, :assists,
            :kd, :kad, :adr, :acs, :kast, :dd, :kpr,
            :fb, :flawless, :aces, :head, :body, :leg,
            :hp, :bp, :lp, :rang
        )
    """, row)
    return True
