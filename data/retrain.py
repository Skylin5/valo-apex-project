"""Ré-entraînement du modèle Random Forest Oracle ML (MOD_PRED_RANG_VALO).

Usage :
    python data/retrain.py
"""

from db_utils import get_db_connection

RETRAIN_PLSQL = """
BEGIN
    BEGIN
        DBMS_DATA_MINING.DROP_MODEL('MOD_PRED_RANG_VALO');
    EXCEPTION WHEN OTHERS THEN NULL;
    END;

    DELETE FROM valo_ml_settings;
    INSERT INTO valo_ml_settings (setting_name, setting_value)
        VALUES (dbms_data_mining.algo_name, dbms_data_mining.algo_random_forest);
    INSERT INTO valo_ml_settings (setting_name, setting_value)
        VALUES (dbms_data_mining.prep_auto, dbms_data_mining.prep_auto_on);
    INSERT INTO valo_ml_settings (setting_name, setting_value)
        VALUES ('RFOR_NUM_TREES', '50');
    COMMIT;

    DBMS_DATA_MINING.CREATE_MODEL(
        model_name          => 'MOD_PRED_RANG_VALO',
        mining_function     => DBMS_DATA_MINING.CLASSIFICATION,
        data_table_name     => 'V_ML_TRAINING_DATA',
        case_id_column_name => NULL,
        target_column_name  => 'RANG_CIBLE_ML',
        settings_table_name => 'VALO_ML_SETTINGS'
    );
END;
"""


def main():
    conn = get_db_connection()
    cur = conn.cursor()

    print("Entraînement du Random Forest en cours dans Oracle...")
    cur.execute(RETRAIN_PLSQL)
    print("[OK] Modèle MOD_PRED_RANG_VALO ré-entraîné avec succès sur l'ensemble des matchs !")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
