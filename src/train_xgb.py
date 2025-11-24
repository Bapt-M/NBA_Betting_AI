import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
from sklearn.metrics import mean_absolute_error
from backend.config import settings

def train_xgboost_model():
    data_path = settings.DATA_PROCESSED
    model_path = settings.MODEL_PATH
    print("--- Entraînement Modèle XGBoost (Expert Betting) ---")
    
    data_path = "data/processed/nba_data_train.csv"
    if not os.path.exists(data_path):
        print("Erreur: Dataset introuvable. Lancez data_processor.py d'abord.")
        return

    # 1. Chargement et Tri
    df = pd.read_csv(data_path).sort_values('GAME_DATE')
    print(f"Données chargées : {len(df)} matchs.")
    
    # 2. Nettoyage strict des Features
    # On ne garde que les chiffres
    df_numeric = df.select_dtypes(include=[np.number])
    
    # On supprime les colonnes qui sont la REPONSE (Data Leakage) ou des IDs inutiles
    cols_to_drop = [
        'GAME_ID_Home', 'GAME_ID_Away', 'TEAM_ID_Home', 'TEAM_ID_Away',
        'TARGET_Total_Pts', # C'est ce qu'on veut prédire
        'Rest_Days_Home', 'Rest_Days_Away' # Déjà capturé dans Meta_Rest_Diff souvent, ou garder si pertinent
    ]
    
    # Suppression des colonnes qui existent dans le df
    X = df_numeric.drop(columns=[c for c in cols_to_drop if c in df_numeric.columns], errors='ignore')
    y = df['TARGET_Total_Pts']
    
    # Sauvegarde des noms de colonnes pour l'inférence (TRES IMPORTANT)
    feature_names = X.columns.tolist()
    os.makedirs("models", exist_ok=True)
    joblib.dump(feature_names, "models/feature_names.pkl")
    print(f"Features utilisées : {len(feature_names)}")
    
    # 3. Split Temporel (On s'entraîne sur le passé, on teste sur le futur)
    # On garde les 15% les plus récents pour tester
    split_idx = int(len(df) * 0.85)
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Train set: {len(X_train)} | Test set: {len(X_test)}")
    
    # 4. Configuration XGBoost
    # Paramètres pour éviter l'overfitting et viser la précision moyenne
    model = xgb.XGBRegressor(
        objective='reg:absoluteerror', # Minimise l'erreur absolue (points)
        n_estimators=2000,             # Beaucoup d'arbres
        learning_rate=0.005,           # Apprentissage lent
        max_depth=6,                   # Profondeur moyenne
        subsample=0.7,                 # Echantillonnage lignes
        colsample_bytree=0.7,          # Echantillonnage colonnes
        early_stopping_rounds=100,     # Arrêt si pas d'amélioration
        n_jobs=-1,
        # Détection GPU automatique (si dispo)
        device='cuda' if os.system("nvidia-smi") == 0 else 'cpu',
        tree_method='hist' # Optimisation vitesse
    )
    
    # 5. Entraînement
    print("Démarrage de l'entraînement...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=200
    )
    
    # 6. Evaluation
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"\nRÉSULTAT FINAL (MAE) : {mae:.2f} points d'erreur moyenne.")
    
    # 7. Sauvegarde Modèle
    model.save_model(model_path)
    print("Modèle sauvegardé dans 'models/xgb_nba_model.json'")
    
    # Sauvegarde d'un extrait de test pour vérification manuelle
    test_sample = X_test.copy()
    test_sample['Actual_Total'] = y_test
    test_sample.to_csv("data/processed/test_set_for_eval.csv", index=False)

if __name__ == "__main__":
    train_xgboost_model()