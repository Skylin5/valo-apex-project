# Valorant Tracker & Oracle Machine Learning (APEX Dashboard)

Projet universitaire d'ingestion de données, d'analyse statistique et de Machine Learning in-database sous **Oracle 23ai Free** et **Oracle APEX**, inspiré des fonctionnalités de Tracker.gg.

Le pipeline récupère les matchs réels via l'API HenrikDev (v4 : rounds, kills, économie, joueurs), les enrichit (premiers kills, aces, KAST, précision par joueur, progression de rang) et les stocke dans Oracle. Des données de référence (dataset Kaggle) et le Random Forest `DBMS_DATA_MINING` estiment le rang mérité d'un joueur et proposent des axes de progression.

---

## Architecture et technologies

| Composant | Technologie | Rôle |
|---|---|---|
| Base de données | Oracle AI Database 23ai Free (`gvenzl/oracle-free:23-slim`) | Stockage et calcul, exécuté sous Docker |
| Moteur ML | Oracle Machine Learning (`DBMS_DATA_MINING`) | Modèles in-database |
| Pipeline d'ingestion | FastAPI / Python 3.11 (conteneurisé) | Récupération, calcul et insertion des données |
| Source de matchs | HenrikDev API v4 (`/v4/matches`) | Rounds, kills (tueur, victime, arme, assistants), économie, précision par joueur |
| Source de rang | HenrikDev API v2 (`/v2/mmr-history`) | Elo, RR gagnés ou perdus par match, palier |
| Restitution UI | Oracle APEX (cible finale) + serveur de prévisualisation local | Tableaux de bord et coaching |

### Modèles de Machine Learning

- **Classification (Random Forest)** : prédit le palier de niveau réel (`RANG_CIBLE_ML`) à partir des métriques en match (K/D, ADR, KAST %, DDΔ, répartition des tirs).
- **Clustering (K-Means)** : segmente les profils de jeu selon les rôles et les styles d'engagement.

---

## Fonctionnalités

### Pipeline d'ingestion (`/sync`)

- Enregistrement du compte principal (niveau et palier issus de ses propres données) et de tous les participants du lobby
- Récupération des matchs récents via l'API v4 (10 au maximum par appel, filtrables par mode)
- Calcul par match et par joueur : K/D, KAD, ADR, ACS, DDΔ, KPR, **KAST**, **premiers kills**, **aces**, **rounds parfaits (flawless)**, répartition tête/corps/jambes
- **Kills par arme** pour chaque joueur du lobby, en ne comptant que les kills avec une arme (capacités ignorées)
- **Progression de rang** du compte principal (table `valo_mmr_history`)
- Erreurs HTTP explicites (`404` compte introuvable, `429` quota atteint, `503` clé absente, `502` API injoignable)

> **Limites de l'API, à connaître :**
> - La précision par arme (tête/corps/jambes par arme) n'est **pas fournie** : les dégâts n'ont pas d'arme et les kills n'indiquent pas le headshot. Les colonnes correspondantes sont donc laissées vides, et l'interface l'indique.
> - L'historique des matchs v4 dépend de ce que l'API a stocké : certains matchs peuvent manquer.

### Client HenrikDev (`henrikdev.py`)

- Cache local de 60 secondes sur les réponses identiques
- Nouvel essai automatique sur `429`, avec attente selon `Retry-After` ou `X-RateLimit-Reset` (maximum 15 s)
- Attente préventive lorsque `X-RateLimit-Remaining` tombe à `0`
- Taille de page plafonnée à 10, comme l'impose l'API

Chaque appel coûte 1 au quota, plus 1 par match absent du cache serveur : une synchro de 10 matchs non stockés coûte donc environ 11 requêtes.

### Coach IA (`/coach/ask`)

- Chatbot accessible via endpoint POST avec contexte joueur (riot_id + question libre)
- Analyse du dernier match du joueur : rang ML prédit, point faible détecté (AIM / PLACEMENT)
- Recherche prioritaire dans la base Oracle (`VALO_COACH_VIDEOS`) par agent et type de ressource
- Fallback dynamique : recherche YouTube par scraping (sans clé API) si aucune vidéo référencée
- Réponse structurée avec vidéo YouTube intégrée, source et diagnostic personnalisé

### Dashboard Oracle APEX (régions PL/SQL)

- **Onglet 1 : Overview** : bandeau KPIs, silhouette colorée selon la précision par rapport au lobby, top 3 armes par kills, top agents par carte
- **Onglet 2 : Coach IA** : programme d'entraînement sur 3 axes (précision, positionnement, impact collectif), diagnostic par arme (top 3)
- Les régions s'appuient sur les vues `v_apex_overview`, `v_apex_top_weapons`, `v_apex_accuracy_compare` et `v_apex_coach_ia`

