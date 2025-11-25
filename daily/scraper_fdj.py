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

# --- PATH SETUP ---
BASE_DIR = "/app" if os.path.exists("/app") else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

try:
    from src.utils import get_team_code
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.utils import get_team_code

# --- MAPPING MOTS-CLÉS ---
KEYWORD_MAPPING = {
    # ATLANTIC
    "celtics": "BOS", "boston": "BOS",
    "nets": "BKN", "brooklyn": "BKN",
    "knicks": "NYK", "new york": "NYK", "ny knicks": "NYK",
    "76ers": "PHI", "sixers": "PHI", "philadelphia": "PHI", "philadelphie": "PHI",
    "raptors": "TOR", "toronto": "TOR",

    # CENTRAL
    "bulls": "CHI", "chicago": "CHI",
    "cavaliers": "CLE", "cleveland": "CLE", "cavs": "CLE",
    "pistons": "DET", "detroit": "DET",
    "pacers": "IND", "indiana": "IND",
    "bucks": "MIL", "milwaukee": "MIL",

    # SOUTHEAST
    "hawks": "ATL", "atlanta": "ATL",
    "hornets": "CHA", "charlotte": "CHA",
    "heat": "MIA", "miami": "MIA",
    "magic": "ORL", "orlando": "ORL",
    "wizards": "WAS", "washington": "WAS",

    # NORTHWEST
    "nuggets": "DEN", "denver": "DEN",
    "timberwolves": "MIN", "minnesota": "MIN", "wolves": "MIN",
    "thunder": "OKC", "oklahoma": "OKC", "oklahoma city": "OKC", "okc": "OKC",
    "blazers": "POR", "portland": "POR", "trail blazers": "POR",
    "jazz": "UTA", "utah": "UTA",

    # PACIFIC
    "warriors": "GSW", "golden state": "GSW", "golden state warriors": "GSW",
    "clippers": "LAC", "la clippers": "LAC", "l.a. clippers": "LAC", "los angeles clippers": "LAC",
    "lakers": "LAL", "la lakers": "LAL", "l.a. lakers": "LAL", "los angeles lakers": "LAL",
    "suns": "PHX", "phoenix": "PHX",
    "kings": "SAC", "sacramento": "SAC",

    # SOUTHWEST
    "mavericks": "DAL", "dallas": "DAL", "mavs": "DAL",
    "rockets": "HOU", "houston": "HOU",
    "grizzlies": "MEM", "memphis": "MEM",
    "pelicans": "NOP", "new orleans": "NOP", "nouvelle orleans": "NOP", "nouvelle-orléans": "NOP",
    "spurs": "SAS", "san antonio": "SAS"
}

def extract_teams_robust(event_text):
    """
    Extrait les codes équipes (ex: 'MIL', 'CHI') d'un texte en respectant l'ordre d'apparition.
    Gère les doublons (ex: "Milwaukee Bucks" -> 1 seule équipe MIL).
    """
    found_matches = [] # Liste de tuples (position_start, code_equipe)
    text_lower = event_text.lower().replace('\n', ' ').strip()
    
    # 1. On cherche TOUS les mots-clés présents dans le texte
    for keyword, code in KEYWORD_MAPPING.items():
        # \b assure qu'on cherche le mot entier (évite de trouver 'IND' dans 'Find')
        # re.escape évite les bugs avec des caractères spéciaux
        pattern = r'\b' + re.escape(keyword) + r'\b'
        
        # finditer trouve toutes les occurrences du mot-clé
        for match in re.finditer(pattern, text_lower):
            found_matches.append((match.start(), code))
    
    # 2. On trie les résultats par leur position dans la phrase
    # Cela garantit que l'équipe citée en premier est bien Home
    found_matches.sort(key=lambda x: x[0])
    
    # 3. On dédoublonne en gardant l'ordre
    final_teams = []
    seen_codes = set()
    
    for _, code in found_matches:
        if code not in seen_codes:
            final_teams.append(code)
            seen_codes.add(code)
    
    # 4. On retourne les 2 premières équipes trouvées
    if len(final_teams) >= 2:
        return final_teams[0], final_teams[1]
        
    return None, None

