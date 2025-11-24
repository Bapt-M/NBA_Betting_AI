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
# Dans Docker, le dossier de travail est /app. On utilise des chemins absolus.
BASE_DIR = "/app" if os.path.exists("/app") else os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

try:
    from src.utils import get_team_code
except ImportError:
    # Fallback local si lancé hors module
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from src.utils import get_team_code

# --- MAPPING MOTS-CLÉS (Robustesse FDJ) ---
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
    all_fdj_odds = []
    try:
        try:
            # Bouton "Points"
            btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Points')]")
            for btn in btns:
                if btn.is_displayed(): 
                    btn.click()
                    break
            time.sleep(0.5)
        except: pass

        outcomes = driver.find_elements(By.CLASS_NAME, 'psel-outcome')
        for outcome in outcomes:
            try:
                txt_label = outcome.find_element(By.CLASS_NAME, 'psel-outcome__label').text.strip()
                txt_val = outcome.find_element(By.CLASS_NAME, 'psel-outcome__data').text.replace(',', '.').strip()
                
                if "Plus" in txt_label or "Moins" in txt_label:
                    match = re.search(r'(?:Plus|Moins)(?: de)?\s+([\d,\.]+)', txt_label)
                    if match:
                        line = float(match.group(1).replace(',', '.'))
                        odd = float(txt_val)
                        otype = "OVER" if "Plus" in txt_label else "UNDER"
                        if 1.40 <= odd <= 2.40: # Filtre élargi
                            all_fdj_odds.append({'type': otype, 'line': line, 'odd': odd})
            except: continue
    except: pass
    return all_fdj_odds

def scrape_nba_odds():
    # URL & Sortie
    URL = "https://www.enligne.parionssport.fdj.fr/paris-basketball/usa/nba"
    OUTPUT_FILE = os.path.join(BASE_DIR, "data/daily/cotes_fdj.json")
    
    print(f"--- SCRAPING FDJ (Docker Mode) ---")
    print(f"Output: {OUTPUT_FILE}")

    # CONFIGURATION CHROME POUR DOCKER
    options = webdriver.ChromeOptions()
    options.add_argument('--headless') # Indispensable en Docker
    options.add_argument('--no-sandbox') # Indispensable en root/Docker
    options.add_argument('--disable-dev-shm-usage') # Gestion mémoire partagée
    options.add_argument('--disable-gpu')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    try:
        # Tentative d'utilisation du driver système (installé dans le Dockerfile)
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        # Fallback local (si testé hors docker)
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    wait = WebDriverWait(driver, 10)
    final_data = []

    try:
        driver.get(URL)
        time.sleep(5)
        
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "popin_tc_privacy_button_2"))).click()
        except: pass

        events = driver.find_elements(By.CLASS_NAME, 'psel-event')
        print(f"[INFO] {len(events)} blocs détectés.")

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
            time.sleep(2)
            
            odds = scrape_match_odds(driver, wait)
            if odds:
                final_data.append({
                    "home": t1, "away": t2,
                    "date": datetime.now().strftime('%Y-%m-%d'),
                    "odds": odds
                })
                print(f" -> {len(odds)} cotes.")
            
            driver.back()
            time.sleep(2)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'psel-event')))

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