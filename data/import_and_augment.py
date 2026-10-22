"""Import des données Kaggle et augmentation synthétique (Fer / Bronze).

Charge le CSV valorant_games.csv, génère des profils synthétiques pour les
rangs bas, puis insère le tout dans Oracle pour enrichir le jeu d'entraînement ML.

Usage :
    python data/import_and_augment.py
"""

import csv
import os
import random

import numpy as np

from db_utils import get_db_connection

KAGGLE_CSV_PATH = os.path.join(
    os.path.dirname(__file__), "valorant_games.csv"
)

# Correspondance des rangs Kaggle vers nos libellés Oracle
MAP_RANGS = {
    "Silver 1": "4 - Argent",
    "Silver 2": "4 - Argent",
    "Silver 3": "4 - Argent",
    "Gold 1": "5 - Or",
    "Gold 2": "5 - Or",
    "Gold 3": "5 - Or",
    "Platinum 1": "6 - Platine",
    "Platinum 2": "6 - Platine",
    "Platinum 3": "6 - Platine",
    "Diamond 1": "6 - Platine",
    "Diamond 2": "6 - Platine",
    "Diamond 3": "6 - Platine",
    "Ascendant 1": "6 - Platine",
    "Ascendant 2": "6 - Platine",
    "Ascendant 3": "6 - Platine",
}


