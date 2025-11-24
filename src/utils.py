"""
Mapping des noms complets des équipes NBA vers leurs codes à 3 lettres.
"""

TEAM_MAPPING = {
    # Eastern Conference - Atlantic
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "New York Knicks": "NYK",
    "Philadelphia 76ers": "PHI",
    "Toronto Raptors": "TOR",

    # Eastern Conference - Central
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Detroit Pistons": "DET",
    "Indiana Pacers": "IND",
    "Milwaukee Bucks": "MIL",

    # Eastern Conference - Southeast
    "Atlanta Hawks": "ATL",
    "Charlotte Hornets": "CHA",
    "Miami Heat": "MIA",
    "Orlando Magic": "ORL",
    "Washington Wizards": "WAS",

    # Western Conference - Northwest
    "Denver Nuggets": "DEN",
    "Minnesota Timberwolves": "MIN",
    "Oklahoma City Thunder": "OKC",
    "Portland Trail Blazers": "POR",
    "Utah Jazz": "UTA",

    # Western Conference - Pacific
    "Golden State Warriors": "GSW",
    "Los Angeles Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Phoenix Suns": "PHX",
    "Sacramento Kings": "SAC",

    # Western Conference - Southwest
    "Dallas Mavericks": "DAL",
    "Houston Rockets": "HOU",
    "Memphis Grizzlies": "MEM",
    "New Orleans Pelicans": "NOP",
    "San Antonio Spurs": "SAS",
}

def get_team_code(team_name):
    """
    Retourne le code à 3 lettres d'une équipe NBA à partir de son nom complet.

    Args:
        team_name (str): Le nom complet de l'équipe (ex: "Boston Celtics" ou "BOS Celtics")

    Returns:
        str: Le code à 3 lettres de l'équipe (ex: "BOS") ou None si non trouvé
    """
    # Essai 1: Recherche directe
    if team_name in TEAM_MAPPING:
        return TEAM_MAPPING[team_name]

    # Essai 2: Le nom peut contenir le code au début (ex: "CHA Hornets" -> "Charlotte Hornets")
    # Extraire le code potentiel (3 premières lettres avant l'espace)
    parts = team_name.split()
    if len(parts) >= 2 and len(parts[0]) == 3:
        potential_code = parts[0].upper()
        # Chercher dans le mapping par code
        for full_name, code in TEAM_MAPPING.items():
            if code == potential_code:
                return code

    # Essai 3: Recherche partielle par le nom de l'équipe
    # Par exemple "LA Clippers" -> chercher "Clippers"
    for full_name, code in TEAM_MAPPING.items():
        if team_name in full_name or full_name.split()[-1] in team_name:
            return code

    return None
