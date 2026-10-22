-- Patch : met à jour les vues du top 3 armes et de la comparaison de précision vs lobby.
-- À jouer une fois sur une base existante (rejouable). Ignoré par Docker (sous-dossier).

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

EXIT;