> La progression de rang n'est **pas encore** affichée dans les régions APEX : seule la version de prévisualisation la montre.

### Enrichissement des données d'entraînement ML

- Import du dataset Kaggle (`valorant_games.csv`) avec mapping des rangs vers le référentiel Oracle
- Génération de profils synthétiques (Fer / Bronze) par distribution gaussienne pour équilibrer les classes basses
- Nettoyage et isolation des profils ML (`DATASET_ML`) via `clean_profiles.py`
- Ré-entraînement à la demande du Random Forest avec 50 arbres (`retrain.py`)

### Base de données vidéo coaching

- Table relationnelle `VALO_COACH_VIDEOS` avec 11 ressources fondamentales
- Couverture : mécaniques débutant (crosshair placement, deadzoning, slice the pie), mécaniques intermédiaire (peeking), économie, guides agents (Sage, Jett, Reyna, Omen, Sova, Killjoy)
- Script de peuplement autonome (`setup_videos.py`)

### Prévisualisation locale

- Serveur HTTP autonome reproduisant le dashboard APEX (2 onglets), avec un thème sombre
- Recherche de joueurs avec autocomplétion (clavier et souris)
- Courbe de progression de rang (elo par match, points verts ou rouges selon le gain ou la perte de RR)
- Chat coach interactif avec recherche vidéo dynamique YouTube
- Diagnostic intelligent : détection d'intention (priorité, agent spécifique, question libre)

---

## Arborescence du projet

```text
valo-apex-project/
├── .gitignore
├── docker-compose.yml                # Orchestration Oracle 23ai + FastAPI
├── README.md
│
├── init_db/                          # Scripts SQL joués au démarrage du conteneur Oracle
│   ├── 01_schema_and_seed.sql        # Schéma relationnel, contraintes, seeds
│   ├── 02_oracle_ml_and_views.sql    # Modèles OML (Random Forest, K-Means) et vues APEX
│   ├── 03_v4_migration.sql           # Colonne saison + table valo_mmr_history (API v4)
│   └── patches/
│       └── 01_views_top_weapons_accuracy.sql   # Mise à jour des vues top armes et précision (rejouable)
│
├── python_sync/                      # Microservice d'ingestion (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                        # Point d'entrée FastAPI (routeurs uniquement)
│   ├── config.py                     # Variables d'environnement et constantes (mapping agent → rôle)
│   ├── database.py                   # Pool de connexions Oracle (singleton)
│   ├── henrikdev.py                  # Client HenrikDev v4/matches + v2/mmr-history
│   ├── youtube.py                    # Recherche YouTube (scraping léger)
│   ├── routes/
│   │   ├── sync.py                   # GET /sync/{region}/{pseudo}/{tag}
│   │   └── coach.py                  # POST /coach/ask
│   ├── services/
│   │   ├── sync_service.py           # Orchestration de la synchro (HenrikDev → Oracle)
│   │   ├── match_parser.py           # Parsing d'un match v4 : kills par arme, premiers kills, aces, KAST, flawless
│   │   └── mmr_parser.py             # Parsing de l'historique MMR
│   ├── repositories/                 # Requêtes Oracle : players.py, matches.py, weapons.py, mmr.py
│   └── tests/
│       ├── test_match_parser.py      # Tests du parsing (sans réseau)
│       └── test_henrikdev.py         # Tests du client HTTP (réseau simulé)
│
├── apex_ui/
│   └── regions_html_plsql.sql        # 3 blocs PL/SQL pour régions APEX (overview, coach)
│
├── data/                             # Scripts d'enrichissement et maintenance des données
│   ├── db_utils.py                   # Connexion Oracle partagée (variables d'env)
│   ├── valorant_games.csv            # Dataset Kaggle brut
│   ├── import_and_augment.py         # Import Kaggle + génération synthétique Fer/Bronze
│   ├── clean_profiles.py             # Isolation des profils d'entraînement ML
│   ├── retrain.py                    # Ré-entraînement du Random Forest (50 arbres)
│   └── setup_videos.py               # Peuplement de la table VALO_COACH_VIDEOS
│
└── a_supprimer_apres/                # [TEMPORAIRE] À supprimer après raccordement APEX
    ├── preview_app.py                # Serveur HTTP local : données, routes et calculs de l'affichage
    └── dashboard_template.py         # Gabarit HTML/CSS/JS du dashboard (thème sombre)
```

