import os
import sys
import logging
from dotenv import load_dotenv
import pandas as pd
import requests
import re
from bs4 import BeautifulSoup

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to make sure modules can be imported
sys.path.append(base_dir)

# Import custom modules for the script
import config
from utils.google_sheets_manager import GoogleSheetsManager
from utils.csv_handler import CSVHandler
from utils.data_fetcher import fetch_data, parse_html
from utils.text_formatter import make_player_key, format_text

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,  # Log messages with level INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

# Load environment variables from the .env file
load_dotenv()
logger.info("Environment variables loaded successfully.")

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

# List to store all player data scraped from the teams
all_data = []

# Set up a persistent session for making HTTP requests
def get_session():
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    )  # Set user-agent for the request
    return session

# Safe request function to handle HTTP errors and return the response
def safe_request(session, url):
    try:
        response = session.get(url)  # Make the GET request
        response.raise_for_status()  # Check for HTTP errors (4xx, 5xx)
        return response
    except requests.exceptions.HTTPError as e:
        logging.warning(f"HTTP error for {url}: {e}")  # Log warning for HTTP errors
    except Exception as e:
        logging.warning(f"Error fetching {url}: {e}")  # Log other errors (e.g., connection issues)
    return None  # Return None if the request fails

# Extract season headers (e.g., "2024-25", "2023-24") from the team's salary table
def extract_season_headers(session, team):
    url = f"https://www.spotrac.com/nba/{team}/yearly"  # Team-specific salary data URL
    response = safe_request(session, url)  # Make a safe HTTP request
    if response:
        soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML with BeautifulSoup
        table = soup.select_one("table")  # Find the first table on the page
        if table:
            header_row = table.find("tr")  # Locate the header row
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all("th")]  # Get header texts
                season_headers = [header for header in headers if re.match(r"^\d{4}-\d{2}$", header)]  # Match season format
                if season_headers:
                    logging.info(f"Season headers extracted for team: {team}")  # Log success
                    return season_headers
    logging.warning(f"Failed to extract headers for team: {team}")  # Log failure
    return []

# Extract player data (name, position, salary, etc.) from the salary table of the team
def extract_player_data(session, team, season_headers):
    url = f"https://www.spotrac.com/nba/{team}/yearly"  # Team-specific salary data URL
    team_name = format_text(team)  # Clean the team name
    response = safe_request(session, url)  # Get the team data with safe_request
    if not response:
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML response
    table = soup.select_one("table")  # Find the first table on the page
    if not table:
        logging.warning(f"No table found for team {team}")  # Log if no table found
        return []
    
    rows = table.find_all("tr")  # Find all rows in the table
    team_data = []
    
    # Loop through each row (skipping the header row)
    for row in rows[1:]:
        cols = row.find_all("td")  # Extract all columns
        if len(cols) < 4:  # Skip rows with insufficient data
            continue
        
        player_name_tag = cols[0].find("a")  # Find player name link
        if not player_name_tag:
            continue
        
        player_name = player_name_tag.get_text(strip=True)  # Get player name text
        player_link = player_name_tag["href"]  # Get player link
        player_key = make_player_key(player_name)  # Generate a unique key for the player
        position = cols[1].get_text(strip=True)  # Get player position
        age = cols[2].get_text(strip=True)  # Get player age

        salary_data = []
        # Extract salary information
        for col in cols[3:]:
            cell_text = col.get_text(strip=True)
            if "Two-Way" in cell_text:
                salary_data.append("Two-Way")
            elif "UFA" in cell_text:
                salary_data.append("UFA")
            elif "RFA" in cell_text:
                salary_data.append("RFA")
            else:
                salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)  # Match salary format
                salary_data.extend(salary_matches)
        
        # Combine player data into a single row and match the header length
        player_data = [player_name, player_link, player_key, team_name, url, position, age] + salary_data
        player_data += [""] * (len(season_headers) - len(salary_data))  # Ensure columns match season headers
        
        team_data.append(player_data)
    return team_data

# Main function to scrape data for all teams and save to CSV
def scrape_and_save_data():
    session = get_session()  # Initialize the session
    
    # Extract season headers from one team (they will be the same across all teams)
    season_headers = []
    for team in teams:
        season_headers = extract_season_headers(session, team)
        if season_headers:
            break  # Stop once valid headers are found
    
    if not season_headers:
        raise ValueError("Failed to extract season headers.")  # Raise error if headers could not be extracted
    
    headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + season_headers
    pd.DataFrame(columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8", quoting=1)  # Write CSV header

    # Scrape player data for all teams
    all_data = []
    for idx, team in enumerate(teams):
        team_name = format_text(team)
        progress = (idx + 1) / len(teams) * 100  # Calculate progress
        logging.info(f"Processed {idx+1}/{len(teams)} teams ({progress:.2f}%) - {team}")  # Log progress with percentage
        team_data = extract_player_data(session, team, season_headers)  # Extract player data
        all_data.extend(team_data)

    # Sort player data by player key (case-insensitive) and save to CSV
    sorted_data = sorted(all_data, key=lambda x: x[2].lower())
    pd.DataFrame(sorted_data, columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8", quoting=1)  # Write sorted data to CSV
    logging.info(f"Data processing completed. Data successfully written to the file: {output_csv}")  # Log completion

if __name__ == "__main__":
    scrape_and_save_data()  # Run the main function to scrape and save the data
