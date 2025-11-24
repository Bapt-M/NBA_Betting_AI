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

# --- CONFIGURATION CHEMINS ---
BASE_DIR = "/app" if os.path.exists("/app") else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

try:
    from src.utils import get_team_code
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.utils import get_team_code

# --- MAPPING MOTS-CLÉS ---
KEYWORD_MAPPING = {
    "celtics": "BOS", "boston": "BOS", "nets": "BKN", "brooklyn": "BKN",
    "knicks": "NYK", "new york": "NYK", "76ers": "PHI", "philadelphia": "PHI",
    "raptors": "TOR", "toronto": "TOR", "bulls": "CHI", "chicago": "CHI",
    "cavaliers": "CLE", "cleveland": "CLE", "cavs": "CLE", "pistons": "DET", "detroit": "DET",
    "pacers": "IND", "indiana": "IND", "bucks": "MIL", "milwaukee": "MIL",
    "hawks": "ATL", "atlanta": "ATL", "hornets": "CHA", "charlotte": "CHA",
    "heat": "MIA", "miami": "MIA", "magic": "ORL", "orlando": "ORL",
    "wizards": "WAS", "washington": "WAS", "nuggets": "DEN", "denver": "DEN",
    "timberwolves": "MIN", "minnesota": "MIN", "wolves": "MIN", "thunder": "OKC", "oklahoma": "OKC",
    "blazers": "POR", "portland": "POR", "jazz": "UTA", "utah": "UTA",
    "warriors": "GSW", "golden state": "GSW", "clippers": "LAC", "lakers": "LAL",
    "suns": "PHX", "phoenix": "PHX", "kings": "SAC", "sacramento": "SAC",
    "mavericks": "DAL", "dallas": "DAL", "mavs": "DAL", "rockets": "HOU", "houston": "HOU",
    "grizzlies": "MEM", "memphis": "MEM", "pelicans": "NOP", "new orleans": "NOP",
    "spurs": "SAS", "san antonio": "SAS"
}

def extract_teams_robust(event_text):
    found_codes = []
    text_lower = event_text.lower().replace('\n', ' ')
    for keyword, code in KEYWORD_MAPPING.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            if code not in found_codes: found_codes.append(code)
    if len(found_codes) == 2: return found_codes[0], found_codes[1]
    return None, None

def scrape_match_odds(driver, wait):
    """
    LOGIQUE D'ORIGINE RESTAURÉE STRICTEMENT
    """
    all_fdj_odds = []

    try:
        # Cliquer sur le filtre 'Points'
        try:
            points_filter = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'psel-market-filters__label') and normalize-space(text())='Points']"))
            )
            points_filter.click()
            time.sleep(2)
        except:
            pass

        # Chercher le marché "Plus / Moins Points - Match"
        market_card = None
        try:
            # Essai précis avec texte exact
            market_card = wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Plus / Moins Points - Match')]/ancestor::*[contains(@class, 'psel-market-card') or contains(@class, 'market')]"))
            )
        except:
            # Fallback recherche manuelle
            all_markets = driver.find_elements(By.CLASS_NAME, 'psel-market-card')
            for market in all_markets:
                if 'Plus / Moins Points - Match' in market.text:
                    market_card = market
                    break
        
        if not market_card:
            return []

        # Cliquer sur "Afficher plus" s'il existe
        try:
            show_more_buttons = market_card.find_elements(By.XPATH, ".//button[contains(@class, 'psel-button--collapse') and normalize-space(text())='Afficher plus']")
            if show_more_buttons:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", show_more_buttons[0])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", show_more_buttons[0])
                time.sleep(1)
        except:
            pass

        # Récupérer les sous-marchés
        sub_markets = market_card.find_elements(By.CLASS_NAME, 'psel-market-card')
        match_total_market = None
        
        # Logique de tri des sous-marchés (Match vs Equipes)
        if not sub_markets:
            # Si pas de sous-marché, le conteneur principal est le marché
            match_total_market = market_card
        else:
            for sub_market in sub_markets:
                try:
                    outcomes_count = len(sub_market.find_elements(By.CLASS_NAME, 'psel-outcome'))
                    text = sub_market.text
                    # Si beaucoup d'issues (>30) et pas de mention "Equipe", c'est le total match
                    if outcomes_count > 20 and "Equipe" not in text:
                        match_total_market = sub_market
                        break # On prend le premier gros bloc pertinent
                except: pass

        # Traiter le marché du total du match
        if match_total_market:
            match_odds_elements = match_total_market.find_elements(By.CLASS_NAME, 'psel-outcome')
            for outcome in match_odds_elements:
                try:
                    label = outcome.find_element(By.CLASS_NAME, 'psel-outcome__label').text.strip()
                    value_str = outcome.find_element(By.CLASS_NAME, 'psel-outcome__data').text.replace(',', '.').strip()
                    value = float(value_str)

                    # Filtre Cotes
                    if 1.4 <= value <= 2.4:
                        bet_type = None
                        line_str = None

                        if label.startswith('Plus de ') or label.startswith('Plus '):
                            bet_type = 'OVER'
                            line_str = label.replace('Plus de ', '').replace('Plus ', '').replace(',', '.').strip()
                        elif label.startswith('Moins de ') or label.startswith('Moins '):
                            bet_type = 'UNDER'
                            line_str = label.replace('Moins de ', '').replace('Moins ', '').replace(',', '.').strip()
                        
                        if bet_type and line_str:
                            try:
                                line = float(line_str)
                                all_fdj_odds.append({
                                    'odd': value,
                                    'type': bet_type,
                                    'line': line,
                                    'category': 'match_total'
                                })
                            except: pass
                except:
                    continue

    except Exception as e:
        print(f"[WARN] Erreur scraping cotes: {e}")

    return all_fdj_odds

def scrape_nba_odds():
    URL = "https://www.enligne.parionssport.fdj.fr/paris-basketball/usa/nba"
    OUTPUT_FILE = os.path.join(BASE_DIR, "data/daily/cotes_fdj.json")
    
    print(f"--- SCRAPING FDJ (Logic Original Restored) ---")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except:
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    wait = WebDriverWait(driver, 15)
    final_data = []

    try:
        driver.get(URL)
        time.sleep(5)
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "popin_tc_privacy_button_2"))).click()
        except: pass

        events = driver.find_elements(By.CLASS_NAME, 'psel-event')
        print(f"[INFO] {len(events)} matchs détectés.")

        for i in range(len(events)):
            events = driver.find_elements(By.CLASS_NAME, 'psel-event')
            if i >= len(events): break
            event = events[i]
            
            t1, t2 = extract_teams_robust(event.text)
            if not t1: continue
            
            print(f"Processing: {t1} vs {t2}")
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", event)
            time.sleep(1)
            try: event.click()
            except: driver.execute_script("arguments[0].click();", event)
            time.sleep(3)
            
            odds = scrape_match_odds(driver, wait)
            
            if odds:
                final_data.append({
                    "home": t1, "away": t2,
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "odds": odds
                })
                print(f" -> {len(odds)} cotes 'Match Total' récupérées.")
            else:
                print(" -> Pas de cotes 'Match Total'.")
            
            driver.back()
            time.sleep(2)
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'psel-event')))
            except:
                driver.get(URL)
                time.sleep(3)

    except Exception as e:
        print(f"[ERREUR] {e}")
    finally:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        print("Scraping terminé.")
        driver.quit()

if __name__ == "__main__":
    scrape_nba_odds()