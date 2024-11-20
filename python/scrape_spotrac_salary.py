import os
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
import logging
import utils

# Set up logging for tracking errors and data processing steps
logging.basicConfig(
    level=logging.INFO,  # Log INFO and higher levels
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# List of NBA teams to scrape salary data for (from Spotrac)
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

# Define the directory and filename for the CSV output
output_dir = "python/data"  # Directory to save the file (adjust as needed)
output_filename = "salary_data.csv"  # Name of the CSV file

# Construct full path to the CSV file using os.path.join (cross-platform compatibility)
output_csv = os.path.join(output_dir, output_filename)

# List to hold all player data collected during scraping
all_data = []

# Set up a persistent session for making requests
def get_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session

# Safe request function with error handling for HTTP requests
def safe_request(session, url):
    try:
        response = session.get(url)
        response.raise_for_status()  # Will raise HTTPError for bad responses (4xx, 5xx)
        return response
    except requests.exceptions.HTTPError as e:
        logging.warning(f"HTTP error for {url}: {e}")
    except Exception as e:
        logging.warning(f"Error fetching {url}: {e}")
    return None

# Extract dynamic season headers (e.g., 2024-25, 2023-24) from the team's salary table
def extract_season_headers(session, team):
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    response = safe_request(session, url)
    if response:
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table")  # Locate the first table on the page
        if table:
            header_row = table.find("tr")  # Find the header row
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
                season_headers = [header for header in headers if re.match(r"^\d{4}-\d{2}$", header)]  # Match season format
                if season_headers:
                    logging.info(f"Season headers extracted for team: {team}")
                    return season_headers
    logging.warning(f"Failed to extract headers for team: {team}")
    return []

# Extract player data (name, position, salary, etc.) from the team's salary table
def extract_player_data(session, team, season_headers):
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    team_name = utils.clean_team_name(url)  # Clean team name
    response = safe_request(session, url)
    if not response:
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("table")
    if not table:
        logging.warning(f"No table found for team {team_name}")
        return []
    
    rows = table.find_all("tr")
    team_data = []
    
    for row in rows[1:]:  # Skip header row
        cols = row.find_all("td")
        if len(cols) < 4:  # Skip rows with insufficient data
            continue
        
        player_name_tag = cols[0].find("a")
        if not player_name_tag:
            continue
        
        player_name = player_name_tag.get_text(strip=True)
        player_link = player_name_tag["href"]
        player_key = utils.make_player_key(player_name)
        position = cols[1].get_text(strip=True)
        age = cols[2].get_text(strip=True)

        salary_data = []
        for col in cols[3:]:
            cell_text = col.get_text(strip=True)
            if "Two-Way" in cell_text:
                salary_data.append("Two-Way")
            elif "UFA" in cell_text:
                salary_data.append("UFA")
            elif "RFA" in cell_text:
                salary_data.append("RFA")
            else:
                salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)
                salary_data.extend(salary_matches)
        
        # Combine player data into a single row and match column count with season headers
        player_data = [player_name, player_link, player_key, team_name, url, position, age] + salary_data
        player_data += [""] * (len(season_headers) - len(salary_data))  # Match header length
        
        team_data.append(player_data)
    return team_data

# Main function to scrape data for all teams and save it to CSV
def scrape_and_save_data():
    session = get_session()
    
    # Extract season headers from any team (they should be the same across teams)
    season_headers = []
    for team in teams:
        season_headers = extract_season_headers(session, team)
        if season_headers:
            break  # Stop once we have valid headers
    
    if not season_headers:
        raise ValueError("Failed to extract season headers.")
    
    headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + season_headers
    pd.DataFrame(columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8", quoting=1)

    # Scrape player data for all teams
    all_data = []
    for idx, team in enumerate(teams):
        logging.info(f"Processing team {team} ({idx+1}/{len(teams)})")
        team_data = extract_player_data(session, team, season_headers)
        all_data.extend(team_data)
    
    # Sort player data by player key (case-insensitive) and save to CSV
    sorted_data = sorted(all_data, key=lambda x: x[2].lower())
    pd.DataFrame(sorted_data, columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8", quoting=1)
    logging.info("Data processing completed and saved to CSV.")

if __name__ == "__main__":
    scrape_and_save_data()
