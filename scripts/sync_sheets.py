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
from utils.csv_handler import CSVHandler
from utils.google_sheets_manager import GoogleSheetsManager
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

import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from lxml import html
from time import sleep
import random

# Retrieve necessary configuration values from the config module
google_sheets_url = config.google_sheets_url
#sheet_name = "Contract Types"  # Name of the sheet where data will be written

# Define what data to read and write
#input_csv = config.spotrac_contracts_path
#output_csv = config.contract_types_path

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

"""
Get Spotrac.com contracts for all 30 NBA teams from https://www.spotrac.com/nba/{team}/yearly
"""
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

# Main function to scrape data for all teams and save to CSV
def get_spotrac_contracts(update_csv=True, update_sheets=False, sheet_name="Contracts"):
    """
    Scrapes salary data for all teams, processes the data, and saves it to a CSV file.
    The CSV includes player names, links, positions, ages, and the first 5 years of salary data.
    """
    output_csv = config.spotrac_contracts_path

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

    session = get_session()
    # Try extracting the season headers (representing the salary years)
    season_headers = []
    for team in teams:
        season_headers = extract_season_headers(session, team)
        if season_headers:
            break
    
    if not season_headers:
        raise ValueError("Failed to extract season headers.")
    
    if update_csv == True:
    
        # Headers include the player details and first 5 salary years
        headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + season_headers[:5]  # Limit to first 5 seasons
        pd.DataFrame(columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8")
        logging.info(f"CSV header written to {output_csv}")

        # Collect all player data across teams
        all_data = []
        for idx, team in enumerate(teams):
            progress = (idx + 1) / len(teams) * 100
            logging.info(f"Processing team {idx+1}/{len(teams)} ({progress:.2f}%) - {team}")
            team_data = extract_player_data(session, team, season_headers)
            all_data.extend(team_data)

        # Log after all teams are processed
        logging.info("All teams processed. Sorting player data...")

        # Sort player data by player name (Player Key)
        sorted_data = sorted(all_data, key=lambda x: x[2].lower())
        # Write the sorted data to CSV
        pd.DataFrame(sorted_data, columns=headers).to_csv(output_csv, index=False, mode="w", encoding="utf-8")
        logging.info(f"Data processing completed. Data successfully written to the file: {output_csv}")

    if update_sheets == True:
        return

def fetch_data(url, headers, retries=3, delay=2):
    """
    Fetch data from the given URL with retry logic.

    Args:
        url (str): The URL to fetch data from.
        headers (dict): HTTP headers to include in the request.
        retries (int): Number of retry attempts if the request fails.
        delay (int): Delay between retry attempts in seconds.

    Returns:
        str: The content of the response if successful.
    """
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed attempt {i + 1}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
        sleep(delay + random.uniform(0, 1))  # Add a slight random delay to avoid rate limiting
    raise Exception("Max retries reached. Unable to fetch data.")

def parse_html(html_content):
    """
    Parse the HTML content and extract player stats into a pandas DataFrame.

    Args:
        html_content (str): The raw HTML content to parse.

    Returns:
        pd.DataFrame: A DataFrame containing the player stats data.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        raise ValueError("Table not found. Ensure the page structure has not changed.")
    
    headers = [th.get_text() for th in table.find("thead").find_all("th")][1:]
    
    # Add extra columns for the player and team links
    headers.extend(["Player Link", "Team Link"])
    
    rows = table.find("tbody").find_all("tr")
    
    # Initialize an empty list to store the data
    data = []

    for row in rows:
        if row.find("td"):  # Skip rows that do not contain data
            row_data = [td.get_text() for td in row.find_all("td")]  # Get text from each 'td' element
            
            # Find all anchor ('a') tags in the row
            links = row.find_all("a")
            
            player_link = None
            team_link = None
            
            # Loop through all the links and check if they correspond to a player or a team
            for link in links:
                href = link.get("href")
                
                # Check if the link is a player link (contains '/players/')
                if "/players/" in href:
                    player_link = "https://www.basketball-reference.com" + href
                    
                # Check if the link is a team link (contains '/teams/')
                elif "/teams/" in href:
                    team_link = "https://www.basketball-reference.com" + href
            
            # Add the player and team links to the row data
            row_data.append(player_link)
            row_data.append(team_link)
            
            # Append the row's data to the list
            data.append(row_data)
    
    # After processing all rows, create the DataFrame with the adjusted headers
    return pd.DataFrame(data, columns=headers)

"""
Get Basketball-Reference NBA totals (defaults to current year, but can be run for previous seasons)
"""
def get_bbref_stats(year=2025, update_csv=True, update_sheets=False, sheet_name="Stats"):
    """
    Main function to fetch, process, and store NBA player stats for the given year.
    It fetches data from Basketball-Reference, processes it, calculates fantasy points,
    and stores the result both in a CSV file and Google Sheets (only for the default year).
    """
    # Construct the URL for the requested year's player stats page on Basketball-Reference
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"
    # Set the request headers for fetching data
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    logger.info(f"Fetching data from URL: {url}")

    # Columns to be used for numerical calculations
    numeric_columns = "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP".split(",")

    # Fetch the HTML data from the Basketball-Reference website
    try:
        response = fetch_data(url, headers)
        logger.info(f"Data fetched successfully from {url}.")
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return

    # Parse the HTML content to extract player stats into a DataFrame
    try:
        df = parse_html(response)
        logger.info("HTML parsed successfully into a DataFrame.")
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return

    # Exclude 'League Average' rows to focus on individual player stats
    df = df[df["Player"] != "League Average"]
    logger.info(f"Excluded 'League Average' rows. Data size is now {len(df)} rows.")

    # Check for and drop any rows with missing player names
    missing_players = df[df["Player"].isna()]
    if not missing_players.empty:
        logger.warning(f"Dropped {len(missing_players)} rows with missing player data.")
    df = df.dropna(subset=["Player"])

    # Add a 'Player Key' column by applying the make_player_key function to the 'Player' column
    df["Player Key"] = df["Player"].apply(make_player_key)
    logger.info("Added 'Player Key' column to DataFrame.")

    # Sort the DataFrame by 'Player Key' and 'Team' columns for organized output
    df = df.sort_values(by=["Player Key", "Team"])
    logger.info("Sorted DataFrame by 'Player Key' and 'Team'.")

    # Drop duplicates based on 'Player Key', keeping the first occurrence
    df = df.drop_duplicates(subset='Player Key', keep='first')
    logger.info("Removed individual teams when more than one.")

    # Convert specified numeric columns to proper numeric types for calculations
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    logger.info(f"Converted numeric columns: {numeric_columns} to numeric types.")

    # Replace any NaN values with 0 across the DataFrame to prevent errors in calculations
    df.fillna(0, inplace=True)
    logger.info("Filled NaN values with 0.")

    # Perform vectorized calculations to compute fantasy points and related stats
    try:
        # Calculate Fantasy Points (FP) as a sum of positive stats and negative ones
        df["FP"] = (
            df["PTS"] + df["TRB"] + df["AST"] + 
            df["STL"] + df["BLK"] - df["TOV"] - df["PF"]
        ).astype(int)  # Fantasy Points: PTS/REB/AST/STL/BLK +1, TO/PF/TF -1
        df["FPPG"] = (df["FP"] / df["G"]).round(1)  # Fantasy Points Per Game
        df["FPPM"] = (df["FP"] / df["MP"]).round(2)  # Fantasy Points Per Minute
        df["MPG"] = (df["MP"] / df["G"]).round(1)  # Minutes Per Game
        df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)  # Fantasy Point Rating = FPPG * FPPM = (FP ** 2) / (G * MP)

        logger.info("Calculated new fantasy stats (FP, FPPG, FPPM, MPG, FPR).")
    except Exception as e:
        logger.error(f"Error during calculations: {e}")
        return
    
    if update_csv == True:

        # Define the file path where the processed data will be saved
        if year == 2025:  # Only sync to Google Sheets for the default year
            output_csv = config.bbref_stats_path
            logger.info(f"Saving data to CSV file: {output_csv}")
            # Save the processed data to a CSV file
            try:
                CSVHandler.write_csv(output_csv, df.values.tolist(), headers=df.columns.tolist())
                logger.info(f"Data successfully written to the CSV file: {output_csv}")
            except Exception as e:
                logger.error(f"Error saving data to CSV: {e}")
                return
            
        else:
            # Generate a dynamic alternate file path using the year
            alternate_output_path = f"data/bbref_stats_{year}.csv"  # Path for alternate CSV output
            logger.info(f"Saving data to alternate CSV file: {alternate_output_path}")
            try:
                CSVHandler.write_csv(alternate_output_path, df.values.tolist(), headers=df.columns.tolist())
                logger.info(f"Data successfully written to alternate CSV file: {alternate_output_path}")
            except Exception as e:
                logger.error(f"Error saving data to alternate CSV: {e}")
    
    if update_sheets == True:

        # Authenticate and update the Google Sheets with the processed data
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name="Stats")
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {config.service_account_email}"]], sheet_name="Stats", start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data to the 'Stats' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name="Stats", start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

"""
Get Sports.ws default NBA player positions
"""
def get_sportsws_positions(update_csv=True, update_sheets=False, sheet_name="Positions"):
    # Log the start message with timestamp and timezone
    logger.info("The script started successfully.")

    # Define the URL
    url = "https://sports.ws/nba/stats"

    output_csv = config.sportsws_positions_path
    
    # Send a GET request to the URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        logging.info(f"Fetching data from {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return
    
    if update_csv == True:
    
        # Parse the HTML using lxml
        logging.info("Parsing HTML content.")
        tree = html.fromstring(response.content)
        
        # Use XPath to extract player names and links
        players = tree.xpath("//td[1]//a")
        logging.info(f"Found {len(players)} players in the data.")
        
        # Extract data into a list of dictionaries
        player_data = []
        for player in players:
            name = player.text.strip() if player.text else ""
            link = "https://sports.ws" + player.get('href')
            key = re.sub("https://sports.ws/nba/", "", link)
            key = make_player_key(key)
            tail = player.tail.strip() if player.tail else ""
            
            player_data.append({"Name": name, "Player Link": link, "Player Key": key, "Tail": tail})
        
        logging.info(f"Extracted data for {len(player_data)} players.")
        
        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(player_data)
        
        # Split the 'Tail' column into 'Team' and 'Pos' columns
        logging.info("Splitting 'Tail' column into 'Team' and 'Position'.")
        df[['Team', 'Position']] = df['Tail'].str.extract(r',\s*([\w*]+),\s*(\w+)')
        
        # Drop the 'Tail' column if no longer needed
        df = df.drop(columns=['Tail'])
        
        # Filter rows where Name is blank
        logging.info("Filtering rows with blank or NaN 'Name'.")
        df = df[df["Name"].str.strip().ne(".")]  # Exclude blank/whitespace-only names
        df = df.dropna(subset=["Name"])  # Also drop rows where Name is NaN
        df = df.fillna("")
        
        # Display the filtered DataFrame
        logging.info("Final filtered data is ready.")

        # Sort the DataFrame by 'Player Key'
        logging.info("Sorting data by 'Player Key'.")
        df = df.sort_values(by="Player Key")
        
        df.to_csv(output_csv, index=False)
        logging.info(f"Data saved to {output_csv}.")

    if update_sheets == True:
        # Define API scope for Google Sheets to enable read/write operations
        scope = ["https://www.googleapis.com/auth/spreadsheets"]

        # Authenticate and update the Google Sheets with the processed data
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name)
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {config.service_account_email}"]], sheet_name, start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data to the 'Stats' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

"""
Update Spotrac contract type
"""
# Function to scrape player data from the player's individual page
def scrape_player_data(player_link, player_key, player_name):
    try:
        # Send a GET request to the player's page and parse the HTML content
        page = requests.get(player_link)
        soup = BeautifulSoup(page.content, "html.parser")

        # CSS selector to find the "Signed Using" contract information
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)

        # Extract contract info
        signed_using_value = (
            signed_using_element.find_next_sibling().get_text().strip()
            if signed_using_element else None
        )

        # Format and clean the extracted contract data
        cleaned_value = format_text(signed_using_value)

        return {
            "Player": player_name,
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": cleaned_value,
        }

    except Exception as e:
        # Log errors and return None for contract data if scraping fails
        logger.error(f"Error scraping data for player {player_name} ({player_key}): {e}")
        return {
            "Player": player_name,
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": None,
        }

def get_contract_types(update_csv=True, update_sheets=False, sheet_name="Contract Types"):
    input_csv = config.spotrac_contracts_path
    output_csv = config.contract_types_path

    logger.info(f"Starting script to scrape player data from {input_csv}")

    try:
        # Load salary data from CSV
        salary_data = pd.read_csv(input_csv)
        logger.info(f"Successfully loaded salary data from {input_csv}")
    except Exception as e:
        logger.error(f"Failed to load salary data: {e}")
        exit()

    # Filter out inactive players or those with "Two-Way" contracts
    active_data = salary_data[(salary_data["2024-25"] != "Two-Way") & (salary_data["2024-25"] != "-")]

    # Extract unique player links and sort by player key
    unique_links = active_data.drop_duplicates(subset=["Player Link", "Player Key"]).sort_values(by="Player Key")["Player Link"].tolist()
    logger.info(f"Found {len(unique_links)} unique player links to scrape")

    if update_csv == True:  ## Where should this line go?

        # Initialize the output CSV with headers
        pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using"]).to_csv(output_csv, index=False, mode="w", encoding="utf-8")
        logger.info(f"Initialized new output CSV file: {output_csv}")

        # Loop through each unique player link and scrape the data
        for idx, link in enumerate(unique_links):
            player_key = active_data[active_data["Player Link"] == link]["Player Key"].values[0]
            player_name = active_data[active_data["Player Link"] == link]["Player"].values[0]

            # Scrape player's contract data
            scraped_row = scrape_player_data(link, player_key, player_name)

            # Append the scraped data to the output CSV file
            pd.DataFrame([scraped_row]).to_csv(output_csv, mode="a", header=False, index=False, encoding="utf-8")

            # Log progress
            logger.info(f"Processed {idx + 1}/{len(unique_links)} players ({((idx + 1) / len(unique_links)) * 100:.2f}%) - {player_name}")

        logger.info(f"Data saved to file: {output_csv}")

    if update_sheets == True:
        # Define API scope for Google Sheets to enable read/write operations
        scope = ["https://www.googleapis.com/auth/spreadsheets"]

        df = CSVHandler.read_csv(input_csv)
        df = pd.DataFrame(df)

        # Authenticate and update the Google Sheets with the processed data
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name)
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {config.service_account_email}"]], sheet_name, start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data to the 'Stats' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    get_spotrac_contracts(update_csv=True, update_sheets=False)
    get_bbref_stats(update_csv=True, update_sheets=False, sheet_name="Stats")
    get_sportsws_positions(update_csv=True, update_sheets=False, sheet_name="Positions")
    get_contract_types(update_csv=False, update_sheets=False, sheet_name="Contract Types")