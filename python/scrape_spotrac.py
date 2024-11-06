# Scrape NBA contracts from Spotrac.com

# Import necessary libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import unicodedata

# Define team IDs for constructing Spotrac URLs
teams = [
    "atlanta-hawks", "brooklyn-nets", "boston-celtics", "charlotte-hornets",
    "cleveland-cavaliers", "chicago-bulls", "dallas-mavericks", "denver-nuggets",
    "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers",
    "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat",
    "milwaukee-bucks", "minnesota-timberwolves", "new-york-knicks",
    "new-orleans-pelicans", "oklahoma-city-thunder", "orlando-magic",
    "philadelphia-76ers", "phoenix-suns", "portland-trail-blazers",
    "san-antonio-spurs", "sacramento-kings", "toronto-raptors",
    "utah-jazz", "washington-wizards"
]
# Define the range of seasons to scrape
years = range(2024, 2029)
    
# Helper function to clean names
def clean_name(player_name):
    # Normalize to ASCII, replace hyphens with underscores, remove other punctuation, convert to lowercase, and replace spaces with underscores
    normalized_text = unicodedata.normalize('NFD', player_name).encode('ascii', 'ignore').decode('utf-8')
    normalized_text = normalized_text.replace('-', '_')
    cleaned_name = re.sub(r'[^\w\s]', '', normalized_text).strip().lower().replace(' ', '_')
    return cleaned_name

# Helper function to remove suffixes
def remove_suffix(player_name):
    # Remove common suffixes like _sr, _jr, _ii, _iii, etc.
    return re.sub(r'_(sr|jr|ii|iii|iv|v|vi|vii)$', '', player_name)

def get_team_name(team_link):
    # Remove the base URL and any trailing slashes from the team link
    path = team_link.replace("https://www.spotrac.com/nba/", "").strip("/")
    # Extract the team name segment from the path
    team_name = path.split("/")[0]
    
    # Split team name by hyphens to handle multi-part names, e.g., "san-antonio-spurs"
    team_name_parts = team_name.split("-")
    
    # Capitalize each part, with specific handling for "LA" and numeric parts like "76ers"
    formatted_name = " ".join(
        part.upper() if part.lower() == "la"  # Capitalize "LA" specifically
        else part.capitalize() if part.isalpha()  # Capitalize alphabetic parts only (e.g., "Bulls")
        else part  # Retain numeric parts as they are (e.g., "76ers")
        for part in team_name_parts
    )
    
    return formatted_name

# Define the main function to scrape player contract data from a given Spotrac URL
def scrape_spotrac(team_link):
    response = requests.get(team_link)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Extract player names; if no players found, return an empty DataFrame
    players = [a.get_text() for a in soup.select('#table_active tbody td:nth-of-type(1) a') if a.get_text() != ""]
    if not players:
        return pd.DataFrame()
    
    # Extract player profile links, positions, ages, contract types, and cap hits
    player_links = [a['href'] for a in soup.select('#table_active tbody td:nth-of-type(1) a') if a['href'] != "javascript:void(0)"]
    positions = [td.get_text().strip() for td in soup.select('#table_active tbody td:nth-of-type(2)')]
    ages = [td.get_text().strip() for td in soup.select('#table_active tbody td:nth-of-type(3)')]
    types = [td.get_text().strip() for td in soup.select('#table_active tbody td:nth-of-type(4)')]
    cap_hits = [td.get_text().strip() for td in soup.select('#table_active tbody td:nth-of-type(5)')]
    
    # Construct the season in "YYYY-YY" format
    year = int(team_link.split("/")[-2])
    seasons = f"{year}-{str(year + 1)[-2:]}"

    # Get team name from team link
    team = get_team_name(team_link)
    
    # Combine extracted data into a DataFrame
    data = pd.DataFrame({
        "player": players,
        "player_link": player_links,
        "season": seasons,
        "cap_hit": cap_hits,
        "position": positions,
        "age": ages,
        "type": types,
        "team_link": team_link,
        "team": team
    })
    
    # Generate 'players_clean' and 'players_clean_no_suffix' columns
    data['player_clean'] = data['player'].apply(clean_name)
    data['player_clean_no_suffix'] = data['player_clean'].apply(remove_suffix)
    
    # Filter out unwanted entries (e.g., "Two-Way" contracts or missing cap hits)
    data = data[(data['cap_hit'] != "Two-Way") & (data['cap_hit'] != "-")]
    
    return data

# Construct Spotrac URLs for each team and season
spotrac_links = [f"https://www.spotrac.com/nba/{team}/cap/_/year/{year}/" for team in teams for year in years]

# Scrape data from all constructed URLs
spotrac_data = pd.concat([scrape_spotrac(link) for link in spotrac_links], ignore_index=True)

# Sort data by player and season
spotrac_data.sort_values(by=["player_clean", "season"], inplace=True)

# Save the cleaned and organized data to a CSV file
spotrac_data.to_csv("spotrac_data.csv", index=False, quoting=1)
