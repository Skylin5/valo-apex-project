"""Nettoyage des profils : isole les données d'entraînement ML des comptes joueurs.

Usage :
    python data/clean_profiles.py
"""

from db_utils import get_db_connection


def main():
    conn = get_db_connection()
    cur = conn.cursor()

    # Marquer les données d'entraînement avec un type dédié
    cur.execute("""
        UPDATE valo_joueurs
        SET type_profil = 'DATASET_ML'
        WHERE riot_id LIKE 'KaggleUser%'
           OR riot_id LIKE 'SimIron%'
           OR riot_id LIKE 'SimBronze%'
    """)
    nb_maj = cur.rowcount

    conn.commit()
    print(f"[OK] {nb_maj} profils d'entraînement isolés avec le statut 'DATASET_ML'.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
