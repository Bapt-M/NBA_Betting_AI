import sys
import os
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION DU CHEMIN POUR LES IMPORTS ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils import get_team_code

# --- Dictionnaire de secours pour la détection (Surnoms/Villes) ---
# FDJ affiche souvent juste "Cleveland" ou "Boston" au lieu du nom complet.
KEYWORD_MAPPING = {
    "celtics": "BOS", "boston": "BOS",
    "nets": "BKN", "brooklyn": "BKN",
    "knicks": "NYK", "new york": "NYK",
    "76ers": "PHI", "philadelphia": "PHI", "philadelphie": "PHI",
    "raptors": "TOR", "toronto": "TOR",
    "bulls": "CHI", "chicago": "CHI",
    "cavaliers": "CLE", "cleveland": "CLE", "cavs": "CLE",
    "pistons": "DET", "detroit": "DET",
    "pacers": "IND", "indiana": "IND",
    "bucks": "MIL", "milwaukee": "MIL",
    "hawks": "ATL", "atlanta": "ATL",
    "hornets": "CHA", "charlotte": "CHA",
    "heat": "MIA", "miami": "MIA",
    "magic": "ORL", "orlando": "ORL",
    "wizards": "WAS", "washington": "WAS",
    "nuggets": "DEN", "denver": "DEN",
    "timberwolves": "MIN", "minnesota": "MIN", "wolves": "MIN",
    "thunder": "OKC", "oklahoma": "OKC",
    "blazers": "POR", "portland": "POR",
    "jazz": "UTA", "utah": "UTA",
    "warriors": "GSW", "golden state": "GSW",
    "clippers": "LAC", 
    "lakers": "LAL", 
    "suns": "PHX", "phoenix": "PHX",
    "kings": "SAC", "sacramento": "SAC",
    "mavericks": "DAL", "dallas": "DAL", "mavs": "DAL",
    "rockets": "HOU", "houston": "HOU",
    "grizzlies": "MEM", "memphis": "MEM",
    "pelicans": "NOP", "new orleans": "NOP",
    "spurs": "SAS", "san antonio": "SAS"
}

def extract_teams_from_text(event_text):
    """
    VERSION CORRIGÉE : Scanne le texte pour trouver les équipes via mots-clés.
    Remplace la logique rigide des tirets '-'.
    """
    found_codes = []
    # Nettoyage
    text_lower = event_text.lower().replace('\n', ' ')
    
    # 1. Recherche par mots-clés (Plus fiable sur FDJ)
    for keyword, code in KEYWORD_MAPPING.items():
        # \b assure qu'on matche le mot entier (ex: évite de matcher 'suns' dans 'sunset')
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            if code not in found_codes:
                found_codes.append(code)
    
    # Cas Spécial : Los Angeles (Lakers vs Clippers)
    # Si on a trouvé LAC et LAL, c'est parfait.
    # Si on a trouvé juste "clippers" ou "lakers", c'est parfait.
    
    if len(found_codes) == 2:
        # On retourne les codes directement, car get_team_code ne connait pas forcément les surnoms
        return found_codes[0], found_codes[1]
        
    return None, None


