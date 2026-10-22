DECLARE
    r v_apex_overview%ROWTYPE;
    a v_apex_accuracy_compare%ROWTYPE;

    -- Couleur d'une zone de la silhouette selon l'écart (±10 %) avec la moyenne du lobby :
    -- vert = mieux que le lobby, rouge = moins bien, jaune = comparable, gris = pas de comparaison.
    -- Pour la tête, plus c'est haut mieux c'est ; pour le corps et les jambes, l'inverse.
    FUNCTION zone_color(p_val NUMBER, p_lobby NUMBER, p_higher_is_better BOOLEAN) RETURN VARCHAR2 IS
        v_ecart NUMBER;
    BEGIN
        IF p_val IS NULL OR p_lobby IS NULL OR p_lobby = 0 THEN
            RETURN '#95a5a6';
        END IF;
        v_ecart := (p_val - p_lobby) / p_lobby * 100;
        IF ABS(v_ecart) < 10 THEN
            RETURN '#f1c40f';
        END IF;
        RETURN CASE WHEN (v_ecart > 0) = p_higher_is_better THEN '#2ecc71' ELSE '#e74c3c' END;
    END zone_color;
BEGIN
    SELECT * INTO r FROM v_apex_overview WHERE LOWER(riot_id) = LOWER(NVL(:P1_RIOT_ID, 'MonCompte#EUW')) FETCH FIRST 1 ROWS ONLY;
    SELECT * INTO a FROM v_apex_accuracy_compare WHERE LOWER(riot_id) = LOWER(r.riot_id);

    HTP.P('<div style="background:#0f1923; color:#ece8e1; padding:20px; border-radius:12px; font-family:sans-serif;">');
    HTP.P('<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #2b3848; padding-bottom:12px; margin-bottom:16px;">');
    HTP.P('  <div><h2 style="margin:0; color:#ff4655;">' || APEX_ESCAPE.HTML(r.riot_id) || ' — LEVEL ' || r.niveau_compte || '</h2>');
    HTP.P('  <span style="color:#8b978f;">Bilan : <b style="color:#2ecc71;">' || r.wins || 'W</b> - <b style="color:#e74c3c;">' || r.losses || 'L</b> (' || r.win_pct || '% WR)</span></div>');
    HTP.P('  <div style="background:#1f2b38; padding:10px 16px; border-radius:8px; border-left:4px solid #2ecc71;">');
    HTP.P('    <small style="color:#8b978f;">RANG MÉRITÉ (ORACLE ML)</small><br><b style="font-size:18px; color:#2ecc71;">' || r.rang_merite_ia || '</b>');
    HTP.P('  </div>');
    HTP.P('</div>');

    -- Grille des 8 KPIs exacts inspirés de Tracker.gg
    HTP.P('<div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:20px;">');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">Damage/Round</small><br><b style="font-size:22px;">' || r.damage_per_round || '</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">K/D Ratio</small><br><b style="font-size:22px;">' || r.kd_ratio || '</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">Headshot %</small><br><b style="font-size:22px;">' || r.head_pct || '%</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">KAST</small><br><b style="font-size:22px;">' || r.kast_pct || '%</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">DDΔ/Round</small><br><b style="font-size:20px;">' || r.dd_delta_round || '</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">ACS</small><br><b style="font-size:20px;">' || r.acs_moyen || '</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">KAD Ratio</small><br><b style="font-size:20px;">' || r.kad_ratio || '</b></div>');
    HTP.P('  <div style="background:#1a242d; padding:12px; border-radius:8px;"><small style="color:#8b978f;">First Bloods / Flawless</small><br><b style="font-size:20px;">' || r.first_bloods || ' / ' || r.flawless_rounds || '</b></div>');
    HTP.P('</div>');

    -- Bloc ACCURACY avec Mannequin SVG dynamique (Tête / Corps / Jambes)
    HTP.P('<div style="background:#1a242d; padding:16px; border-radius:10px; display:flex; align-items:center; gap:24px;">');
    HTP.P('  <svg width="70" height="140" viewBox="0 0 70 140">');
    -- Tête
    HTP.P('    <circle cx="35" cy="18" r="12" fill="' || zone_color(a.head_pct, a.lobby_head_pct, TRUE) || '"/>');
    -- Corps (Torse + Bras)
    HTP.P('    <rect x="20" y="34" width="30" height="48" rx="5" fill="' || zone_color(a.body_pct, a.lobby_body_pct, FALSE) || '"/>');
    HTP.P('    <rect x="8" y="34" width="9" height="42" rx="4" fill="' || zone_color(a.body_pct, a.lobby_body_pct, FALSE) || '"/>');
    HTP.P('    <rect x="53" y="34" width="9" height="42" rx="4" fill="' || zone_color(a.body_pct, a.lobby_body_pct, FALSE) || '"/>');
    -- Jambes
    HTP.P('    <rect x="21" y="86" width="12" height="48" rx="4" fill="' || zone_color(a.leg_pct, a.lobby_leg_pct, FALSE) || '"/>');
    HTP.P('    <rect x="37" y="86" width="12" height="48" rx="4" fill="' || zone_color(a.leg_pct, a.lobby_leg_pct, FALSE) || '"/>');
    HTP.P('  </svg>');
    HTP.P('  <div style="flex:1;">');
    HTP.P('    <h4 style="margin:0 0 10px 0; color:#ece8e1;">ACCURACY (Derniers Matchs, vs lobby)</h4>');
    HTP.P('    <div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span>Head</span><b>' || r.head_pct || '%</b><span style="color:#8b978f;">lobby ' || NVL(TO_CHAR(a.lobby_head_pct), '-') || '% · ' || r.head_hits || ' Hits</span></div>');
    HTP.P('    <div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span>Body</span><b>' || r.body_pct || '%</b><span style="color:#8b978f;">lobby ' || NVL(TO_CHAR(a.lobby_body_pct), '-') || '% · ' || r.body_hits || ' Hits</span></div>');
    HTP.P('    <div style="display:flex; justify-content:space-between;"><span>Legs</span><b>' || r.leg_pct || '%</b><span style="color:#8b978f;">lobby ' || NVL(TO_CHAR(a.lobby_leg_pct), '-') || '% · ' || r.leg_hits || ' Hits</span></div>');
    HTP.P('    <small style="color:#8b978f;">Vert : mieux que le lobby · Jaune : comparable · Rouge : moins bien</small>');
    HTP.P('  </div>');
    HTP.P('</div></div>');
