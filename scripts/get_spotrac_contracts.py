import os
import sys
import logging
from dotenv import load_dotenv

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Import custom modules for the script
import config
from utils.text_formatter import make_player_key, format_text

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

# Load environment variables from the .env file
load_dotenv()
logger.info("Environment variables loaded successfully.")

import pandas as pd
import requests
import re
from bs4 import BeautifulSoup

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

# Define the directory and filename for saving the CSV file
output_csv = config.spotrac_contracts_path

# Set up a persistent session for making HTTP requests
def get_session():
    """
    Creates and returns a persistent session with appropriate headers
    for making requests to Spotrac.
    """
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    )
    return session

# Safe request function to handle HTTP errors and return the response
def safe_request(session, url):
    """
    Attempts to fetch data from the given URL, handling HTTP errors gracefully.
    Returns the response if successful, otherwise logs an error.
    """
    try:
        response = session.get(url)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        logging.warning(f"HTTP error for {url}: {e}")
    except Exception as e:
        logging.warning(f"Error fetching {url}: {e}")
    return None

# Extract season headers (e.g., "2024-25", "2023-24") from the team's salary table
def extract_season_headers(session, team):
    """
    Extracts the season headers (e.g., "2024-25") from the salary table
    for a given team on Spotrac. These headers represent the years for
    the player's salary data.
    """
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    response = safe_request(session, url)
    if response:
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table")
        if table:
            header_row = table.find("tr")
            if header_row:
                # Extract headers that represent years
                headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
                season_headers = [header for header in headers if re.match(r"^\d{4}-\d{2}$", header)]
                if season_headers:
                    logging.info(f"Season headers extracted for team: {team}")
                    return season_headers
    logging.warning(f"Failed to extract headers for team: {team}")
    return []

# Extract player data (name, position, salary, etc.) from the salary table of the team
def extract_player_data(session, team, season_headers):
    """
    Extracts player data (name, position, salary, etc.) from the salary table
    of the given team on Spotrac, limiting to the first 5 salary years.
    """
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    team_name = format_text(team)
    response = safe_request(session, url)
    if not response:
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("table")
    if not table:
        logging.warning(f"No table found for team {team}")
        return []
    
    rows = table.find_all("tr")
    team_data = []
    
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        
        # Extract player name and other details
        player_name_tag = cols[0].find("a")
        if not player_name_tag:
            continue
        
        player_name = player_name_tag.get_text(strip=True)
        player_link = player_name_tag["href"]
        player_key = make_player_key(player_name)
        position = cols[1].get_text(strip=True)
        age = cols[2].get_text(strip=True)

        salary_data = []
        # Extract salary data (e.g., "$10M", "UFA", etc.)
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
                salary_data.extend([s.replace(",", "") for s in salary_matches])
        
        # Only keep the first 5 salaries (and pad with empty strings if fewer)
        player_data = [player_name, player_link, player_key, team_name, url, position, age] + salary_data[:5]
        player_data += [""] * (5 - len(salary_data))  # Fill missing salary slots with empty strings
        team_data.append(player_data)
        
        # Log each player being processed
        logging.info(f"Processed player: {player_name}, Position: {position}, Salary: {', '.join(salary_data[:5])}")
    
    return team_data

# Main function to scrape data for all teams and return the DataFrame
def main():
    """
    Scrapes salary data for all teams, processes the data, and returns a pandas DataFrame.
    The DataFrame includes player names, links, positions, ages, and the first 5 years of salary data.
    """
    session = get_session()
    
    # Try extracting the season headers (representing the salary years)
    season_headers = []
    for team in teams:
        season_headers = extract_season_headers(session, team)
        if season_headers:
            break
    
    if not season_headers:
        raise ValueError("Failed to extract season headers.")
    
    # Headers include the player details and first 5 salary years
    headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + season_headers[:5]  # Limit to first 5 seasons

    # Collect all player data across teams
    all_data = []
    for idx, team in enumerate(teams):
        progress = (idx + 1) / len(teams) * 100
        logging.info(f"Processing team {idx+1}/{len(teams)} ({progress:.2f}%) - {team}")
        team_data = extract_player_data(session, team, season_headers)
        all_data.extend(team_data)

    # Log after all teams are processed
    logging.info("All teams processed. Creating player data frame...")

    # Create a pandas DataFrame
    data_frame = pd.DataFrame(all_data, columns=headers)

    # Sort the DataFrame by the "Player Key" column
    data_frame = data_frame.sort_values(by="Player Key")

    # Log the sorting completion
    logging.info("Player data sorted by Player Key.")

    return data_frame

if __name__ == "__main__":
    # Run the scraping and get the data as a DataFrame
    data_frame = main()
    print(data_frame.head())  # Example usage: display the first few rows