def load_kaggle_data():
    records = []
    if not os.path.exists(KAGGLE_CSV_PATH):
        print(f"[!] Fichier {KAGGLE_CSV_PATH} introuvable.")
        return records

    with open(KAGGLE_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_rank = row.get("rank", "")
            mapped_rank = MAP_RANGS.get(raw_rank)
            if not mapped_rank:
                continue

            try:
                kills = int(row.get("kills", 0))
                deaths = max(1, int(row.get("deaths", 1)))
                assists = int(row.get("assists", 0))
                kdr = float(row.get("kdr", round(kills / deaths, 2)))
                adr = float(row.get("avg_dmg", 120.0))
                hs_pct = float(row.get("headshot_pct", 15.0))
                dd = float(row.get("avg_dmg_delta", 0.0))
                acs = float(row.get("acs", 200.0))
                agent = row.get("agent", "Jett")
                match_id = f"KGL_{row.get('game_id', random.randint(1000, 999999))}"

                # Décomposition estimée des impacts
                tot_shots = 100
                head_hits = int(round(tot_shots * (hs_pct / 100.0)))
                body_hits = int(
                    round(tot_shots * (max(0.0, 100.0 - hs_pct - 10.0) / 100.0))
                )
                leg_hits = max(0, tot_shots - head_hits - body_hits)

                records.append(
                    {
                        "match_id": match_id,
                        "riot_id": f"KaggleUser#{row.get('game_id')}",
                        "mode_jeu": "Competitive",
                        "carte": row.get("map", "Ascent"),
                        "agent": agent,
                        "role_agent": "Duelist",
                        "score_eq": 13,
                        "score_en": 10,
                        "victoire": 1,
                        "kills": kills,
                        "deaths": deaths,
                        "assists": assists,
                        "kd": kdr,
                        "kad": round((kills + assists) / deaths, 2),
                        "adr": adr,
                        "acs": acs,
                        "kast": 70.0,
                        "dd": dd,
                        "kpr": round(kills / 20.0, 2),
                        "head": head_hits,
                        "body": body_hits,
                        "leg": leg_hits,
                        "hp": hs_pct,
                        "bp": round(body_hits / tot_shots * 100.0, 1),
                        "lp": round(leg_hits / tot_shots * 100.0, 1),
                        "rang": mapped_rank,
                    }
                )
            except Exception:
                continue
    return records


def generate_augmented_data(nb_samples=250):
    """Génération par distribution gaussienne pour Fer et Bronze."""
    augmented = []

    # Profils Fer (Iron)
    for i in range(nb_samples):
        hp = round(np.clip(np.random.normal(10.5, 2.5), 3.0, 15.0), 1)
        bp = round(np.clip(np.random.normal(74.0, 4.0), 60.0, 85.0), 1)
        lp = round(max(0.0, 100.0 - hp - bp), 1)
        kd = round(np.clip(np.random.normal(0.72, 0.15), 0.3, 1.1), 2)
        adr = round(np.clip(np.random.normal(92.0, 18.0), 45.0, 125.0), 1)
        dd = round(np.clip(np.random.normal(-35.0, 18.0), -85.0, 10.0), 1)
        acs = round(np.clip(np.random.normal(140.0, 25.0), 75.0, 210.0), 1)
        kast = round(np.clip(np.random.normal(55.0, 5.0), 40.0, 65.0), 1)

        augmented.append(
            {
                "match_id": f"AUG_IRON_{i}",
                "riot_id": f"SimIron#{i:03d}",
                "mode_jeu": "Competitive",
                "carte": random.choice(["Ascent", "Haven", "Bind", "Split"]),
                "agent": random.choice(["Sage", "Brimstone", "Phoenix"]),
                "role_agent": "Sentinel",
                "score_eq": 8,
                "score_en": 13,
                "victoire": 0,
                "kills": int(kd * 16),
                "deaths": 16,
                "assists": random.randint(1, 5),
                "kd": kd,
                "kad": kd + 0.15,
                "adr": adr,
                "acs": acs,
                "kast": kast,
                "dd": dd,
                "kpr": round(kd * 0.7, 2),
                "head": int(hp),
                "body": int(bp),
                "leg": int(lp),
                "hp": hp,
                "bp": bp,
                "lp": lp,
                "rang": "1 - Débutant (Niv 1-20)",
            }
        )

    # Profils Bronze
    for i in range(nb_samples):
        hp = round(np.clip(np.random.normal(15.0, 2.8), 8.0, 20.0), 1)
        bp = round(np.clip(np.random.normal(72.0, 3.5), 62.0, 80.0), 1)
        lp = round(max(0.0, 100.0 - hp - bp), 1)
        kd = round(np.clip(np.random.normal(0.88, 0.16), 0.5, 1.3), 2)
        adr = round(np.clip(np.random.normal(115.0, 20.0), 70.0, 150.0), 1)
        dd = round(np.clip(np.random.normal(-15.0, 15.0), -50.0, 25.0), 1)
        acs = round(np.clip(np.random.normal(175.0, 30.0), 110.0, 245.0), 1)
        kast = round(np.clip(np.random.normal(63.0, 5.0), 50.0, 72.0), 1)

        augmented.append(
            {
                "match_id": f"AUG_BRONZE_{i}",
                "riot_id": f"SimBronze#{i:03d}",
                "mode_jeu": "Competitive",
                "carte": random.choice(["Ascent", "Haven", "Lotus", "Sunset"]),
                "agent": random.choice(["Reyna", "Jett", "Omen", "Sova"]),
                "role_agent": "Duelist",
                "score_eq": 11,
                "score_en": 13,
                "victoire": 0,
                "kills": int(kd * 17),
                "deaths": 17,
                "assists": random.randint(2, 6),
                "kd": kd,
                "kad": kd + 0.2,
                "adr": adr,
                "acs": acs,
                "kast": kast,
                "dd": dd,
                "kpr": round(kd * 0.8, 2),
                "head": int(hp),
                "body": int(bp),
                "leg": int(lp),
                "hp": hp,
                "bp": bp,
                "lp": lp,
                "rang": "3 - Bronze",
            }
        )

    return augmented


def insert_into_oracle(all_rows):
    conn = get_db_connection()
    cur = conn.cursor()

    # Insertion des joueurs dans VALO_JOUEURS pour respecter les contraintes
    joueurs_uniques = [
        {"r_id": r["riot_id"], "rang": r["rang"]} for r in all_rows
    ]
    sql_joueurs = """
        MERGE INTO valo_joueurs d
        USING (SELECT :r_id AS riot_id FROM dual) s
        ON (LOWER(d.riot_id) = LOWER(s.riot_id))
        WHEN NOT MATCHED THEN INSERT (riot_id, type_profil, niveau_compte, rang_actuel)
        VALUES (:r_id, 'JOUEUR_MATCHMAKING', 50, :rang)
    """
    cur.executemany(sql_joueurs, joueurs_uniques, batcherrors=True)
    conn.commit()

    # Insertion des matchs dans VALO_MATCHS_STATS sans hint défaillant
    sql_matchs = """
        INSERT INTO valo_matchs_stats (
            match_id, riot_id, mode_jeu, carte, agent, role_agent,
            score_equipe, score_ennemi, victoire, kills, deaths, assists,
            kd_ratio, kad_ratio, adr, acs, kast_pct, dd_delta, kills_per_round,
            first_bloods, flawless_rounds, aces, head_hits, body_hits, leg_hits,
            head_pct, body_pct, leg_pct, rang_cible_ml
        ) VALUES (
            :match_id, :riot_id, :mode_jeu, :carte, :agent, :role_agent,
            :score_eq, :score_en, :victoire, :kills, :deaths, :assists,
            :kd, :kad, :adr, :acs, :kast, :dd, :kpr,
            1, 0, 0, :head, :body, :leg,
            :hp, :bp, :lp, :rang
        )
    """

    # batcherrors=True ignore les doublons éventuels sans bloquer le script
    cur.executemany(sql_matchs, all_rows, batcherrors=True)

    nb_erreurs = len(cur.getbatcherrors())
    conn.commit()

    print(
        f"[OK] Insertion terminée : {len(all_rows) - nb_erreurs} lignes insérées ({nb_erreurs} doublons ignorés)."
    )
    cur.close()
    conn.close()


if __name__ == "__main__":
    k_data = load_kaggle_data()
    aug_data = generate_augmented_data(250)
    total = k_data + aug_data
    print(
        f"Préparation : {len(k_data)} Kaggle + {len(aug_data)} Augmentées (Fer/Bronze) = {len(total)} au total."
    )
    insert_into_oracle(total)