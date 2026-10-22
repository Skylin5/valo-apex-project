"""Page HTML du dashboard de prévisualisation (thème sombre, esprit gaming).

Le gabarit utilise des jetons `__NOM__` remplacés par `render_dashboard`. Les accolades
du CSS et du JavaScript restent donc telles quelles, sans échappement.
"""

import html as html_lib
import math

TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Valo Oracle · __RIOT_ID__</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #070a12;
            --panel: rgba(17, 24, 39, 0.62);
            --panel-2: rgba(30, 41, 59, 0.42);
            --line: rgba(148, 163, 184, 0.13);
            --text: #e6ebf3;
            --muted: #7f8ba3;
            --red: #ff4655;
            --red-deep: #b9242f;
            --cyan: #22d3ee;
            --violet: #a78bfa;
            --green: #34d399;
            --amber: #fbbf24;
            --radius: 16px;
            --display: 'Rajdhani', 'Segoe UI', sans-serif;
            --body: 'Inter', 'Segoe UI', system-ui, sans-serif;
        }
        @media (prefers-color-scheme: dark) {
            :root:not([data-theme="light"]) { --bg: #070a12; }
        }
        :root[data-theme="dark"] { --bg: #070a12; }

        * { box-sizing: border-box; }
        html, body { margin: 0; }
        body {
            min-height: 100vh;
            background-color: var(--bg);
            background-image:
                radial-gradient(1100px 620px at 8% -12%, rgba(255, 70, 85, 0.13), transparent 60%),
                radial-gradient(900px 540px at 100% 0%, rgba(34, 211, 238, 0.10), transparent 60%),
                linear-gradient(rgba(148, 163, 184, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(148, 163, 184, 0.035) 1px, transparent 1px);
            background-size: auto, auto, 44px 44px, 44px 44px;
            background-attachment: fixed;
            color: var(--text);
            font-family: var(--body);
            font-size: 14px;
            line-height: 1.5;
        }
        h3, h4 { margin: 0; font-family: var(--display); }

        /* --- Barre du haut ------------------------------------------------ */
        .topbar {
            position: sticky; top: 0; z-index: 50;
            display: flex; align-items: center; justify-content: space-between; gap: 18px;
            padding: 14px 28px;
            background: rgba(7, 10, 18, 0.72);
            backdrop-filter: blur(14px);
            border-bottom: 1px solid var(--line);
        }
        .brand {
            font-family: var(--display); font-weight: 700; font-size: 22px; letter-spacing: 0.08em;
            white-space: nowrap;
        }
        .brand .slash { color: var(--red); }
        .brand small {
            margin-left: 8px; font-size: 11px; letter-spacing: 0.18em; color: var(--muted); font-weight: 600;
        }

        .search { position: relative; width: min(440px, 100%); }
        .search-box {
            display: flex; align-items: center; gap: 10px;
            padding: 9px 14px;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--line);
            border-radius: 999px;
            transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
        }
        .search-box:focus-within {
            border-color: rgba(34, 211, 238, 0.6);
            box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.12);
            background: rgba(255, 255, 255, 0.06);
        }
        .search-box svg { color: var(--muted); flex-shrink: 0; }
        .search-input {
            flex: 1; min-width: 0; background: transparent; border: 0; outline: 0;
            color: var(--text); font: inherit;
        }
        .search-input::placeholder { color: #5b6679; }
        .clear {
            display: none; background: none; border: 0; color: var(--muted);
            font-size: 18px; line-height: 1; cursor: pointer; padding: 0 2px;
        }
        .clear:hover { color: var(--red); }

        .dropdown {
            position: absolute; top: calc(100% + 8px); left: 0; right: 0;
            display: none; max-height: 380px; overflow-y: auto;
            background: #0c1220;
            border: 1px solid var(--line);
            border-radius: 14px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.6);
            z-index: 100;
        }
        .dropdown::-webkit-scrollbar { width: 6px; }
        .dropdown::-webkit-scrollbar-thumb { background: #243047; border-radius: 3px; }
        .dd-head {
            display: flex; justify-content: space-between; padding: 10px 14px;
            font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
            color: var(--muted); border-bottom: 1px solid var(--line);
        }
        .dd-item {
            display: flex; align-items: center; justify-content: space-between; gap: 10px;
            padding: 11px 14px; cursor: pointer; border-bottom: 1px solid rgba(148, 163, 184, 0.07);
        }
        .dd-item:last-child { border-bottom: 0; }
        .dd-item:hover, .dd-item.highlighted { background: rgba(255, 255, 255, 0.05); }
        .dd-id { font-weight: 600; }
        .dd-id .matched { color: var(--red); }
        .dd-meta { display: block; font-size: 12px; color: var(--muted); }
        .dd-empty { padding: 18px; text-align: center; color: var(--muted); }

        /* --- Badges ------------------------------------------------------- */
        .badge {
            display: inline-block; padding: 4px 9px; border-radius: 999px; border: 1px solid;
            font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
            white-space: nowrap; vertical-align: middle;
        }
        .badge-mon-compte { color: var(--green); background: rgba(52, 211, 153, 0.1); border-color: rgba(52, 211, 153, 0.35); }
        .badge-matchmaking { color: var(--red); background: rgba(255, 70, 85, 0.1); border-color: rgba(255, 70, 85, 0.35); }
        .badge-benchmark { color: var(--amber); background: rgba(251, 191, 36, 0.1); border-color: rgba(251, 191, 36, 0.35); }
        .badge-dataset-ml { color: var(--muted); background: rgba(127, 139, 163, 0.1); border-color: rgba(127, 139, 163, 0.3); }

        /* --- Structure ---------------------------------------------------- */
        .page { max-width: 1280px; margin: 0 auto; padding: 26px 28px 40px; }
        .card {
            position: relative; overflow: hidden;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            padding: 22px;
            backdrop-filter: blur(10px);
        }
        .card::before {
            content: ""; position: absolute; inset: 0 0 auto 0; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255, 70, 85, 0.55), transparent);
        }
        .section-title {
            font-family: var(--display); font-size: 15px; font-weight: 700;
            letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted);
            margin: 0 0 16px;
        }
        .eyebrow {
            font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted);
        }
        .empty { text-align: center; color: var(--muted); padding: 26px 10px; }
        .empty small { color: #5b6679; }

        /* --- Héros -------------------------------------------------------- */
        .hero { display: grid; grid-template-columns: 1.55fr 1fr; gap: 20px; }
        .hero-name {
            display: flex; align-items: center; flex-wrap: wrap; gap: 12px;
            font-family: var(--display); font-size: clamp(30px, 4vw, 44px); font-weight: 700; line-height: 1.1;
            margin: 8px 0 18px;
        }
        .rank-pill {
            display: inline-flex; align-items: center; gap: 14px;
            padding: 12px 18px; border-radius: 14px;
            background: linear-gradient(135deg, rgba(255, 70, 85, 0.2), rgba(34, 211, 238, 0.08));
            border: 1px solid rgba(255, 70, 85, 0.4);
            box-shadow: 0 0 36px rgba(255, 70, 85, 0.16);
        }
        .rank-pill b { font-family: var(--display); font-size: 24px; font-weight: 700; }
        .hero-meta { display: flex; gap: 22px; flex-wrap: wrap; margin-top: 18px; color: var(--muted); font-size: 13px; }
        .hero-meta b { color: var(--text); font-weight: 600; }
        .ring-wrap { display: flex; align-items: center; gap: 22px; height: 100%; }
        .ring { position: relative; width: 128px; height: 128px; flex-shrink: 0; }
        .ring svg { transform: rotate(-90deg); }
        .ring-value {
            position: absolute; inset: 0; display: grid; place-content: center; text-align: center;
            font-family: var(--display); font-size: 30px; font-weight: 700; line-height: 1;
        }
        .ring-value small { display: block; font-family: var(--body); font-size: 10px; letter-spacing: 0.14em; color: var(--muted); margin-top: 4px; }
        .ring-stats { display: grid; gap: 8px; font-size: 13px; color: var(--muted); }
        .ring-stats b { color: var(--text); font-family: var(--display); font-size: 22px; font-weight: 700; margin-right: 4px; }
        .win { color: var(--green); } .loss { color: #f87171; }

        /* --- KPI ---------------------------------------------------------- */
        .kpis { display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-top: 20px; }
        .kpi {
            position: relative; overflow: hidden;
            padding: 16px 16px 14px;
            background: var(--panel-2); border: 1px solid var(--line); border-radius: 14px;
        }
        .kpi::after {
            content: ""; position: absolute; left: 0; right: 0; top: 0; height: 2px;
            background: linear-gradient(90deg, var(--red), var(--cyan));
            opacity: 0.8;
        }
        .kpi-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
        .kpi-value { font-family: var(--display); font-size: 34px; font-weight: 700; margin-top: 4px; line-height: 1.1; }

        /* --- Onglets ------------------------------------------------------ */
        .tabs {
            display: inline-flex; gap: 4px; padding: 4px; margin: 26px 0 18px;
            background: rgba(255, 255, 255, 0.04); border: 1px solid var(--line); border-radius: 12px;
        }
        .tab {
            padding: 9px 18px; border: 0; border-radius: 9px; cursor: pointer;
            background: transparent; color: var(--muted); font: 600 13px var(--body);
            transition: color 0.2s, background 0.2s;
        }
        .tab:hover { color: var(--text); }
        .tab.active {
            color: #fff; background: linear-gradient(135deg, var(--red), var(--red-deep));
            box-shadow: 0 8px 24px rgba(255, 70, 85, 0.3);
        }

        /* --- Onglet 1 ----------------------------------------------------- */
        .layout { display: grid; grid-template-columns: 340px 1fr; gap: 20px; }
        .stack { display: grid; gap: 20px; align-content: start; }
        .body-card { text-align: center; }
        .body-card h4 { font-size: 15px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 14px; }

        .weapon {
            display: grid; grid-template-columns: 56px 1fr auto; gap: 16px; align-items: center;
            padding: 14px 16px; margin-bottom: 10px;
            background: var(--panel-2); border: 1px solid var(--line); border-radius: 14px;
            transition: transform 0.2s, border-color 0.2s;
        }
        .weapon:hover { transform: translateY(-2px); border-color: rgba(34, 211, 238, 0.35); }
        .weapon-icon {
            width: 56px; height: 44px; display: grid; place-items: center;
            background: rgba(255, 255, 255, 0.03); border-radius: 10px;
        }
        .weapon-icon img { max-width: 52px; max-height: 32px; object-fit: contain; filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.5)); }
        .weapon-name { font-family: var(--display); font-size: 19px; font-weight: 700; }
        .bar { height: 6px; margin: 8px 0 6px; border-radius: 99px; background: rgba(255, 255, 255, 0.06); overflow: hidden; }
        .bar i { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--cyan), var(--violet)); }
        .weapon-body small { color: var(--muted); font-size: 12px; }
        .weapon-kills { text-align: right; }
        .weapon-kills b { display: block; font-family: var(--display); font-size: 28px; font-weight: 700; line-height: 1; }
        .weapon-kills small { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; }

        .mmr-head { display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
        .mmr-sub { color: var(--muted); font-size: 13px; }
        .mmr-sub b { color: var(--text); }
        .mmr-chart { width: 100%; height: auto; display: block; }
        .mmr-legend { display: flex; gap: 16px; justify-content: flex-end; font-size: 12px; color: var(--muted); margin-top: 6px; }
        .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }

        /* --- Onglet 2 ----------------------------------------------------- */
        .coach-grid { display: grid; grid-template-columns: 1fr 1.25fr; gap: 20px; align-items: start; }
        .coach-rank { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
        .advice {
            padding: 16px 18px; margin-bottom: 12px; line-height: 1.6; font-size: 14px;
            background: var(--panel-2); border: 1px solid var(--line); border-radius: 14px;
        }
        .advice b { display: block; font-family: var(--display); font-size: 15px; letter-spacing: 0.06em; margin-bottom: 4px; }
        .advice.a1 { border-left: 3px solid var(--red); } .advice.a1 b { color: var(--red); }
        .advice.a2 { border-left: 3px solid var(--amber); } .advice.a2 b { color: var(--amber); }
        .advice.a3 { border-left: 3px solid var(--green); } .advice.a3 b { color: var(--green); }

        .chat { display: flex; flex-direction: column; height: 460px; }
        .messages { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 4px 6px 4px 2px; }
        .messages::-webkit-scrollbar { width: 6px; }
        .messages::-webkit-scrollbar-thumb { background: #243047; border-radius: 3px; }
        .bubble {
            max-width: 86%; padding: 12px 15px; font-size: 14px; line-height: 1.55;
            white-space: pre-line; border-radius: 14px;
        }
        .bubble.me {
            align-self: flex-end; color: #fff;
            background: linear-gradient(135deg, var(--red), var(--red-deep));
            border-bottom-right-radius: 4px;
        }
        .bubble.bot {
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.05); border: 1px solid var(--line);
            border-bottom-left-radius: 4px;
        }
        .bubble strong { color: #fff; }
        .chat-bar { display: flex; gap: 10px; margin-top: 14px; }
        .chat-bar input {
            flex: 1; min-width: 0; padding: 12px 16px; font: inherit;
            background: rgba(255, 255, 255, 0.04); color: var(--text);
            border: 1px solid var(--line); border-radius: 999px; outline: 0;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .chat-bar input:focus { border-color: rgba(34, 211, 238, 0.6); box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.12); }
        .chat-bar button {
            padding: 12px 20px; border: 0; border-radius: 999px; cursor: pointer;
            font: 600 14px var(--body); color: #fff;
            background: linear-gradient(135deg, var(--red), var(--red-deep));
            box-shadow: 0 8px 20px rgba(255, 70, 85, 0.25);
        }
        .chat-bar button:hover { filter: brightness(1.08); }

        .video-title { font-family: var(--display); font-size: 18px; font-weight: 700; margin: 0 0 12px; min-height: 26px; }
        .video-frame {
            position: relative; width: 100%; aspect-ratio: 16 / 9;
            border-radius: 12px; overflow: hidden; border: 1px solid var(--line);
            background: #000;
        }
        .video-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
        .video-source { margin-top: 10px; font-size: 12px; color: var(--muted); }

        /* --- Responsive --------------------------------------------------- */
        @media (max-width: 1100px) {
            .kpis { grid-template-columns: repeat(3, 1fr); }
            .hero, .layout, .coach-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 640px) {
            .topbar { flex-wrap: wrap; padding: 14px 16px; }
            .search { width: 100%; }
            .page { padding: 16px; }
            .kpis { grid-template-columns: repeat(2, 1fr); }
            .kpi-value { font-size: 28px; }
            .card { padding: 18px; }
            .ring-wrap { flex-direction: column; align-items: flex-start; }
            .chat { height: 400px; }
        }
    </style>
</head>
<body>
    <header class="topbar">
        <div class="brand">VALO<span class="slash">//</span>ORACLE <small>ML · PREVIEW</small></div>
        <div class="search" id="searchContainer">
            <div class="search-box">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                <input type="text" id="playerSearchInput" class="search-input" placeholder="Rechercher un joueur (ex : Nova#roma)" autocomplete="off" spellcheck="false">
                <button type="button" id="searchClearBtn" class="clear" onclick="clearPlayerSearch()" title="Effacer">&times;</button>
            </div>
            <div id="searchDropdown" class="dropdown"></div>
        </div>
    </header>

    <main class="page">
        <section class="hero">
            <div class="card">
                <div class="eyebrow">Joueur analysé · Oracle Database 23ai</div>
                <div class="hero-name">
                    <span>__RIOT_ID__</span>
                    <span class="badge __BADGE_CLASS__">__PTYPE__</span>
                </div>
                <div class="rank-pill">
                    <div>
                        <div class="eyebrow">Rang actuel</div>
                        <b>__RANK__</b>
                    </div>
                </div>
                <div class="hero-meta">
                    <span>Niveau <b>__LEVEL__</b></span>
                    <span><b>__PLAYERS_COUNT__</b> joueurs en base</span>
                    <span><b>__NB_MATCHS__</b> matchs analysés</span>
                </div>
            </div>

            <div class="card">
                <div class="ring-wrap">
                    <div class="ring">
                        <svg width="128" height="128" viewBox="0 0 128 128">
                            <circle cx="64" cy="64" r="50" fill="none" stroke="rgba(148,163,184,0.14)" stroke-width="10"/>
                            <circle cx="64" cy="64" r="50" fill="none" stroke="url(#winGrad)" stroke-width="10" stroke-linecap="round" stroke-dasharray="__RING_DASH__"/>
                            <defs>
                                <linearGradient id="winGrad" x1="0" y1="0" x2="1" y2="1">
                                    <stop offset="0%" stop-color="#34d399"/>
                                    <stop offset="100%" stop-color="#22d3ee"/>
                                </linearGradient>
                            </defs>
                        </svg>
                        <div class="ring-value">__WINRATE__%<small>WINRATE</small></div>
                    </div>
                    <div class="ring-stats">
                        <div><b class="win">__WINS__</b> victoires</div>
                        <div><b class="loss">__LOSSES__</b> défaites</div>
                    </div>
                </div>
            </div>
        </section>

        <section class="kpis">
            <div class="kpi"><div class="kpi-label">K/D</div><div class="kpi-value">__KD__</div></div>
            <div class="kpi"><div class="kpi-label">ADR</div><div class="kpi-value">__ADR__</div></div>
            <div class="kpi"><div class="kpi-label">ACS</div><div class="kpi-value">__ACS__</div></div>
            <div class="kpi"><div class="kpi-label">KAST</div><div class="kpi-value">__KAST__%</div></div>
            <div class="kpi"><div class="kpi-label">Headshot</div><div class="kpi-value">__HS__%</div></div>
            <div class="kpi"><div class="kpi-label">Matchs</div><div class="kpi-value">__NB_MATCHS__</div></div>
        </section>

        <nav class="tabs">
            <button id="btnTab1" class="tab active" onclick="switchTab('tab1')">Vue d'ensemble</button>
            <button id="btnTab2" class="tab" onclick="switchTab('tab2')">Coach IA</button>
        </nav>

        <div id="tab1Content">
            <div class="layout">
                <div class="card body-card">__MANNEQUIN__</div>
                <div class="stack">
                    <div class="card">
                        <h3 class="section-title">Top 3 armes · kills</h3>
                        __ARMES__
                    </div>
                    <div class="card">__MMR__</div>
                </div>
            </div>
        </div>

        <div id="tab2Content" style="display:none;">
            <div class="coach-grid">
                <div class="card">
                    <h3 class="section-title">Plan d'entraînement</h3>
                    <div class="coach-rank">
                        <span class="eyebrow">Niveau de jeu estimé par l'IA d'après tes stats</span>
                        <span class="rank-pill"><b>__COACH_RANK__</b></span>
                    </div>
                    <div class="advice a1"><b>Précision</b>__AXE1__</div>
                    <div class="advice a2"><b>Positionnement</b>__AXE2__</div>
                    <div class="advice a3"><b>Impact collectif</b>__AXE3__</div>
                </div>

                <div class="card">
                    <h3 class="section-title">Assistant coach</h3>
                    <div class="chat">
                        <div class="messages" id="chatMsgs">
                            <div class="bubble bot">Salut ! Je suis ton coach analytique relié à Oracle. J'analyse actuellement le joueur <strong>__RIOT_ID__</strong>. Pose-moi une question sur tes priorités, un agent, ou demande ton pire point faible.</div>
                        </div>
                        <div class="chat-bar">
                            <input type="text" id="chatInput" placeholder="Ex : Quel est mon point le plus faible ?" onkeydown="if(event.key==='Enter') sendMsg()">
                            <button onclick="sendMsg()">Envoyer</button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card" style="margin-top:20px;">
                <h3 class="section-title" id="vidTitle">Vidéo recommandée</h3>
                <div class="video-frame">
                    <iframe id="vidFrame" src="https://www.youtube.com/embed/JnA8WfGqZ9c" allowfullscreen title="Vidéo recommandée"></iframe>
                </div>
                <div id="vidSource" class="video-source">Source : top recommandation YouTube</div>
            </div>
        </div>
    </main>

    <script>
        function switchTab(tabId) {
            const onFirst = tabId === 'tab1';
            document.getElementById('tab1Content').style.display = onFirst ? 'block' : 'none';
            document.getElementById('tab2Content').style.display = onFirst ? 'none' : 'block';
            document.getElementById('btnTab1').classList.toggle('active', onFirst);
            document.getElementById('btnTab2').classList.toggle('active', !onFirst);
        }

        // Recherche et autocomplétion de tous les pseudos
        const searchInput = document.getElementById('playerSearchInput');
        const searchDropdown = document.getElementById('searchDropdown');
        const searchClearBtn = document.getElementById('searchClearBtn');
        const searchContainer = document.getElementById('searchContainer');
        let searchTimeout = null;
        let highlightedIndex = -1;
        let currentResults = [];

        function getBadgeClass(type) {
            if (type === 'MON_COMPTE') return 'badge-mon-compte';
            if (type === 'JOUEUR_MATCHMAKING') return 'badge-matchmaking';
            if (type === 'BENCHMARK') return 'badge-benchmark';
            return 'badge-dataset-ml';
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function highlightMatch(text, query) {
            if (!query) return escapeHtml(text);
            const idx = text.toLowerCase().indexOf(query.toLowerCase());
            if (idx === -1) return escapeHtml(text);
            const before = escapeHtml(text.substring(0, idx));
            const match = escapeHtml(text.substring(idx, idx + query.length));
            const after = escapeHtml(text.substring(idx + query.length));
            return before + '<span class="matched">' + match + '</span>' + after;
        }

        async function fetchPlayers(query = '') {
            try {
                const res = await fetch('/api/players?q=' + encodeURIComponent(query));
                const data = await res.json();
                currentResults = data;
                highlightedIndex = -1;
                renderDropdown(data, query);
            } catch (err) {
                console.error('Erreur lors de la récupération des joueurs :', err);
            }
        }

        function renderDropdown(players, query) {
            if (!players || players.length === 0) {
                searchDropdown.innerHTML = `<div class="dd-empty">Aucun joueur pour « ${escapeHtml(query)} »</div>`;
                searchDropdown.style.display = 'block';
                return;
            }

            const headerTitle = query ? 'Résultats' : 'Joueurs';
            const countLabel = players.length >= 30 ? '30+' : `${players.length}`;
            const headerHtml = `<div class="dd-head"><span>${headerTitle}</span><span>${countLabel}</span></div>`;

            const itemsHtml = players.map((p, idx) => {
                const badgeCls = getBadgeClass(p.type_profil);
                const metaParts = [p.rang_actuel ? escapeHtml(p.rang_actuel) : '', p.niveau_compte ? `Niv. ${p.niveau_compte}` : '']
                    .filter(Boolean).join(' · ');
                return `
                    <div class="dd-item" data-index="${idx}" onclick="selectPlayer('${escapeHtml(p.riot_id)}')">
                        <div>
                            <span class="dd-id">${highlightMatch(p.riot_id, query)}</span>
                            ${metaParts ? `<span class="dd-meta">${metaParts}</span>` : ''}
                        </div>
                        <span class="badge ${badgeCls}">${escapeHtml(p.type_profil)}</span>
                    </div>`;
            }).join('');

            searchDropdown.innerHTML = headerHtml + itemsHtml;
            searchDropdown.style.display = 'block';
        }

        function selectPlayer(riotId) {
            if (!riotId) return;
            window.location.href = '/?player=' + encodeURIComponent(riotId);
        }

        function clearPlayerSearch() {
            searchInput.value = '';
            searchClearBtn.style.display = 'none';
            searchInput.focus();
            fetchPlayers('');
        }

        searchInput.addEventListener('input', (e) => {
            const val = e.target.value.trim();
            searchClearBtn.style.display = val ? 'block' : 'none';
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => fetchPlayers(val), 150);
        });

        searchInput.addEventListener('focus', () => fetchPlayers(searchInput.value.trim()));

        searchInput.addEventListener('keydown', (e) => {
            const items = searchDropdown.querySelectorAll('.dd-item');
            if (items.length === 0 || searchDropdown.style.display === 'none') {
                if (e.key === 'Enter') {
                    const val = searchInput.value.trim();
                    if (val) selectPlayer(val);
                }
                return;
            }

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                highlightedIndex = (highlightedIndex + 1) % items.length;
                updateHighlighted(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                highlightedIndex = (highlightedIndex - 1 + items.length) % items.length;
                updateHighlighted(items);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (highlightedIndex >= 0 && highlightedIndex < currentResults.length) {
                    selectPlayer(currentResults[highlightedIndex].riot_id);
                } else if (currentResults.length > 0) {
                    selectPlayer(currentResults[0].riot_id);
                }
            } else if (e.key === 'Escape') {
                searchDropdown.style.display = 'none';
                highlightedIndex = -1;
            }
        });

        function updateHighlighted(items) {
            items.forEach((item, idx) => {
                item.classList.toggle('highlighted', idx === highlightedIndex);
                if (idx === highlightedIndex) item.scrollIntoView({ block: 'nearest' });
            });
        }

        document.addEventListener('click', (e) => {
            if (!searchContainer.contains(e.target)) {
                searchDropdown.style.display = 'none';
                highlightedIndex = -1;
            }
        });

        // Mise en forme légère des réponses du coach
        function formatChatMessage(text) {
            if (!text) return '';
            let formatted = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            formatted = formatted.replace(/__(.*?)__/g, '<strong>$1</strong>');
            formatted = formatted.replace(/(^|[^\*])\*(?!\*)(.*?)\*(?!\*)/g, '$1<em>$2</em>');
            formatted = formatted.replace(/\n\n/g, '<br><br>');
            formatted = formatted.replace(/\n/g, '<br>');
            return formatted;
        }

        async function sendMsg() {
            const input = document.getElementById('chatInput');
            const txt = input.value.trim();
            if (!txt) return;

            const box = document.getElementById('chatMsgs');
            const uMsg = document.createElement('div');
            uMsg.className = 'bubble me';
            uMsg.innerText = txt;
            box.appendChild(uMsg);
            input.value = '';
            box.scrollTop = box.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ riot_id: __JS_PLAYER__, question: txt })
                });
                const data = await res.json();

                const iaMsg = document.createElement('div');
                iaMsg.className = 'bubble bot';
                iaMsg.innerHTML = formatChatMessage(data.reponse);
                box.appendChild(iaMsg);
                box.scrollTop = box.scrollHeight;

                if (data.youtube_id) {
                    document.getElementById('vidFrame').src = 'https://www.youtube.com/embed/' + data.youtube_id;
                    document.getElementById('vidTitle').innerText = data.titre_video;
                    document.getElementById('vidSource').innerText = 'Source : ' + data.source;
                }
            } catch (e) {
                const err = document.createElement('div');
                err.className = 'bubble bot';
                err.innerText = 'Erreur de communication avec le serveur.';
                box.appendChild(err);
            }
        }
    </script>
