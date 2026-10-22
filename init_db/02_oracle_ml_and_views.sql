ALTER SESSION SET CONTAINER = FREEPDB1;
ALTER SESSION SET CURRENT_SCHEMA = valo_app;

-- ============================================================================
-- 1. ENTRAÎNEMENT DES MODÈLES ORACLE MACHINE LEARNING (DBMS_DATA_MINING)
-- ============================================================================
CREATE TABLE valo_ml_settings (
    setting_name  VARCHAR2(30),
    setting_value VARCHAR2(4000)
);

-- Configuration du modèle 1 : Classification (Random Forest)
INSERT INTO valo_ml_settings VALUES ('ALGO_NAME', 'ALGO_RANDOM_FOREST');
INSERT INTO valo_ml_settings VALUES ('PREP_AUTO', 'ON');
COMMIT;

CREATE OR REPLACE VIEW v_ml_training_data AS
SELECT
    id_perf,
    head_pct,
    body_pct,
    leg_pct,
    adr,
    kd_ratio,
    kast_pct,
    dd_delta,
    rang_cible_ml
FROM valo_matchs_stats
WHERE rang_cible_ml IS NOT NULL;

BEGIN
    BEGIN
        DBMS_DATA_MINING.DROP_MODEL('MOD_PRED_RANG_VALO');
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    DBMS_DATA_MINING.CREATE_MODEL(
        model_name          => 'MOD_PRED_RANG_VALO',
        mining_function     => dbms_data_mining.classification,
        data_table_name     => 'V_ML_TRAINING_DATA',
        case_id_column_name => 'ID_PERF',
        target_column_name  => 'RANG_CIBLE_ML',
        settings_table_name => 'VALO_ML_SETTINGS'
    );
END;
/

-- Configuration du modèle 2 : Clustering K-Means
TRUNCATE TABLE valo_ml_settings;
INSERT INTO valo_ml_settings VALUES ('ALGO_NAME', 'ALGO_KMEANS');
INSERT INTO valo_ml_settings VALUES ('CLUS_NUM_CLUSTERS', '4');
INSERT INTO valo_ml_settings VALUES ('PREP_AUTO', 'ON');
COMMIT;

BEGIN
    BEGIN
        DBMS_DATA_MINING.DROP_MODEL('MOD_CLUSTER_STYLE_VALO');
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    DBMS_DATA_MINING.CREATE_MODEL(
        model_name          => 'MOD_CLUSTER_STYLE_VALO',
        mining_function     => dbms_data_mining.clustering,
        data_table_name     => 'V_ML_TRAINING_DATA',
        case_id_column_name => 'ID_PERF',
        settings_table_name => 'VALO_ML_SETTINGS'
    );
END;
/

-- ============================================================================
-- 2. VUE ONGLET 1 : BANDEAU OVERVIEW + SILHOUETTE ACCURACY + RANG PRÉDIT OML
-- ============================================================================
CREATE OR REPLACE VIEW v_apex_overview AS
SELECT
    j.riot_id,
    j.niveau_compte,
    j.rang_actuel,
    COUNT(m.id_perf) AS nb_matchs,
    SUM(m.victoire) AS wins,
    COUNT(m.id_perf) - SUM(m.victoire) AS losses,
    ROUND((SUM(m.victoire) / NULLIF(COUNT(m.id_perf), 0)) * 100, 1) AS win_pct,
    ROUND(AVG(m.adr), 1) AS damage_per_round,
    ROUND(SUM(m.kills) / NULLIF(SUM(m.deaths), 0), 2) AS kd_ratio,
    ROUND((SUM(m.kills) + SUM(m.assists)) / NULLIF(SUM(m.deaths), 0), 2) AS kad_ratio,
    ROUND(AVG(m.kast_pct), 1) AS kast_pct,
    ROUND(AVG(m.dd_delta), 0) AS dd_delta_round,
    SUM(m.kills) AS total_kills,
    SUM(m.deaths) AS total_deaths,
    SUM(m.assists) AS total_assists,
    ROUND(AVG(m.acs), 1) AS acs_moyen,
    ROUND(AVG(m.kills_per_round), 1) AS kills_per_round,
    SUM(m.first_bloods) AS first_bloods,
    SUM(m.flawless_rounds) AS flawless_rounds,
    SUM(m.aces) AS aces,
    SUM(m.head_hits) AS head_hits,
    SUM(m.body_hits) AS body_hits,
    SUM(m.leg_hits) AS leg_hits,
    ROUND((SUM(m.head_hits) / NULLIF(SUM(m.head_hits + m.body_hits + m.leg_hits), 0)) * 100, 1) AS head_pct,
    ROUND((SUM(m.body_hits) / NULLIF(SUM(m.head_hits + m.body_hits + m.leg_hits), 0)) * 100, 1) AS body_pct,
    ROUND((SUM(m.leg_hits)  / NULLIF(SUM(m.head_hits + m.body_hits + m.leg_hits), 0)) * 100, 1) AS leg_pct,
    STATS_MODE(PREDICTION(MOD_PRED_RANG_VALO USING m.head_pct, m.body_pct, m.leg_pct, m.adr, m.kd_ratio, m.kast_pct, m.dd_delta)) AS rang_merite_ia
