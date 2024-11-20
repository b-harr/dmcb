import os
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
import logging
import utils

# Set up logging for tracking errors and steps in data processing
logging.basicConfig(
    level=logging.INFO,  # Log all INFO level messages and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the start message with timestamp and timezone
logger.info("The script started successfully.")

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
output_dir = "python/data"  # Directory to store the output
output_filename = "salary_data.csv"  # Output CSV filename

# Generate the full path to the CSV file (ensures cross-platform compatibility)
output_csv = os.path.join(output_dir, output_filename)

# List to store all player data scraped from the teams
all_data = []

# Set up a persistent session for making HTTP requests
def get_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})  # Set user-agent for the request
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
    team_name = utils.clean_team_name(url)  # Clean the team name
    response = safe_request(session, url)  # Get the team data with safe_request
    if not response:
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")  # Parse HTML response
    table = soup.select_one("table")  # Find the first table on the page
    if not table:
        logging.warning(f"No table found for team {team_name}")  # Log if no table found
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
        player_key = utils.make_player_key(player_name)  # Generate a unique key for the player
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
        logging.info(f"Processing team {team} ({idx+1}/{len(teams)})")  # Log progress
        team_data = extract_player_data(session, team, season_headers)  # Extract player data
        all_data.extend(team_data)
    
    # Sort player data by player key (case-insensitive) and save to CSV
    sorted_data = sorted(all_data, key=lambda x: x[2].lower())
    pd.DataFrame(sorted_data, columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8", quoting=1)  # Write sorted data to CSV
    logging.info(f"Data processing completed. Data successfully written to the file: {output_csv}")  # Log completion

if __name__ == "__main__":
    scrape_and_save_data()  # Run the main function to scrape and save the data