END;


BEGIN
    HTP.P('<div style="background:#0f1923; color:#ece8e1; padding:18px; border-radius:12px; font-family:sans-serif;">');
    HTP.P('<h3 style="margin-top:0;">TOP 3 ARMES (par kills)</h3>');
    FOR w IN (
        SELECT * FROM v_apex_top_weapons
        WHERE LOWER(riot_id) = LOWER(NVL(:P1_RIOT_ID, 'MonCompte#EUW'))
          AND rang_arme <= 3
        ORDER BY rang_arme
    ) LOOP
        HTP.P('<div style="background:#1a242d; padding:12px 16px; border-radius:8px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">');
        HTP.P('  <div style="width:160px;">');
        HTP.P('    <img src="' || w.image_url || '" style="height:32px; object-fit:contain; filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5));"><br>');
        HTP.P('    <b>' || APEX_ESCAPE.HTML(w.nom_arme) || '</b> <small style="color:#8b978f;">(' || APEX_ESCAPE.HTML(w.categorie_arme) || ')</small>');
        HTP.P('  </div>');
        HTP.P('  <div style="flex:1; margin:0 16px;">');
        HTP.P('    <small style="color:#8b978f;">' || NVL(TO_CHAR(w.part_kills_pct), '0') || '% de tes kills</small>');
        HTP.P('    <div style="background:#2b3848; border-radius:4px; height:8px;"><div style="background:#2ecc71; border-radius:4px; height:8px; width:' || NVL(TO_CHAR(w.part_kills_pct, 'FM990.0', 'NLS_NUMERIC_CHARACTERS=''.,'''), '0') || '%;"></div></div>');
        HTP.P('  </div>');
        HTP.P('  <div style="text-align:right;">');
        HTP.P('    <small style="color:#8b978f;">Kills</small><br><b style="font-size:20px;">' || w.kills || '</b>');
        HTP.P('  </div>');
        HTP.P('</div>');
    END LOOP;
    HTP.P('</div>');
END;


DECLARE
    c v_apex_coach_ia%ROWTYPE;
BEGIN
    SELECT * INTO c FROM v_apex_coach_ia WHERE LOWER(riot_id) = LOWER(NVL(:P1_RIOT_ID, 'MonCompte#EUW')) FETCH FIRST 1 ROWS ONLY;

    HTP.P('<div style="background:#0f1923; color:#ece8e1; padding:20px; border-radius:12px; font-family:sans-serif;">');
    HTP.P('  <h2 style="margin-top:0; color:#2ecc71;">PROGRAMME D''ENTRAÎNEMENT PERSONNALISÉ (ORACLE ML)</h2>');
    HTP.P('  <p style="color:#8b978f;">Comparaison automatique de tes statistiques avec le palier supérieur (Bronze / Argent) calculée via <code>DBMS_DATA_MINING</code> :</p>');
    HTP.P('  <div style="background:#1a242d; padding:14px; border-left:4px solid #ff4655; border-radius:6px; margin-bottom:12px;">' || APEX_ESCAPE.HTML(c.reco_precision) || '</div>');
    HTP.P('  <div style="background:#1a242d; padding:14px; border-left:4px solid #f39c12; border-radius:6px; margin-bottom:12px;">' || APEX_ESCAPE.HTML(c.reco_positionnement) || '</div>');
    HTP.P('  <div style="background:#1a242d; padding:14px; border-left:4px solid #2ecc71; border-radius:6px; margin-bottom:20px;">' || APEX_ESCAPE.HTML(c.reco_collectif) || '</div>');

    HTP.P('  <h3>DIAGNOSTIC PAR ARME (Top 3, croisement Dataset Kaggle)</h3>');
    FOR w IN (
        SELECT * FROM v_apex_top_weapons
        WHERE LOWER(riot_id) = LOWER(NVL(:P1_RIOT_ID, 'MonCompte#EUW'))
          AND rang_arme <= 3
        ORDER BY rang_arme
    ) LOOP
        HTP.P('  <div style="background:#162029; padding:12px; border-radius:8px; margin-bottom:8px;">');
        HTP.P('    <b style="color:#ff4655;">' || APEX_ESCAPE.HTML(w.nom_arme) || ' (' || w.kills || ' kills) :</b> ');
        HTP.P('    <span>' || APEX_ESCAPE.HTML(w.conseil_arme_ia) || '</span>');
        HTP.P('  </div>');
    END LOOP;
    HTP.P('</div>');
END;