def scrape_match_odds(driver, wait):
    """
    Logique avec traces d'exécution (Logs).
    """
    all_fdj_odds = []
    print("    >  Début analyse page match...")

    try:
        # 1. Filtre Points
        try:
            print("    >  Recherche onglet 'Points'...")
            points_filter = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'psel-market-filters__label') and normalize-space(text())='Points']"))
            )
            points_filter.click()
            print("    >  Clic sur 'Points' effectué.")
            time.sleep(2)
        except: 
            print("    >  (Info) Onglet 'Points' non trouvé ou déjà actif.")

        # 2. Trouver le marché
        print("    >  Recherche bloc 'Plus / Moins Points - Match'...")
        market_card = None
        try:
            market_card = wait.until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Plus / Moins Points - Match')]/ancestor::*[contains(@class, 'psel-market-card') or contains(@class, 'market')]"))
            )
        except:
            all_markets = driver.find_elements(By.CLASS_NAME, 'psel-market-card')
            for market in all_markets:
                if 'Plus / Moins Points - Match' in market.text:
                    market_card = market
                    break
        
        if not market_card: 
            print("    >  [WARN] Marché introuvable.")
            return []

        # 3. Déplier "Afficher plus"
        try:
            show_more = market_card.find_elements(By.XPATH, ".//button[contains(@class, 'psel-button--collapse') and normalize-space(text())='Afficher plus']")
            if show_more:
                print("    >  Bouton 'Afficher plus' détecté, clic...")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", show_more[0])
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", show_more[0])
                time.sleep(1)
        except: pass

        # 4. Analyser les sous-marchés
        sub_markets = market_card.find_elements(By.CLASS_NAME, 'psel-market-card')
        match_total_market = None

        if not sub_markets:
            match_total_market = market_card
        else:
            for sub_market in sub_markets:
                try:
                    outcomes_count = len(sub_market.find_elements(By.CLASS_NAME, 'psel-outcome'))
                    text = sub_market.text
                    if outcomes_count > 10 and "Equipe" not in text:
                        match_total_market = sub_market
                        break
                except: pass

        # 5. Extraction
        if match_total_market:
            outcomes = match_total_market.find_elements(By.CLASS_NAME, 'psel-outcome')
            print(f"    >  Analyse de {len(outcomes)} lignes de cotes...")
            
            for outcome in outcomes:
                try:
                    label = outcome.find_element(By.CLASS_NAME, 'psel-outcome__label').text.strip()
                    val_str = outcome.find_element(By.CLASS_NAME, 'psel-outcome__data').text.replace(',', '.').strip()
                    value = float(val_str)

                    if 1.40 <= value <= 2.50:
                        bet_type = None
                        line_str = None
                        
                        if 'Plus' in label:
                            bet_type = 'OVER'
                            match = re.search(r'(?:Plus|Moins)(?: de)?\s+([\d,\.]+)', label)
                            if match: line_str = match.group(1).replace(',', '.')
                        elif 'Moins' in label:
                            bet_type = 'UNDER'
                            match = re.search(r'(?:Plus|Moins)(?: de)?\s+([\d,\.]+)', label)
                            if match: line_str = match.group(1).replace(',', '.')

                        if bet_type and line_str:
                            try:
                                all_fdj_odds.append({
                                    'odd': value,
                                    'type': bet_type,
                                    'line': float(line_str),
                                    'category': 'match_total'
                                })
                            except: pass
                except: continue

    except Exception as e: 
        print(f"    >  [ERREUR] {e}")
        pass
    
    print(f"    > [BILAN] {len(all_fdj_odds)} cotes extraites pour ce match.")
    return all_fdj_odds

def scrape_nba_odds():
    URL = "https://www.enligne.parionssport.fdj.fr/paris-basketball/usa/nba"
    OUTPUT_FILE = os.path.join(BASE_DIR, "data/daily/cotes_fdj.json")
    
    print(f"--- SCRAPING FDJ ---")
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
        try: wait.until(EC.element_to_be_clickable((By.ID, "popin_tc_privacy_button_2"))).click()
        except: pass

        events = driver.find_elements(By.CLASS_NAME, 'psel-event')
        print(f"[INFO] {len(events)} matchs détectés.")

        for i in range(len(events)):
            events = driver.find_elements(By.CLASS_NAME, 'psel-event')
            if i >= len(events): break
            event = events[i]
            
            t1, t2 = extract_teams_robust(event.text)
            if not t1: continue
            
            print(f"\nTRAITEMENT MATCH {i+1}: {t1} vs {t2}")
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", event)
            time.sleep(1)
            try: event.click()
            except: driver.execute_script("arguments[0].click();", event)
            time.sleep(3)
            
            odds = scrape_match_odds(driver, wait)
            if odds:
                final_data.append({ "home": t1, "away": t2, "date": datetime.now().strftime('%Y-%m-%d'), "odds": odds })
            
            driver.back()
            time.sleep(2)
            try: wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'psel-event')))
            except: 
                driver.get(URL)
                time.sleep(3)

    except Exception as e: print(f"[ERREUR] {e}")
    finally:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        print("Scraping terminé.")
        driver.quit()

if __name__ == "__main__":
    scrape_nba_odds()