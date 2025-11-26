import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import os
import sys
import json
from datetime import datetime
from sklearn.metrics import mean_absolute_error, accuracy_score

# Ajout path pour import backend config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.config import settings

def train_xgboost_model():
    print("--- Entraînement Modèle Hybride (Régression + Classification) ---")
    
    data_path = settings.DATA_PROCESSED
    
    if not os.path.exists(data_path):
        print("Erreur: Dataset introuvable. Lancez data_processor.py d'abord.")
        return

    # 1. Chargement
    df = pd.read_csv(data_path).sort_values('GAME_DATE')
    print(f"Données chargées : {len(df)} matchs.")
    
    # 2. Préparation
    df_numeric = df.select_dtypes(include=[np.number])
    cols_to_drop = [
        'GAME_ID_Home', 'GAME_ID_Away', 'TEAM_ID_Home', 'TEAM_ID_Away',
        'TARGET_Total_Pts', 
        'Rest_Days_Home', 'Rest_Days_Away'
    ]
    
    X = df_numeric.drop(columns=[c for c in cols_to_drop if c in df_numeric.columns], errors='ignore')
    y_reg = df['TARGET_Total_Pts']
    
    # Cible Classification : Est-ce que le match dépasse 220 points ? (Médiane NBA approx)
    # L'idéal serait d'avoir la ligne historique du bookmaker, mais 220 est un bon pivot statistique.
    y_class = (df['TARGET_Total_Pts'] > 220.5).astype(int)
    
    # Sauvegarde Feature Names
    feature_names = X.columns.tolist()
    os.makedirs(os.path.dirname(settings.FEATURE_NAMES), exist_ok=True)
    joblib.dump(feature_names, settings.FEATURE_NAMES)
    
    # 3. Split Temporel
    split_idx = int(len(df) * 0.85)
    
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_reg_train, y_reg_test = y_reg.iloc[:split_idx], y_reg.iloc[split_idx:]
    y_class_train, y_class_test = y_class.iloc[:split_idx], y_class.iloc[split_idx:]
    
    print(f"Train set: {len(X_train)} | Test set: {len(X_test)}")
    
    # --- A. MODELE REGRESSION (Score Exact) ---
    print("\n[1/2] Entraînement Régresseur...")
    regressor = xgb.XGBRegressor(
        objective='reg:absoluteerror',
        n_estimators=2500, # Augmenté
        learning_rate=0.005,
        max_depth=6,
        subsample=0.7,
        colsample_bytree=0.7,
        early_stopping_rounds=100,
        n_jobs=-1,
        tree_method='hist'
    )
    
    regressor.fit(
        X_train, y_reg_train,
        eval_set=[(X_test, y_reg_test)],
        verbose=False 
    )
    
    preds_reg = regressor.predict(X_test)
    mae = mean_absolute_error(y_reg_test, preds_reg)
    print(f"MAE Régression : {mae:.2f} points")
    
    regressor.save_model(settings.MODEL_PATH)
    print("Modèle Régression sauvegardé.")

    # --- B. MODELE CLASSIFICATION (Probabilité Over/Under) ---
    print("\n[2/2] Entraînement Classifieur...")
    classifier = xgb.XGBClassifier(
        objective='binary:logistic',
        n_estimators=1000,
        learning_rate=0.01,
        max_depth=5,
        subsample=0.8,
        eval_metric='logloss',
        early_stopping_rounds=50,
        n_jobs=-1
    )
    
    classifier.fit(
        X_train, y_class_train,
        eval_set=[(X_test, y_class_test)],
        verbose=False
    )
    
    preds_class = classifier.predict(X_test)
    acc = accuracy_score(y_class_test, preds_class)
    print(f"Précision Classification (>220.5) : {acc*100:.1f}%")
    
    # Sauvegarde Classifier (nom différent)
    clf_path = settings.MODEL_PATH.replace(".json", "_classifier.json")
    classifier.save_model(clf_path)
    print("Modèle Classification sauvegardé.")

    # --- Métriques & Sauvegarde ---
    metrics = {
        "mae": float(mae),
        "accuracy": float(acc),
        "last_trained": datetime.now().isoformat()
    }
    metrics_path = os.path.join(os.path.dirname(settings.MODEL_PATH), "model_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f)

    print(f"\n✅ Terminé. MAE={mae:.2f} | Acc={acc*100:.1f}%")

if __name__ == "__main__":
    train_xgboost_model()