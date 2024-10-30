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
years = range(2024, 2028)  # Define the range of seasons to scrape

# Helper function to clean text
def clean_text(text):
    return re.sub(r"\s+", "", text.replace("\n", ""))
    
# Helper function to clean name as per the new requirements
def clean_name(name):
    # Normalize to ASCII, remove punctuation, convert to lowercase, and replace spaces with underscores
    normalized_text = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    cleaned_name = re.sub(r'[^\w\s]', '', normalized_text).strip().lower().replace(' ', '_')
    return cleaned_name

# Helper function to remove suffixes
def remove_suffix(name):
    # Remove common suffixes like _sr, _jr, _ii, _iii, etc.
    return re.sub(r'_(sr|jr|ii|iii|iv|v|vi|vii)$', '', name)

# Define the main function to scrape player contract data from a given Spotrac URL
def scrape_spotrac_link(link):
    response = requests.get(link)
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Extract player names; if no players found, return an empty DataFrame
    players = [a.get_text() for a in soup.select('#table_active tbody td:nth-of-type(1) a') if a.get_text() != ""]
    if not players:
        return pd.DataFrame()
    
    # Extract player profile links, positions, ages, contract types, and cap hits
    player_links = [a['href'] for a in soup.select('#table_active tbody td:nth-of-type(1) a') if a['href'] != "javascript:void(0)"]
    positions = [clean_text(td.get_text()) for td in soup.select('#table_active tbody td:nth-of-type(2)')]
    ages = [clean_text(td.get_text()) for td in soup.select('#table_active tbody td:nth-of-type(3)')]
    types = [clean_text(td.get_text()) for td in soup.select('#table_active tbody td:nth-of-type(4)')]
    cap_hits = [clean_text(td.get_text()) for td in soup.select('#table_active tbody td:nth-of-type(5)')]
    
    # Construct the season in "YYYY-YY" format
    year = int(link.split("/")[-2])
    seasons = f"{year}-{str(year + 1)[-2:]}"
    
    # Combine extracted data into a DataFrame
    data = pd.DataFrame({
        "player": players,
        "player_link": player_links,
        "season": seasons,
        "cap_hit": cap_hits,
        "position": positions,
        "age": ages,
        "type": types,
        "link": link
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
spotrac_data = pd.concat([scrape_spotrac_link(link) for link in spotrac_links], ignore_index=True)

# Sort data by player and season
spotrac_data.sort_values(by=["player_clean", "season"], inplace=True)

# Save the cleaned and organized data to a CSV file
spotrac_data.to_csv("spotrac_data.csv", index=False)
