import pandas as pd
import numpy as np
import os
import sys
import json
from datetime import datetime, timedelta

# Import des modules du dossier src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_all_game_data
from src.data_processor import process_data
from src.train_xgb import train_xgboost_model

# Chemins
PREDICTIONS_CSV = "data/daily/all_odds_predictions.csv"
PERFORMANCE_LOG = "data/daily/model_history_log.csv"
TRAIN_DATA = "data/processed/nba_data_train.csv"

def evaluate_past_predictions():
    """
    Compare les prédictions stockées dans le CSV avec les résultats réels
    récupérés après la mise à jour des données.
    """
    print("\n--- 2. ÉVALUATION DES PERFORMANCES ---")
    
    if not os.path.exists(PREDICTIONS_CSV):
        print("[ERREUR] Pas de fichier de prédictions trouvé à évaluer.")
        return

    if not os.path.exists(TRAIN_DATA):
        print("[ERREUR] Pas de données d'entraînement à jour.")
        return

    # 1. Charger les prédictions et l'historique réel à jour
    df_preds = pd.read_csv(PREDICTIONS_CSV)
    df_actual = pd.read_csv(TRAIN_DATA)
    
    # On s'assure d'avoir les mappings d'équipe pour faire la correspondance
    # On reconstruit le map Code -> ID depuis le fichier d'entrainement
    if 'TEAM_ABBREVIATION_Home' in df_actual.columns:
        map_df = df_actual[['TEAM_ABBREVIATION_Home', 'TEAM_ID_Home']].drop_duplicates()
        code_to_id = dict(zip(map_df.TEAM_ABBREVIATION_Home, map_df.TEAM_ID_Home))
    else:
        print("[ERREUR] Colonne Abbreviation manquante dans les données.")
        return

    # Préparation du journal de performance
    results_list = []
    
    # Pour chaque prédiction faite
    for index, row in df_preds.iterrows():
        # Si le match a déjà été évalué (on pourrait ajouter une colonne 'Evaluated' dans le CSV futur), on passe
        # Ici on recalcule tout pour simplifier
        
        home_code = row['Home']
        away_code = row['Away']
        pred_date = row['Date'] # Format YYYY-MM-DD
        
        # Trouver l'ID des équipes
        home_id = code_to_id.get(home_code)
        away_id = code_to_id.get(away_code)
        
        if not home_id or not away_id:
            continue
            
        # Chercher ce match dans les données réelles (TRAIN_DATA)
        # On cherche un match à cette date (ou date +1 jour décalage fuseau horaire) avec ces équipes
        match_real = df_actual[
            (df_actual['TEAM_ID_Home'] == home_id) & 
            (df_actual['TEAM_ID_Away'] == away_id) &
            (df_actual['GAME_DATE'].astype(str).str.contains(pred_date))
        ]
        
        if match_real.empty:
            # Le match n'a peut-être pas encore été joué ou récupéré
            continue
            
        # Le match a été joué !
        real_score = match_real.iloc[0]['TARGET_Total_Pts']
        
        # Vérification du Pari
        bet_type = row['Type_Pari'] # OVER ou UNDER
        line = row['Ligne_Bookmaker']
        cote = row['Cote']
        
        won = False
        if bet_type == "OVER" and real_score > line: won = True
        elif bet_type == "UNDER" and real_score < line: won = True
        
        # Calcul Profit (Mise fictive de 1 unité)
        profit = (cote - 1) if won else -1
        
        results_list.append({
            "Date": pred_date,
            "Match": row['Match'],
            "Prediction": row['Prediction_Modele'],
            "Reel": real_score,
            "Erreur_Abs": abs(row['Prediction_Modele'] - real_score),
            "Pari": f"{bet_type} {line}",
            "Resultat": "GAGNÉ" if won else "PERDU",
            "Profit": profit
        })

    if not results_list:
        print("[ERREUR] Aucun nouveau résultat de match trouvé pour les prédictions existantes.")
        return

    # Sauvegarde / Mise à jour du Log
    df_results = pd.DataFrame(results_list)
    
    # Affichage du bilan de la session
    print(f"Matchs évalués : {len(df_results)}")
    print(f"Taux de réussite : {(df_results['Resultat'] == 'GAGNÉ').mean() * 100:.1f}%")
    print(f"Profit Net (Mise 1u) : {df_results['Profit'].sum():.2f}u")
    print(f"Erreur Moyenne Modèle (MAE) : {df_results['Erreur_Abs'].mean():.2f} pts")
    
    # Append au fichier historique global
    header = not os.path.exists(PERFORMANCE_LOG)
    df_results.to_csv(PERFORMANCE_LOG, mode='a', header=header, index=False)
    print(f"Historique mis à jour : {PERFORMANCE_LOG}")
    
    # Optionnel : Nettoyer le fichier all_odds_predictions pour ne pas réévaluer demain ?
    # Pour l'instant on garde tout, c'est plus sûr.

def run_update_pipeline():
    print("==================================================")
    print("   MISE À JOUR QUOTIDIENNE DU MODÈLE NBA")
    print("==================================================")
    
    # ÉTAPE 1 : Récupérer les nouveaux matchs (Nuit dernière)
    print("\n--- 1. TÉLÉCHARGEMENT DES DONNÉES ---")
    try:
        # On appelle le fetcher existant (qui gère l'historique et la mise à jour)
        fetch_all_game_data() # Met à jour raw/nba_games_raw.csv
        process_data()        # Recalcule processed/nba_data_train.csv
    except Exception as e:
        print(f"[ERREUR] Erreur lors de la mise à jour des données : {e}")
        return

    # ÉTAPE 2 : Vérifier si on a gagné hier
    try:
        evaluate_past_predictions()
    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'évaluation (pas bloquant) : {e}")

    # ÉTAPE 3 : Ré-entraîner le cerveau (Fine-tuning)
    print("\n--- 3. RÉ-ENTRAÎNEMENT DU MODÈLE ---")
    print("Le modèle va apprendre des matchs de la nuit dernière...")
    try:
        train_xgboost_model()
    except Exception as e:
        print(f"[ERREUR] Erreur lors de l'entraînement : {e}")
        return

    print("\nMISE À JOUR TERMINÉE AVEC SUCCÈS.")
    print("Vous pouvez maintenant lancer : python daily/scraper_fdj.py")

if __name__ == "__main__":
    run_update_pipeline()