---

## Installation et démarrage rapide

### Prérequis

- Docker Desktop installé et lancé (avec intégration WSL2 sous Windows)
- Git
- Clé API HenrikDev (gratuite) : https://api.henrikdev.xyz/dashboard

### 1. Cloner le dépôt

```bash
git clone <URL_DU_DEPOT_GIT>
cd valo-apex-project
```

### 2. Configurer la clé API

Créer un fichier `.env` à la racine du projet :

```bash
HENRIKDEV_API_KEY=ta_cle_henrikdev_ici
```

Le `docker-compose.yml` lit cette variable via `${HENRIKDEV_API_KEY:-HDEV-REMPLACE-MOI}`. Sans clé valide, `/sync` répond `503`.

### 3. Démarrer les conteneurs

```bash
docker compose up -d --build
```

> **Note :** au premier lancement, le conteneur Oracle exécute automatiquement les scripts de `init_db/` (01, 02 puis 03). Cette étape prend entre 1 et 2 minutes.
>
> Sur une base **déjà créée**, ces scripts ne se rejouent pas : voir la section *Mettre à jour une base existante*.

Vérifier la bonne santé des conteneurs :

```bash
docker ps
```

---

## Mettre à jour une base existante

Les scripts de `init_db/` ne s'exécutent qu'à la création du volume Oracle. Pour une base déjà en place :

| Script | Quand le jouer | Rejouable ? |
|---|---|---|
| `03_v4_migration.sql` | Une seule fois (ajoute la colonne `saison` et la table `valo_mmr_history`) | Non |
| `patches/01_views_top_weapons_accuracy.sql` | À chaque évolution des vues top armes et précision | Oui |

Exemple PowerShell (depuis la racine du projet) :

```powershell
docker exec -i valo-oracle-db sqlplus -S valo_app/ValoPassword123@//localhost:1521/FREEPDB1 "@/container-entrypoint-initdb.d/03_v4_migration.sql"
```

Si la migration a déjà été jouée, SQL*Plus renvoie « name is already used by an existing object » : ne la relancez pas.

Pour supprimer les données d'un joueur (par exemple après une ancienne synchro faussée) :

```powershell
@"
DELETE FROM valo_stats_armes WHERE LOWER(riot_id) = 'nova#roma';
DELETE FROM valo_matchs_stats WHERE LOWER(riot_id) = 'nova#roma';
COMMIT;
EXIT;
"@ | docker exec -i valo-oracle-db sqlplus -S valo_app/ValoPassword123@//localhost:1521/FREEPDB1
```

---

## Utilisation du pipeline d'ingestion

Une fois les conteneurs démarrés, l'API FastAPI est accessible sur le port `8000`.

### Synchroniser un joueur

1. Ouvre l'interface Swagger : <http://localhost:8000/docs>
2. Déplie l'endpoint `GET /sync/{region}/{pseudo}/{tag}` et clique sur **Try it out**.
3. Renseigne les paramètres :
   - `region` : `eu`, `na`, `ap` ou `kr`
   - `pseudo` : ton pseudo Valorant (ex : `Nova`)
   - `tag` : ton tag sans le `#` (ex : `roma`)
   - `playlist` : `competitive` ou `unrated` (filtre le mode de jeu)
   - `platform` : `pc` (par défaut) ou `console`
   - `size` : nombre de matchs, 10 au maximum
4. Clique sur **Execute**.

Ou en ligne de commande :

```powershell
curl "http://localhost:8000/sync/eu/nova/roma?playlist=competitive&platform=pc"
```

La réponse indique le nombre de matchs analysés, les performances insérées, les entrées MMR ajoutées et un éventuel `avertissement_mmr` si l'historique de rang n'a pas pu être récupéré.

### Utiliser le Coach IA

1. Déplie l'endpoint `POST /coach/ask` dans Swagger.
2. Envoie un corps JSON :
   ```json
   {
     "riot_id": "Nova#roma",
     "question": "Quel est mon point le plus faible ?"
   }
   ```
3. La réponse inclut un diagnostic personnalisé, une vidéo YouTube recommandée et la source utilisée (base Oracle ou recherche dynamique).

### Vérifier l'état du service

```bash
curl http://localhost:8000/health
```

---

## Enrichissement des données ML

Les scripts du dossier `data/` permettent d'enrichir le jeu d'entraînement et de ré-entraîner les modèles :

