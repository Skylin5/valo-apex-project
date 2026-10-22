"""Accès Oracle : table valo_stats_armes (kills par arme)."""

from collections.abc import Mapping


def upsert_weapon_kills(cur, riot_id: str, weapon_kills: Mapping[str, int]) -> int:
    """MERGE les kills par arme d'un joueur dans valo_stats_armes.

    Seules les armes présentes dans kaggle_ref_armes sont enregistrées (les autres,
    par exemple le corps à corps, sont ignorées). Les colonnes de précision ne sont
    pas fournies par l'API par arme : elles sont remises à NULL pour ne pas garder
    d'anciennes valeurs fausses. Retourne le nombre d'armes enregistrées.
    """
    count = 0
    for weapon, kills in weapon_kills.items():
        cur.execute("""
            MERGE INTO valo_stats_armes d
            USING (SELECT :r_id AS riot_id, k.nom_arme FROM kaggle_ref_armes k WHERE k.nom_arme = :nom) s
            ON (LOWER(d.riot_id) = LOWER(s.riot_id) AND d.nom_arme = s.nom_arme)
            WHEN MATCHED THEN UPDATE SET d.kills = :k1,
                d.head_pct = NULL, d.body_pct = NULL, d.leg_pct = NULL, d.adr_arme = NULL
            WHEN NOT MATCHED THEN INSERT (riot_id, nom_arme, kills)
            VALUES (s.riot_id, s.nom_arme, :k2)
        """, {"r_id": riot_id, "nom": weapon, "k1": kills, "k2": kills})
        count += cur.rowcount
    return count