</body>
</html>
"""


def render_dashboard(ctx: dict) -> str:
    """Remplit le gabarit. Les clés `mannequin`, `armes`, `mmr` sont déjà du HTML."""
    st = ctx["st"]
    coach = ctx["coach"]
    nb_matchs = int(st.get("nb_matchs") or 0)
    winrate = max(0.0, min(100.0, float(st.get("winrate") or 0)))
    wins = round(nb_matchs * winrate / 100)
    ring = 2 * math.pi * 50  # circonférence du cercle de rayon 50

    values = {
        "__RIOT_ID__": html_lib.escape(str(ctx["display_riot_id"])),
        "__BADGE_CLASS__": ctx["badge_class"],
        "__PTYPE__": html_lib.escape(str(ctx["ptype"])),
        "__RANK__": html_lib.escape(str(ctx.get("rank_label") or "-")),
        "__COACH_RANK__": html_lib.escape(str(coach.get("rang_predit_ml") or "-")),
        "__LEVEL__": html_lib.escape(str(ctx.get("level") or "-")),
        "__PLAYERS_COUNT__": html_lib.escape(str(ctx["total_players_cnt"])),
        "__NB_MATCHS__": str(nb_matchs),
        "__WINRATE__": f"{winrate:.0f}",
        "__WINS__": str(wins),
        "__LOSSES__": str(nb_matchs - wins),
        "__RING_DASH__": f"{ring * winrate / 100:.1f} {ring:.1f}",
        "__KD__": html_lib.escape(str(st.get("kd_moyen"))),
        "__ADR__": html_lib.escape(str(st.get("adr_moyen"))),
        "__ACS__": html_lib.escape(str(st.get("acs_moyen"))),
        "__KAST__": html_lib.escape(str(st.get("kast_moyen"))),
        "__HS__": html_lib.escape(str(st.get("hs_pct"))),
        "__AXE1__": html_lib.escape(str(coach.get("axe_viseur"))),
        "__AXE2__": html_lib.escape(str(coach.get("axe_positionnement"))),
        "__AXE3__": html_lib.escape(str(coach.get("axe_survie"))),
        "__MANNEQUIN__": ctx["mannequin_html"],
        "__ARMES__": ctx["armes_html"],
        "__MMR__": ctx["mmr_html"],
        "__JS_PLAYER__": ctx["js_selected_player"],
    }

    page = TEMPLATE
    for token, value in values.items():
        page = page.replace(token, value)
    return page
