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
from utils.google_sheets_manager import GoogleSheetsManager
from utils.text_formatter import make_player_key

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

# Retrieve necessary configuration values from the config module
google_sheets_url = config.google_sheets_url
sheet_name = "Positions"  # Name of the sheet where data will be written

import pandas as pd
import requests
import re
from lxml import html

# Define the directory and filename for saving the CSV file
output_csv = config.sportsws_positions_path

def main():
    # Log the start message with timestamp and timezone
    logger.info("The script started successfully.")

    # Define the URL
    url = "https://sports.ws/nba/stats"
    
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

if __name__ == "__main__":
    main()
