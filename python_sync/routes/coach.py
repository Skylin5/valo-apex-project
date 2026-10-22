"""Route /coach — chatbot coaching basé sur les données Oracle ML."""

from fastapi import APIRouter
from pydantic import BaseModel

from database import get_db_conn
from youtube import search_youtube

router = APIRouter()


class ChatRequest(BaseModel):
    riot_id: str
    question: str


@router.post("/coach/ask")
def coach_chat(req: ChatRequest):
    """Analyse les données du joueur et recommande une vidéo YouTube ciblée."""
    conn = get_db_conn()
    cur = conn.cursor()

    try:
        # 1. Récupération du dernier match du joueur
        cur.execute("""
            SELECT rang_predit_ml, point_faible_viseur, agent_prefere
            FROM (
                SELECT
                    rang_cible_ml AS rang_predit_ml,
                    CASE WHEN head_pct < 16 THEN 'AIM' ELSE 'PLACEMENT' END AS point_faible_viseur,
                    agent AS agent_prefere
                FROM valo_matchs_stats
                WHERE LOWER(riot_id) = LOWER(:r_id)
                ORDER BY perf_id DESC
            ) WHERE ROWNUM = 1
        """, {"r_id": req.riot_id})

        row = cur.fetchone()
        rang = row[0] if row else "3 - Bronze"
        axe_faible = row[1] if row else "AIM"
        agent_joueur = row[2] if row else "Sage"

        q_lower = req.question.lower()

        # 2. Recherche dans la table Oracle VALO_COACH_VIDEOS
        cur.execute("""
            SELECT titre, chaine_youtube, video_id_yt, description
            FROM valo_coach_videos
            WHERE (LOWER(agent_concerne) = LOWER(:ag) AND :ag_in_q = 1)
               OR (LOWER(type_ressource) LIKE '%' || :type_r || '%' AND :type_in_q = 1)
            ORDER BY video_id ASC
        """, {
            "ag": agent_joueur,
            "ag_in_q": 1 if agent_joueur.lower() in q_lower else 0,
            "type_r": "AIM" if any(w in q_lower for w in ("shoot", "viseur", "aim")) else "PLACEMENT",
            "type_in_q": 1 if any(w in q_lower for w in ("shoot", "viseur", "aim", "placement", "mourir", "duel")) else 0,
        })

        res = cur.fetchone()

        if res:
            source = "Base Oracle SQL (VALO_COACH_VIDEOS)"
            titre, chaine, yt_id, desc = res
            reponse = (
                f"D'après tes données ({rang}, point faible : {axe_faible}), "
                f"voici la ressource recommandée issue de notre base Oracle : "
                f"**{titre}** par *{chaine}*. {desc}"
            )
        else:
            # 3. Fallback : recherche dynamique YouTube
            source = "Recherche Dynamique YouTube"
            search_query = f"Valorant {req.question} guide"
            yt_id = search_youtube(search_query)
            titre = f"Guide recommandé : {req.question}"
            reponse = (
                f"Voici un tutoriel ciblé correspondant à ta demande "
                f"pour progresser depuis ton palier ({rang}) :"
            )
    finally:
        cur.close()
        conn.close()

    return {
        "statut": "OK",
        "joueur": req.riot_id,
        "rang_contexte": rang,
        "source": source,
        "reponse": reponse,
        "titre_video": titre,
        "youtube_id": yt_id,
        "url_video": f"https://www.youtube.com/watch?v={yt_id}",
    }