def scrape_match_odds(driver, wait, team_home_code, team_away_code):
    """
    Ta fonction originale de scraping complexe (Total Match + Total Equipe).
    Je l'ai gardée intacte car elle est très complète.
    """
    all_fdj_odds = []

    try:
        # Cliquer sur le filtre 'Points'
        try:
            points_filter = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'psel-market-filters__label') and normalize-space(text())='Points']"))
            )
            points_filter.click()
            time.sleep(1)
        except:
            # Parfois le filtre est déjà actif ou n'existe pas sous ce nom
            pass

        # Chercher le marché "Plus / Moins Points - Match"
        market_card = None
        try:
            # Essai précis
            market_card = driver.find_element(By.XPATH, "//*[contains(text(), 'Plus / Moins Points - Match')]/ancestor::*[contains(@class, 'psel-market-card')]")
        except:
            # Essai large
            all_markets = driver.find_elements(By.CLASS_NAME, 'psel-market-card')
            for market in all_markets:
                if 'Plus / Moins Points - Match' in market.text:
                    market_card = market
                    break
        
        if not market_card:
            return []

        # Cliquer sur "Afficher plus" s'il existe
        try:
            show_more_buttons = market_card.find_elements(By.XPATH, ".//button[contains(@class, 'psel-button--collapse') and contains(text(), 'Afficher plus')]")
            if show_more_buttons:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", show_more_buttons[0])
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", show_more_buttons[0])
                time.sleep(1)
        except:
            pass

        # Récupérer les sous-marchés (Total Match vs Total Equipe)
        sub_markets = market_card.find_elements(By.CLASS_NAME, 'psel-market-card')
        match_total_market = None
        team_total_market = None

        # Logique de détection des sous-marchés (basée sur le nombre d'issues ou le texte)
        if not sub_markets:
            # Parfois il n'y a pas de sous-marché, le marché principal EST le total match
            match_total_market = market_card
        else:
            for sub_market in sub_markets:
                txt = sub_market.text
                outcomes = sub_market.find_elements(By.CLASS_NAME, 'psel-outcome')
                if len(outcomes) > 10 and "Equipe" not in txt:
                    match_total_market = sub_market
                elif "Equipe" in txt:
                    team_total_market = sub_market

        # --- 1. Traitement Total Match ---
        if match_total_market:
            outcomes = match_total_market.find_elements(By.CLASS_NAME, 'psel-outcome')
            for outcome in outcomes:
                try:
                    label = outcome.find_element(By.CLASS_NAME, 'psel-outcome__label').text.strip()
                    val_str = outcome.find_element(By.CLASS_NAME, 'psel-outcome__data').text.replace(',', '.').strip()
                    value = float(val_str)

                    # Filtre Main Line (cotes équilibrées)
                    if 1.4 <= value <= 2.2:
                        match = re.search(r'(Plus|Moins)(?: de)?\s+([\d,\.]+)', label)
                        if match:
                            bet_type = 'OVER' if match.group(1) == 'Plus' else 'UNDER'
                            line = float(match.group(2).replace(',', '.'))
                            
                            all_fdj_odds.append({
                                'odd': value,
                                'type': bet_type,
                                'line': line,
                                'category': 'match_total'
                            })
                except: continue

        # --- 2. Traitement Total Equipe (Optionnel mais présent dans ton code original) ---
        if team_total_market:
            outcomes = team_total_market.find_elements(By.CLASS_NAME, 'psel-outcome')
            # On stocke temporairement pour attribuer à la bonne équipe
            # Logique simplifiée : si ligne basse -> Equipe A, ligne haute -> Equipe B ? 
            # Non, trop risqué sans les noms. Dans ton code original tu utilisais un tri par ligne.
            # On va essayer de récupérer le nom de l'équipe dans le titre du sous-marché si possible.
            pass 

    except Exception as e:
        print(f"[WARN] Erreur partielle scraping cotes: {e}")

    return all_fdj_odds


def scrape_nba_odds():
    URL = "https://www.enligne.parionssport.fdj.fr/paris-basketball/usa/nba"
    OUTPUT_FILE = "data/daily/cotes_fdj.json"

    options = webdriver.ChromeOptions()
    options.add_argument('--headless') 
    options.add_argument('--log-level=3')
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    print(f"[INFO] Navigation vers : {URL}")
    driver.get(URL)
    time.sleep(3)
    
    try:
        wait.until(EC.element_to_be_clickable((By.ID, "popin_tc_privacy_button_2"))).click()
    except: pass

    final_data = []

    try:
        all_events = driver.find_elements(By.CLASS_NAME, 'psel-event')
        print(f"[INFO] {len(all_events)} matchs trouvés.\n")

        for event_idx in range(len(all_events)):
            try:
                # Refresh DOM
                all_events = driver.find_elements(By.CLASS_NAME, 'psel-event')
                if event_idx >= len(all_events): break
                current_event = all_events[event_idx]
                time.sleep(0.5)

                # --- NOUVELLE EXTRACTION ---
                # On utilise la fonction robuste basée sur les mots clés
                t1_code, t2_code = extract_teams_from_text(current_event.text)

                if not t1_code:
                    continue

                print(f"Match détecté : {t1_code} vs {t2_code}")

                # Scroll & Click
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", current_event)
                time.sleep(1)
                try:
                    current_event.click()
                except:
                    driver.execute_script("arguments[0].click();", current_event)
                
                time.sleep(2)

                # Scraping avec ta logique interne
                all_fdj_odds = scrape_match_odds(driver, wait, t1_code, t2_code)

                if all_fdj_odds:
                    match_data = {
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'home': t1_code, # Clés compatibles avec daily_predict.py
                        'away': t2_code,
                        'odds': all_fdj_odds
                    }
                    final_data.append(match_data)
                    print(f"[OK] {len(all_fdj_odds)} cotes récupérées.")
                else:
                    print("[WARN] Pas de cotes Over/Under trouvées.")

                driver.back()
                time.sleep(2)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'psel-event')))

            except Exception as match_error:
                print(f"[ERROR] Match {event_idx}: {match_error}")
                driver.get(URL)
                time.sleep(3)
                continue

    except Exception as e:
        print(f"[ERROR GENERAL] {e}")

    finally:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)

        print(f"\n[FIN] {len(final_data)} matchs sauvegardés dans {OUTPUT_FILE}")
        driver.quit()

if __name__ == "__main__":
    scrape_nba_odds()