FROM valo_joueurs j
JOIN valo_matchs_stats m ON j.riot_id = m.riot_id
GROUP BY j.riot_id, j.niveau_compte, j.rang_actuel;

-- ============================================================================
-- 3. VUE ONGLET 1 : TOP AGENTS
-- ============================================================================
CREATE OR REPLACE VIEW v_apex_top_agents AS
SELECT
    riot_id,
    agent,
    role_agent,
    COUNT(*) AS matches,
    ROUND((SUM(victoire) / COUNT(*)) * 100, 1) AS win_pct,
    ROUND(SUM(kills) / NULLIF(SUM(deaths), 0), 2) AS kd_ratio,
    ROUND(AVG(adr), 1) AS adr,
    ROUND(AVG(acs), 1) AS acs,
    ROUND(AVG(dd_delta), 0) AS dd_delta,
    STATS_MODE(carte) AS best_map
FROM valo_matchs_stats
GROUP BY riot_id, agent, role_agent;

-- ============================================================================
-- 4. VUE ONGLET 1 & 2 : TOP WEAPONS + CROISEMENT KAGGLE
-- ============================================================================
CREATE OR REPLACE VIEW v_apex_top_weapons AS
SELECT
    sa.riot_id,
    sa.nom_arme,
    k.categorie_arme,
    k.image_url,
    sa.kills,
    sa.head_pct,
    sa.body_pct,
    sa.leg_pct,
    sa.adr_arme,
    k.dmg_tete_0_30m,
    k.dmg_corps_0_30m,
    k.dmg_jambes_0_30m,
    ROUND(
        (sa.head_pct / 100) * k.dmg_tete_0_30m +
        (sa.body_pct / 100) * k.dmg_corps_0_30m +
        (sa.leg_pct  / 100) * k.dmg_jambes_0_30m, 1
    ) AS degats_moyens_par_balle,
    ROUND(sa.kills / NULLIF(SUM(sa.kills) OVER (PARTITION BY sa.riot_id), 0) * 100, 1) AS part_kills_pct,
    ROW_NUMBER() OVER (PARTITION BY sa.riot_id ORDER BY sa.kills DESC, sa.nom_arme) AS rang_arme,
    CASE
        WHEN sa.head_pct IS NULL THEN
            sa.kills || ' kills avec cette arme : la précision par arme n''est pas fournie par l''API, voir la silhouette globale.'
        WHEN sa.nom_arme IN ('Vandal', 'Phantom') AND sa.head_pct < 18 THEN
            'PRIORITÉ HAUTE : ' || sa.body_pct || '% de tirs au corps (' || k.dmg_corps_0_30m || ' dmg au lieu de ' || k.dmg_tete_0_30m || ' en tête). Arrête le spray continu après 3 balles.'
        WHEN sa.nom_arme = 'Sheriff' AND sa.leg_pct > 15 THEN
            'ATTENTION : ' || sa.leg_pct || '% de tirs dans les pieds au Sheriff. Pose ton viseur plus haut et attends 0.3s entre chaque balle.'
        WHEN sa.head_pct >= 25 THEN
            'EXCELLENT : ' || sa.head_pct || '% de Headshots sur cette arme (Niveau Or/Platine atteint).'
        ELSE
            'EN PROGRESSION : Vise +4% de tirs tête pour passer le cap du palier supérieur.'
    END AS conseil_arme_ia
FROM valo_stats_armes sa
JOIN kaggle_ref_armes k ON sa.nom_arme = k.nom_arme;

