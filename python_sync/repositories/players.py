"""Accès Oracle : table valo_joueurs."""


def upsert_player(cur, riot_id: str, level: int, rank: str, profile_type: str = "JOUEUR_MATCHMAKING"):
    """MERGE un joueur dans valo_joueurs (insert, ou mise à jour du niveau et du rang)."""
    cur.execute("""
        MERGE INTO valo_joueurs d
        USING (SELECT :p_id AS riot_id FROM dual) s ON (LOWER(d.riot_id) = LOWER(s.riot_id))
        WHEN MATCHED THEN UPDATE SET d.niveau_compte = :p_lvl, d.rang_actuel = :p_rank1,
            d.derniere_maj = SYSTIMESTAMP
        WHEN NOT MATCHED THEN INSERT (riot_id, type_profil, niveau_compte, rang_actuel)
        VALUES (:p_id2, :profil, :p_lvl2, :p_rank2)
    """, {
        "p_id": riot_id, "p_lvl": level, "p_rank1": rank,
        "p_id2": riot_id, "profil": profile_type, "p_lvl2": level, "p_rank2": rank,
    })
