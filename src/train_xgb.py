import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import sys
import json  # AJOUT
from datetime import datetime # AJOUT
from sklearn.metrics import mean_absolute_error

# Ajout path pour import backend config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.config import settings

def train_xgboost_model():
    print("--- Entraînement Modèle XGBoost (Expert Betting) ---")
    
    # Utilisation du chemin configuré
    data_path = settings.DATA_PROCESSED
    model_path = settings.MODEL_PATH
    
    if not os.path.exists(data_path):
        print("Erreur: Dataset introuvable. Lancez data_processor.py d'abord.")
        return

    # 1. Chargement
    df = pd.read_csv(data_path).sort_values('GAME_DATE')
    print(f"Données chargées : {len(df)} matchs.")
    
    # 2. Préparation
    meta_cols = ['GAME_DATE', 'TEAM_ABBREVIATION_Home', 'TEAM_ABBREVIATION_Away', 'TARGET_Total_Pts']
    df_meta = df[meta_cols].copy()

    df_numeric = df.select_dtypes(include=[np.number])
    cols_to_drop = [
        'GAME_ID_Home', 'GAME_ID_Away', 'TEAM_ID_Home', 'TEAM_ID_Away',
        'TARGET_Total_Pts', 
        'Rest_Days_Home', 'Rest_Days_Away'
    ]
    X = df_numeric.drop(columns=[c for c in cols_to_drop if c in df_numeric.columns], errors='ignore')
    y = df['TARGET_Total_Pts']
    
    # Sauvegarde des noms de colonnes
    feature_names = X.columns.tolist()
    os.makedirs(os.path.dirname(settings.FEATURE_NAMES), exist_ok=True)
    joblib.dump(feature_names, settings.FEATURE_NAMES)
    
    # 3. Split Temporel (85% train, 15% test)
    split_idx = int(len(df) * 0.85)
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    
    print(f"Train set: {len(X_train)} | Test set: {len(X_test)}")
    
    # 4. Configuration & Entraînement
    model = xgb.XGBRegressor(
        objective='reg:absoluteerror',
        n_estimators=2000,
        learning_rate=0.005,
        max_depth=6,
        subsample=0.7,
        colsample_bytree=0.7,
        early_stopping_rounds=100,
        n_jobs=-1,
        tree_method='hist'
    )
    
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train), (X_test, y_test)],
        verbose=False 
    )
    
    # 5. Prédictions et Évaluation
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    print(f"\nRÉSULTAT FINAL (MAE) : {mae:.2f} points d'erreur moyenne.")
    
    model.save_model(model_path)
    print("Modèle sauvegardé.")

    # --- CORRECTION MAE : Sauvegarde des métriques dans un JSON ---
    metrics = {
        "mae": float(mae),
        "last_trained": datetime.now().isoformat()
    }
    metrics_path = os.path.join(os.path.dirname(model_path), "model_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f)
    print(f"✅ Métriques (MAE={mae:.2f}) sauvegardées dans {metrics_path}")

    # Sauvegarde des prédictions de test (pour l'update DB)
    meta_test = df_meta.iloc[split_idx:].copy()
    meta_test['Predicted_Total'] = preds
    output_test_path = os.path.join(settings.BASE_DIR, "data/processed/latest_test_predictions.csv")
    meta_test.to_csv(output_test_path, index=False)

if __name__ == "__main__":
    train_xgboost_model()