-- ============================================================================
-- 4b. VUE ONGLET 1 : PRÉCISION DU JOUEUR COMPARÉE AU LOBBY (couleurs de la silhouette)
--     Le lobby = tous les autres joueurs enregistrés dans valo_matchs_stats.
-- ============================================================================
CREATE OR REPLACE VIEW v_apex_accuracy_compare AS
SELECT
    j.riot_id,
    ROUND(100 * SUM(m.head_hits) / NULLIF(SUM(m.head_hits + m.body_hits + m.leg_hits), 0), 1) AS head_pct,
    ROUND(100 * SUM(m.body_hits) / NULLIF(SUM(m.head_hits + m.body_hits + m.leg_hits), 0), 1) AS body_pct,
    ROUND(100 * SUM(m.leg_hits)  / NULLIF(SUM(m.head_hits + m.body_hits + m.leg_hits), 0), 1) AS leg_pct,
    (SELECT ROUND(100 * SUM(o.head_hits) / NULLIF(SUM(o.head_hits + o.body_hits + o.leg_hits), 0), 1)
       FROM valo_matchs_stats o WHERE o.riot_id <> j.riot_id) AS lobby_head_pct,
    (SELECT ROUND(100 * SUM(o.body_hits) / NULLIF(SUM(o.head_hits + o.body_hits + o.leg_hits), 0), 1)
       FROM valo_matchs_stats o WHERE o.riot_id <> j.riot_id) AS lobby_body_pct,
    (SELECT ROUND(100 * SUM(o.leg_hits) / NULLIF(SUM(o.head_hits + o.body_hits + o.leg_hits), 0), 1)
       FROM valo_matchs_stats o WHERE o.riot_id <> j.riot_id) AS lobby_leg_pct
FROM valo_joueurs j
JOIN valo_matchs_stats m ON j.riot_id = m.riot_id
GROUP BY j.riot_id;

-- ============================================================================
-- 5. VUE ONGLET 2 : "SUR QUOI TAFFER"
-- ============================================================================
CREATE OR REPLACE VIEW v_apex_coach_ia AS
WITH stats_joueur AS (
    SELECT * FROM v_apex_overview
),
cible_bronze_argent AS (
    SELECT
        ROUND(AVG(head_pct), 1) AS cible_hs,
        ROUND(AVG(body_pct), 1) AS cible_body,
        ROUND(AVG(adr), 1)      AS cible_adr,
        ROUND(AVG(kd_ratio), 2) AS cible_kd,
        ROUND(AVG(kast_pct), 1) AS cible_kast,
        ROUND(AVG(dd_delta), 0) AS cible_dd
    FROM valo_matchs_stats
    WHERE rang_cible_ml IN ('3 - Bronze', '4 - Argent')
)
SELECT
    j.riot_id,
    j.rang_actuel,
    j.rang_merite_ia,
    j.head_pct AS mon_hs_pct,
    c.cible_hs AS objectif_hs_pct,
    CASE
        WHEN j.head_pct < c.cible_hs THEN
            'AXE N°1 (VISEUR) : Ton HS% global est de ' || j.head_pct || '% (' || j.body_pct || '% dans le corps). L''objectif Bronze/Argent est de ' || c.cible_hs || '%. Travaille le placement de viseur à hauteur de tête en Deathmatch avec la Vandal et le Sheriff.'
        ELSE
            'VALIDÉ : Ton HS% (' || j.head_pct || '%) dépasse déjà la cible Bronze/Argent (' || c.cible_hs || '%).'
    END AS reco_precision,
    j.dd_delta_round AS mon_dd_delta,
    c.cible_dd       AS objectif_dd_delta,
    CASE
        WHEN j.dd_delta_round < 0 THEN
            'AXE N°2 (POSITIONNEMENT) : Ton DDΔ/Round est de ' || j.dd_delta_round || ' (notamment -17 avec Sage). Tu subis plus de dégâts que tu n''en infliges. Joue plus couvert et utilise tes compétences avant de prendre un duel.'
        ELSE
            'VALIDÉ : Ton différentiel de dégâts (' || j.dd_delta_round || ') est positif.'
    END AS reco_positionnement,
    j.kast_pct AS mon_kast_pct,
    c.cible_kast AS objectif_kast_pct,
    CASE
        WHEN j.kast_pct >= c.cible_kast AND j.kd_ratio >= 1.0 THEN
            'POINT FORT DÉTECTÉ : Ton K/D (' || j.kd_ratio || ') et ton KAST (' || j.kast_pct || '%) sont déjà au niveau Argent ! Tu as un excellent impact collectif.'
        ELSE
            'AXE N°3 (SURVIE) : Cherche le trade avec tes alliés pour maintenir un KAST supérieur à ' || c.cible_kast || '%.'
    END AS reco_collectif
FROM stats_joueur j
CROSS JOIN cible_bronze_argent c;