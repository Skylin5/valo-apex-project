"""Accès Oracle : table valo_mmr_history (progression de rang par match)."""


def insert_missing_mmr_rows(cur, rows: list[dict]) -> int:
    """Insère les entrées d'historique MMR absentes (rows : `services.mmr_parser.mmr_rows`).

    Retourne le nombre de nouvelles lignes.
    """
    inserted = 0
    for row in rows:
        cur.execute("""
            MERGE INTO valo_mmr_history d
            USING (SELECT :r_id AS riot_id, :m_id AS match_id FROM dual) s
            ON (LOWER(d.riot_id) = LOWER(s.riot_id) AND d.match_id = s.match_id)
            WHEN NOT MATCHED THEN INSERT (riot_id, match_id, date_match, carte, saison,
                tier_id, tier_nom, elo, rr, variation_rr)
            VALUES (:r_id2, :m_id2, :date_match, :carte, :saison,
                :tier_id, :tier_nom, :elo, :rr, :variation)
        """, {**row, "r_id2": row["r_id"], "m_id2": row["m_id"]})
        inserted += cur.rowcount
    return inserted