```bash
# 1. Importer le dataset Kaggle + générer des profils synthétiques Fer/Bronze
python data/import_and_augment.py

# 2. Isoler les profils d'entraînement pour ne pas polluer les stats joueurs
python data/clean_profiles.py

# 3. Ré-entraîner le Random Forest avec les nouvelles données
python data/retrain.py

# 4. (Optionnel) Recréer la table de vidéos coaching
python data/setup_videos.py
```

> **Pré-requis Python :** `pip install oracledb numpy`

---

## Tests

Les tests du pipeline sont dans `python_sync/tests/`. Ils ne nécessitent ni Oracle ni clé API.

```powershell
cd python_sync
python -m unittest discover -s tests -v
```

- `test_match_parser.py` (12 tests) : kills par arme, premiers kills, aces, KAST, flawless, valeurs de ligne SQL, correspondance des rangs, historique MMR.
- `test_henrikdev.py` (7 tests) : clé absente, URL et plafond de taille, erreurs `404` et `429`, nouvel essai après `429`, cache.

Le second fichier est ignoré (`skipped`) si le paquet `requests` n'est pas installé dans l'environnement : c'est normal, il ne sert qu'aux tests du client HTTP. Pour le lancer : `pip install requests`.

---

## Prévisualisation locale (en attendant Oracle APEX)

Un serveur léger et autonome permet de visualiser le dashboard sans configurer APEX localement :

```powershell
# Depuis la racine du projet, dans ton environnement virtuel Python
pip install oracledb
python a_supprimer_apres/preview_app.py
```

Accède ensuite à <http://localhost:5000/?player=nova%23roma> (le `#` s'écrit `%23` dans l'URL).

- **Vue d'ensemble** : carte joueur avec palier estimé et taux de victoire, six KPI, silhouette colorée selon la précision par rapport au lobby, top 3 armes par kills, courbe de progression de rang.
- **Coach IA** : palier prédit par le Random Forest OML, plan d'entraînement sur 3 axes et assistant coach vidéo interactif avec recommandations YouTube.

---

## Ce qu'il reste à faire

### 1. Intégration du jeu de données Kaggle complet

**Objectif :** remplacer le seed partiel de `kaggle_ref_armes` par un import massif du dataset Kaggle Valorant (prix, cadences, profils de recul, dégâts selon la portée).

**Action :** ajouter un script SQL ou un loader Python dans `init_db/` pour insérer l'intégralité du catalogue d'armes et les statistiques de distribution des rangs.

### 2. Déploiement sur l'instance APEX de l'école

1. Se connecter au workspace APEX universitaire.
2. Créer les tables et vues en exécutant `01_schema_and_seed.sql`, `02_oracle_ml_and_views.sql` puis `03_v4_migration.sql` dans le **SQL Workshop**.
3. Monter l'application APEX :
   - **Page 1 : Dashboard de synthèse** (cartes, graphiques en anneau pour la précision, région HTML/CSS pour la silhouette, courbe de rang à ajouter).
   - **Page 2 : Interface de coaching** (régions de contenu basées sur la vue `v_apex_coach_ia`).
4. Raccorder le bouton d'actualisation de la page APEX à un appel REST vers l'API FastAPI, ou exécuter le script de synchro en tâche de fond.

### 3. Nettoyage du code temporaire

Une fois les écrans validés dans APEX, supprimer le dossier temporaire :

```powershell
Remove-Item -Recurse a_supprimer_apres
```

### 4. Points à vérifier

- **Dépendance `curl_cffi`** : listée dans `requirements.txt`, elle n'est plus utilisée par la synchro. À retirer si `youtube.py` et `coach.py` ne l'utilisent pas non plus.
- **Noms de modes** : le filtre `playlist` accepte les noms des modes de l'API (`competitive`, `unrated`). À confirmer sur un vrai appel.
- **Correspondance des tours** : `kills[].round` et `rounds[].id` sont supposés suivre la même numérotation. À confirmer sur une réponse réelle.

---

## Pistes d'amélioration

- **Automatisation de l'ingestion** : planificateur (cron ou `DBMS_SCHEDULER`) pour interroger l'API après chaque session de jeu.
- **Raffinement des hyperparamètres OML** :
  - Augmenter le nombre d'arbres du Random Forest (`TREE_NUM_TREES`).
  - Expérimenter un modèle XGBoost natif Oracle 23ai pour affiner la prédiction du rang.
- **Économie par round** : rentabilité des achats (arme et armure achetées, crédits dépensés), disponibles dans `rounds[].stats[].economy`.
- **Historique des saisons** : comparer les performances d'un acte à l'autre grâce à la colonne `saison`.
- **Export PDF / Rapport** : exploiter les fonctions d'impression d'Oracle APEX pour exporter une fiche de débriefing de match personnalisée.
