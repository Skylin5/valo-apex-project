"""Création et peuplement de la table VALO_COACH_VIDEOS (ressources coaching).

Usage :
    python data/setup_videos.py
"""

from db_utils import get_db_connection

# ---------------------------------------------------------------------------
# Catalogue de ressources vidéo coaching
# Format : (type_ressource, agent_concerne, palier_min, titre, chaine, yt_id, description)
# ---------------------------------------------------------------------------
RESSOURCES = [
    # Mécaniques Débutant / Bronze
    ("MECANIQUE_AIM", "TOUS", "DEBUTANT",
     "Le guide ultime du placement de réticule", "Swoopae", "b1_6j039600",
     "Exercices essentiels pour placer son viseur à hauteur de tête et arrêter de viser le sol."),
    ("MECANIQUE_PLACEMENT", "TOUS", "DEBUTANT",
     "Arrête de mourir bêtement : Slice the Pie", "Woohoojin", "08x5gM1j7oU",
     "Technique pour aborder les angles un par un et limiter les expositions multiples."),
    ("MECANIQUE_AIM", "TOUS", "DEBUTANT",
     "Maîtriser le Deadzoning et le Gunplay", "Miyagi", "76z8i7_F2jY",
     "Apprendre à tirer uniquement à l'arrêt complet pour éliminer les tirs aléatoires."),

    # Mécaniques Intermédiaire / Silver+
    ("MECANIQUE_PLACEMENT", "TOUS", "INTERMEDIAIRE",
     "Comment peeker comme un Pro", "Konpeki", "Fw9X1bO57zE",
     "Ferraille, jiggle peek et jump peek pour prendre des informations sans risque."),
    ("ECONOMIE", "TOUS", "TOUS",
     "Comprendre l'économie dans Valorant", "Thinking Man's Valorant", "mP7G6j5gH_Y",
     "Gestion des crédits : bonus round, semi-buy, full eco et save."),

    # Guides Agents clés
    ("GUIDE_AGENT", "Sage", "TOUS",
     "Guide complet Sage : Murs, orbes et tempo", "Grim", "p29u8F8sJso",
     "Optimisation des murs de ralentissement et survie en tant que Sentinelle."),
    ("GUIDE_AGENT", "Jett", "TOUS",
     "Guide Déplacements et Entrées de Site : Jett", "TenZ", "u2cZ0rWf4iY",
     "Mécaniques de dash et prises d'espace agressives."),
    ("GUIDE_AGENT", "Reyna", "TOUS",
     "Reyna : Gagner ses duels et isoler les 1v1", "Eggwick", "3k8G1wH9sAo",
     "Placement des œilletons et gestion de la réappropriation d'orbes."),
    ("GUIDE_AGENT", "Omen", "TOUS",
     "Guide Maître des Ombres : Omen", "Flexinja", "Y8s2W9fF4bA",
     "Smokes unilatérales, flashs paraboles et repositionnements ultimes."),
    ("GUIDE_AGENT", "Sova", "TOUS",
     "Guide et Lineups Fondamentaux : Sova", "AverageJonas", "d2S8jK0L1pA",
     "Reconnaissance de zones et flèches de révélation par rebond."),
    ("GUIDE_AGENT", "Killjoy", "TOUS",
     "Lockdown et Setups de Défense : Killjoy", "Thinking Man's Valorant", "5g8H9sK1wPo",
     "Configuration optimale des tourelles et essaims de nanobites."),
]


def main():
    conn = get_db_connection()
    cur = conn.cursor()

    # Recréation de la table
    cur.execute("""
        BEGIN
            EXECUTE IMMEDIATE 'DROP TABLE valo_coach_videos CASCADE CONSTRAINTS';
        EXCEPTION WHEN OTHERS THEN NULL;
        END;
    """)

    cur.execute("""
        CREATE TABLE valo_coach_videos (
            video_id       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            type_ressource VARCHAR2(30),
            agent_concerne VARCHAR2(30),
            palier_min     VARCHAR2(30),
            titre          VARCHAR2(150),
            chaine_youtube VARCHAR2(100),
            video_id_yt    VARCHAR2(50),
            description    VARCHAR2(500)
        )
    """)

    cur.executemany("""
        INSERT INTO valo_coach_videos
            (type_ressource, agent_concerne, palier_min, titre, chaine_youtube, video_id_yt, description)
        VALUES (:1, :2, :3, :4, :5, :6, :7)
    """, RESSOURCES)

    conn.commit()
    print(f"[OK] Table VALO_COACH_VIDEOS créée avec {len(RESSOURCES)} ressources fondamentales.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
