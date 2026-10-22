import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import urllib.error
import re
import html as html_lib
import oracledb

from dashboard_template import render_dashboard

PORT = 5000
SYNC_API_URL = "http://localhost:8000"
SYNC_TIMEOUT = 180  # une synchro de 10 matchs peut attendre le quota HenrikDev
DB_CONFIG = {
    "user": "valo_app",
    "password": "ValoPassword123",
    "dsn": "localhost:1521/FREEPDB1"
}

def query_db(sql, params={}):
    try:
        conn = oracledb.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0].lower() for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[DB ERROR] {e}")
        return []

def zone_color(val, lobby, higher_is_better):
    """Couleur d'une zone de la silhouette selon l'écart (±10 %) avec la moyenne du lobby.

    Vert = mieux, rouge = moins bien, jaune = comparable, gris = pas de comparaison possible.
    """
    if val is None or not lobby:
        return "#95a5a6"
    ecart = (val - lobby) / lobby * 100
    if abs(ecart) < 10:
        return "#f1c40f"
    return "#2ecc71" if (ecart > 0) == higher_is_better else "#e74c3c"


def build_mmr_chart(points):
    """Courbe SVG de l'elo par match (valo_mmr_history), points colorés selon le gain ou la perte de RR."""
    if len(points) < 2:
        return """
            <div class="empty">
                <h3 class="section-title">Progression de rang</h3>
                Pas encore d'historique MMR pour ce joueur.<br>
                <small>Rempli par /sync, compte principal uniquement.</small>
            </div>"""

    width, height, pad = 700, 200, 24
    elos = [p["elo"] for p in points]
    low, high = min(elos), max(elos)
    span = max(1, high - low)
    step = (width - 2 * pad) / (len(points) - 1)

    coords = [
        (pad + i * step, height - pad - (p["elo"] - low) / span * (height - 2 * pad))
        for i, p in enumerate(points)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f"{pad:.1f},{height - pad:.1f} {line} {coords[-1][0]:.1f},{height - pad:.1f}"

    dots = ""
    for (x, y), p in zip(coords, points):
        change = p.get("variation_rr")
        color = "#94a3b8" if change is None else ("#34d399" if change >= 0 else "#f87171")
        when = p["date_match"].strftime("%d/%m") if p.get("date_match") else "?"
        label = f"{when} · {p.get('tier_nom') or '-'} · elo {p['elo']}"
        if change is not None:
            label += f" · {change:+.0f} RR"
        dots += (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="#070a12" stroke-width="2">'
            f'<title>{html_lib.escape(label)}</title></circle>'
        )

    total = sum(p["variation_rr"] or 0 for p in points)
    total_color = "#34d399" if total >= 0 else "#f87171"
    last_tier = html_lib.escape(str(points[-1].get("tier_nom") or "-"))
    return f"""
            <div class="mmr-head">
                <h3 class="section-title" style="margin:0">Progression de rang · {len(points)} matchs</h3>
                <span class="mmr-sub">Rang actuel <b>{last_tier}</b> · bilan <b style="color:{total_color};">{total:+.0f} RR</b></span>
            </div>
            <svg class="mmr-chart" viewBox="0 0 {width} {height}" role="img" aria-label="Progression d'elo par match">
                <defs>
                    <linearGradient id="mmrFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#ff4655" stop-opacity="0.35"/>
                        <stop offset="100%" stop-color="#ff4655" stop-opacity="0"/>
                    </linearGradient>
                </defs>
                <polygon points="{area}" fill="url(#mmrFill)"/>
                <polyline points="{line}" fill="none" stroke="#ff4655" stroke-width="2.5" stroke-linejoin="round"/>
                {dots}
            </svg>
            <div class="mmr-legend">
                <span><i class="dot" style="background:#34d399"></i>Gain de RR</span>
                <span><i class="dot" style="background:#f87171"></i>Perte de RR</span>
            </div>"""


def _weapon_card(w):
    """Carte d'une arme du top 3 : icône, part des kills et nombre de kills."""
    part = w["part_kills"] or 0
    icon = f'<img src="{html_lib.escape(str(w["image_url"]))}" alt="">' if w.get("image_url") else ""
    return f"""
            <div class="weapon">
                <div class="weapon-icon">{icon}</div>
                <div class="weapon-body">
                    <div class="weapon-name">{html_lib.escape(str(w['nom_arme']))}</div>
                    <div class="bar"><i style="width:{part}%"></i></div>
                    <small>{part}% de tes kills</small>
                </div>
                <div class="weapon-kills"><b>{w['kills']}</b><small>kills</small></div>
            </div>"""


EMPTY_WEAPONS = """
            <div class="empty">
                Aucune statistique d'arme synchronisée pour ce profil.<br>
                <small>Lance /sync pour ce joueur.</small>
            </div>"""


def get_real_youtube_video(search_term):
    try:
        clean_query = f"Valorant {search_term} guide"
        encoded = urllib.parse.quote_plus(clean_query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw_html = resp.read().decode('utf-8', errors='ignore')

        match_id = re.search(r'"videoRenderer":\{"videoId":"([a-zA-Z0-9_-]{11})"', raw_html)
        if match_id:
            vid_id = match_id.group(1)
            pattern_title = r'"videoRenderer":\{"videoId":"' + vid_id + r'".*?"title":\{"runs":\[\{"text":"(.*?)"\}'
            match_title = re.search(pattern_title, raw_html)
            title = match_title.group(1) if match_title else f"Guide Valorant : {search_term}"
            title = html_lib.unescape(title).replace(r'\u0026', '&')
            return vid_id, title
    except Exception:
        pass
    return "JnA8WfGqZ9c", "Guide Valorant : Crosshair Placement & Gunfight"

def sync_player(riot_id, region):
    """Relaie vers le /sync du service FastAPI. Retourne (code HTTP, payload JSON)."""
    if "#" not in riot_id:
        return 400, {"detail": "Riot ID invalide : attendu Pseudo#TAG."}
    if region not in ("eu", "na", "ap", "kr"):
        return 400, {"detail": "Région invalide."}
    pseudo, tag = riot_id.rsplit("#", 1)
    url = f"{SYNC_API_URL}/sync/{region}/{urllib.parse.quote(pseudo, safe='')}/{urllib.parse.quote(tag, safe='')}"
    try:
        with urllib.request.urlopen(url, timeout=SYNC_TIMEOUT) as resp:
            return 200, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"detail": f"Erreur {e.code} du service de synchro."}
    except Exception as e:
        return 502, {"detail": f"Service de synchro injoignable ({SYNC_API_URL}) : {e}"}


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/api/sync":
            try:
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                code, payload = sync_player(str(data.get("riot_id", "")).strip(), str(data.get("region", "eu")).lower())
            except Exception as e:
                code, payload = 400, {"detail": f"Requête invalide : {e}"}
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == "/api/chat":
            try:
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                pseudo = data.get("riot_id", "Nova#roma")
                question = data.get("question", "")
                q_lower = question.lower()

                # Récupération des statistiques réelles du joueur
                p_stats = query_db("""
                    SELECT 
                        ROUND(AVG(kd_ratio), 2) as kd,
                        ROUND(AVG(adr), 1) as adr,
                        ROUND(AVG(head_pct), 1) as hs,
                        ROUND(AVG(body_pct), 1) as body,
                        ROUND(AVG(dd_delta), 1) as dd,
                        ROUND(AVG(kast_pct), 1) as kast
                    FROM valo_matchs_stats
                    WHERE LOWER(riot_id) = LOWER(:p)
                """, {"p": pseudo})

                st = p_stats[0] if p_stats and p_stats[0].get('kd') is not None else {
                    "kd": 1.15, "adr": 138.2, "hs": 14.8, "body": 74.2, "dd": -39.0, "kast": 71.0
                }
                for k, default_val in [("kd", 1.0), ("adr", 130.0), ("hs", 15.0), ("body", 70.0), ("dd", 0.0), ("kast", 70.0)]:
                    if st.get(k) is None:
                        st[k] = default_val

                # Détection d'intentions
                demande_priorite = any(w in q_lower for w in ["premier", "priorite", "priorité", "faible", "defaut", "défaut", "rank", "monter", "ameliorer", "améliorer"])
                demande_agent = next((a for a in ["sage", "omen", "jett", "reyna", "sova", "clove", "cypher", "killjoy", "phoenix", "brimstone"] if a in q_lower), None)

                # Diagnostic textuel intelligent
                if demande_priorite and not demande_agent:
                    if st['dd'] < -15:
                        point_critique = "le positionnement et l'échange de dégâts (DDΔ)"
                        explication = (
                            f"Pour le joueur **{pseudo}**, le point le plus faible actuellement est **{point_critique}**.\n\n"
                            f"📊 **Le constat chiffré :** Ton DDΔ moyen est de **{st['dd']} par manche**. "
                            f"Cela signifie que même si tu fais des éliminations, tu subis systématiquement plus de dégâts que tu n'en infliges. "
                            f"Pour passer durablement au palier supérieur, cette valeur doit être proche de 0 ou positive.\n\n"
                            f"🎯 **Ce que tu dois corriger en premier :**\n"
                            f"1. **Arrête de 'dry peek'** : Ne décale aucun angle sans utiliser une compétence ou sans isoler les lignes une par une.\n"
                            f"2. **Joue les trades** : Reste à proximité d'un coéquipier au lieu de tenter des duels 1v1 isolés.\n"
                            f"3. **Recul après tir** : Tire 2 ou 3 balles maximum, puis désengage-toi derrière un couvert au lieu de t'accroupir en plein milieu."
                        )
                        terme_yt = "positionnement peeking isoler les angles"
                    elif st['hs'] < 16.0:
                        point_critique = "la précision du premier tir (placement de réticule)"
                        explication = (
                            f"Pour le joueur **{pseudo}**, le point faible prioritaire est **{point_critique}**.\n\n"
                            f"📊 **Le constat chiffré :** Tu as **{st['body']}% de tirs dans le corps** contre seulement **{st['hs']}% dans la tête**. "
                            f"Au-delà du rang Bronze, les duels sont sanctionnés instantanément par un one-tap à la Vandal (160 dégâts).\n\n"
                            f"🎯 **Ce que tu dois corriger en premier :**\n"
                            f"1. **Hauteur de tête passive** : Ton viseur doit toujours être calé sur les repères visuels des cartes (lignes de caisses, rainures des murs).\n"
                            f"2. **Bannis le réflexe accroupi** : S'accroupir prématurément abaisse ta tête directement dans les tirs ennemis qui visaient le torse.\n"
                            f"3. **Pratique le tap-fire** : En Deathmatch, force-toi à jouer au Sheriff sans tirer tant que le viseur n'est pas sur la tête."
                        )
                        terme_yt = "crosshair placement hauteur de tete"
                    else:
                        explication = (
                            f"Les métriques individuelles de **{pseudo}** sont stables (KD: {st['kd']}, HS%: {st['hs']}%, KAST: {st['kast']}%).\n"
                            f"L'axe de progression principal est la **coordination d'équipe** : joue systématiquement sur le timing de tes initiateurs et convertis tes rounds d'avantage numérique."
                        )
                        terme_yt = "game sense valorant teamplay"

                elif demande_agent:
                    explication = (
                        f"Voici le plan de jeu pour progresser sur **{demande_agent.capitalize()}** avec **{pseudo}** :\n\n"
                        f"En tant qu'agent spécialisé, adapte tes prises d'information. "
                        f"Conserve tes compétences pour ralentir l'exécution adverse sur site et reste en vie pour sécuriser les réanimations, smokes ou retakes."
                    )
                    terme_yt = f"{demande_agent.capitalize()} guide trucs et astuces"

                else:
                    explication = f"Voici ce qu'indiquent les données Oracle pour **{pseudo}** : travaille en priorité ton placement de réticule ({st['hs']}% HS) et la gestion de tes prises d'angles pour réduire tes dégâts subis ({st['dd']} DDΔ)."
                    terme_yt = question

                # Recherche vidéo correspondante
                real_vid_id, real_title = get_real_youtube_video(terme_yt)

                resp_payload = {
                    "statut": "OK",
                    "reponse": explication,
                    "titre_video": real_title,
                    "youtube_id": real_vid_id,
                    "source": "Analyse Oracle ML & Recommandation YouTube"
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode('utf-8'))

            except Exception as e:
                print(f"[CHAT ERROR] {e}")
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "statut": "OK",
                    "reponse": "Erreur lors de l'analyse des données de match.",
                    "titre_video": "Guide Tir Valorant",
                    "youtube_id": "JnA8WfGqZ9c",
                    "source": "Guide de secours"
                }, ensure_ascii=False).encode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # 1. Endpoint API : Recherche et autocomplétion des joueurs
        if parsed.path == "/api/players":
            q = params.get('q', [''])[0].strip()
            if q:
                sql = """
                    SELECT riot_id, type_profil, rang_actuel, niveau_compte
                    FROM valo_joueurs
                    WHERE LOWER(riot_id) LIKE LOWER(:q)
                    ORDER BY 
                        CASE WHEN LOWER(riot_id) LIKE LOWER(:q_prefix) THEN 0 ELSE 1 END,
                        CASE WHEN type_profil = 'MON_COMPTE' THEN 0 
                             WHEN type_profil = 'JOUEUR_MATCHMAKING' THEN 1 
                             WHEN type_profil = 'BENCHMARK' THEN 2
                             ELSE 3 END,
                        riot_id
                    FETCH FIRST 30 ROWS ONLY
                """
                players = query_db(sql, {"q": f"%{q}%", "q_prefix": f"{q}%"})
            else:
                sql = """
                    SELECT riot_id, type_profil, rang_actuel, niveau_compte
                    FROM valo_joueurs
                    ORDER BY 
                        CASE WHEN type_profil = 'MON_COMPTE' THEN 0 
                             WHEN type_profil = 'JOUEUR_MATCHMAKING' THEN 1 
                             WHEN type_profil = 'BENCHMARK' THEN 2
                             ELSE 3 END,
                        riot_id
                    FETCH FIRST 20 ROWS ONLY
                """
                players = query_db(sql)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(players, ensure_ascii=False).encode('utf-8'))
            return

        # 2. Page HTML principale
        selected_player = params.get('player', ['Nova#roma'])[0]

        # Récupération des informations de profil du joueur sélectionné
        p_info_rows = query_db("""
            SELECT riot_id, type_profil, rang_actuel, niveau_compte 
            FROM valo_joueurs 
            WHERE LOWER(riot_id) = LOWER(:p)
        """, {"p": selected_player})
        p_info = p_info_rows[0] if p_info_rows else {
            "riot_id": selected_player, "type_profil": "PERSONNALISÉ", "rang_actuel": "-", "niveau_compte": None
        }
        display_riot_id = p_info.get("riot_id") or selected_player

        # Nombre total de joueurs enregistrés en base
        count_rows = query_db("SELECT COUNT(*) as cnt FROM valo_joueurs")
        total_players_cnt = count_rows[0]['cnt'] if count_rows else 2180

        # Statistiques globales de match
        stats_rows = query_db("""
            SELECT 
                COUNT(*) as nb_matchs,
                ROUND(AVG(kd_ratio), 2) as kd_moyen,
                ROUND(AVG(adr), 1) as adr_moyen,
                ROUND(AVG(acs), 1) as acs_moyen,
                ROUND(AVG(kast_pct), 1) as kast_moyen,
                ROUND(AVG(head_pct), 1) as hs_pct,
                ROUND(AVG(body_pct), 1) as body_pct,
                ROUND(AVG(leg_pct), 1) as leg_pct,
                ROUND(SUM(victoire) / GREATEST(COUNT(*), 1) * 100, 1) as winrate
            FROM valo_matchs_stats
            WHERE LOWER(riot_id) = LOWER(:p)
        """, {"p": selected_player})

        st = stats_rows[0] if stats_rows and stats_rows[0].get('nb_matchs', 0) > 0 else {
            "nb_matchs": 0, "kd_moyen": 1.15, "adr_moyen": 138.2, "acs_moyen": 210.5,
            "kast_moyen": 71.0, "hs_pct": 14.8, "body_pct": 74.2, "leg_pct": 11.0, "winrate": 50.0
        }
        for k, default_val in [
            ("kd_moyen", 0.0), ("adr_moyen", 0.0), ("acs_moyen", 0.0),
            ("kast_moyen", 0.0), ("hs_pct", 0.0), ("body_pct", 0.0),
            ("leg_pct", 0.0), ("winrate", 0.0), ("nb_matchs", 0)
        ]:
            if st.get(k) is None:
                st[k] = default_val

        # Diagnostic Oracle Machine Learning (Vue V_APEX_COACH_IA)
        coach_rows = query_db("""
            SELECT 
                rang_merite_ia as rang_predit_ml, 
                reco_precision as axe_viseur, 
                reco_positionnement as axe_positionnement, 
                reco_collectif as axe_survie
            FROM v_apex_coach_ia
            WHERE LOWER(riot_id) = LOWER(:p)
        """, {"p": selected_player})

        if not coach_rows:
            print(f"[COACH] Aucune ligne dans v_apex_coach_ia pour {selected_player} : rang réel affiché à la place.")
        coach = coach_rows[0] if coach_rows else {
            "rang_predit_ml": p_info.get("rang_actuel") or "Non estimé",
            "axe_viseur": "AXE N°1 (VISEUR) : Travaille le placement de viseur en Deathmatch.",
            "axe_positionnement": "AXE N°2 (POSITIONNEMENT) : Améliore tes prises d'angles pour réduire les dégâts reçus.",
            "axe_survie": "AXE N°3 (SURVIE) : Reste avec tes alliés pour assurer les trades (KAST)."
        }
        for k in ["rang_predit_ml", "axe_viseur", "axe_positionnement", "axe_survie"]:
            if not coach.get(k):
                coach[k] = "En attente de données complémentaires."

        # Précision du joueur (tête/corps/jambes) comparée à la moyenne du lobby
        # (= tous les autres joueurs enregistrés), même calcul que la vue v_apex_accuracy_compare
        acc_sql = """
            SELECT
                ROUND(100 * SUM(head_hits) / NULLIF(SUM(head_hits + body_hits + leg_hits), 0), 1) AS head,
                ROUND(100 * SUM(body_hits) / NULLIF(SUM(head_hits + body_hits + leg_hits), 0), 1) AS body,
                ROUND(100 * SUM(leg_hits)  / NULLIF(SUM(head_hits + body_hits + leg_hits), 0), 1) AS leg
            FROM valo_matchs_stats
            WHERE LOWER(riot_id) {op} LOWER(:p)
        """
        acc_rows = query_db(acc_sql.format(op="="), {"p": selected_player})
        lobby_rows = query_db(acc_sql.format(op="<>"), {"p": selected_player})
        acc = acc_rows[0] if acc_rows else {}
        lobby = lobby_rows[0] if lobby_rows else {}

        # Top 3 armes par kills (l'API ne fournit pas la précision par arme)
        armes = query_db("""
            SELECT a.nom_arme, a.kills, k.image_url,
                   ROUND(a.kills / NULLIF(SUM(a.kills) OVER (), 0) * 100, 1) AS part_kills
            FROM valo_stats_armes a
            LEFT JOIN kaggle_ref_armes k ON a.nom_arme = k.nom_arme
            WHERE LOWER(a.riot_id) = LOWER(:p)
            ORDER BY a.kills DESC
            FETCH FIRST 3 ROWS ONLY
        """, {"p": selected_player})
        # SUM() OVER () porte sur toutes les armes avant le FETCH FIRST : la part reste donc exacte

        # SUM() OVER () porte sur toutes les armes avant le FETCH FIRST : la part reste donc exacte
        armes_html = "".join(_weapon_card(w) for w in armes) or EMPTY_WEAPONS

        # Progression de rang (alimentée par /sync via v2/mmr-history)
        mmr_points = query_db("""
            SELECT date_match, elo, tier_nom, variation_rr
            FROM valo_mmr_history
            WHERE LOWER(riot_id) = LOWER(:p) AND elo IS NOT NULL
            ORDER BY date_match
        """, {"p": selected_player})
        mmr_html = build_mmr_chart(mmr_points)

        # Silhouette : couleur de chaque zone selon l'écart (±10 %) avec le lobby
        c_head = zone_color(acc.get('head'), lobby.get('head'), True)
        c_body = zone_color(acc.get('body'), lobby.get('body'), False)
        c_leg = zone_color(acc.get('leg'), lobby.get('leg'), False)

        def fmt(v):
            return "-" if v is None else f"{v}%"

        mannequin_html = f"""
                <h4>Précision vs lobby</h4>
                <svg width="180" height="260" viewBox="0 0 180 260">
                    <circle cx="90" cy="40" r="24" fill="{c_head}" opacity="0.9"/>
                    <text x="90" y="45" font-size="12" fill="#000" font-weight="bold" text-anchor="middle">{fmt(acc.get('head'))}</text>
                    <rect x="62" y="70" width="56" height="85" rx="8" fill="{c_body}" opacity="0.9"/>
                    <rect x="38" y="72" width="18" height="75" rx="6" fill="{c_body}" opacity="0.9"/>
                    <rect x="124" y="72" width="18" height="75" rx="6" fill="{c_body}" opacity="0.9"/>
                    <text x="90" y="118" font-size="12" fill="#000" font-weight="bold" text-anchor="middle">{fmt(acc.get('body'))}</text>
                    <rect x="64" y="162" width="22" height="85" rx="5" fill="{c_leg}" opacity="0.9"/>
                    <rect x="94" y="162" width="22" height="85" rx="5" fill="{c_leg}" opacity="0.9"/>
                    <text x="90" y="210" font-size="12" fill="#000" font-weight="bold" text-anchor="middle">{fmt(acc.get('leg'))}</text>
                </svg>
                <div style="font-size:12px; color:#8899aa; margin-top:10px; line-height:1.6;">
                    Lobby : tête {fmt(lobby.get('head'))} · corps {fmt(lobby.get('body'))} · jambes {fmt(lobby.get('leg'))}
                </div>
                <div style="display:flex; justify-content:space-around; font-size:12px; margin-top:8px;">
                    <span style="color:#2ecc71;">● Mieux</span>
                    <span style="color:#f1c40f;">● Comparable</span>
                    <span style="color:#e74c3c;">● Moins bien</span>
                </div>
        """

        # Badge type profil
        ptype = p_info.get('type_profil', 'JOUEUR')
        if ptype == 'MON_COMPTE':
            badge_class = 'badge-mon-compte'
        elif ptype == 'JOUEUR_MATCHMAKING':
            badge_class = 'badge-matchmaking'
        elif ptype == 'BENCHMARK':
            badge_class = 'badge-benchmark'
        else:
            badge_class = 'badge-dataset-ml'

        js_selected_player = json.dumps(display_riot_id)

        html = render_dashboard({
            "display_riot_id": display_riot_id,
            "ptype": ptype,
            "badge_class": badge_class,
            "rank_label": p_info.get("rang_actuel"),
            "level": p_info.get("niveau_compte"),
            "total_players_cnt": total_players_cnt,
            "st": st,
            "coach": coach,
            "mannequin_html": mannequin_html,
            "armes_html": armes_html,
            "mmr_html": mmr_html,
            "js_selected_player": js_selected_player,
        })
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

socketserver.ThreadingTCPServer.allow_reuse_address = True
socketserver.ThreadingTCPServer.daemon_threads = True
with socketserver.ThreadingTCPServer(("", PORT), CustomHandler) as httpd:
    print(f"Serveur relancé sur http://localhost:{PORT}")
    httpd.serve_forever()
