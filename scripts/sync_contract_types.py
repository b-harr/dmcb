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
from utils.text_formatter import format_text

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
import pandas as pd
from bs4 import BeautifulSoup

# Retrieve necessary configuration values from the config module
google_sheets_url = config.google_sheets_url
sheet_name = "Contract Types"  # Name of the sheet where data will be written

# Define what data to read and write
input_csv = config.spotrac_contracts_path
output_csv = config.contract_types_path

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

def scrape_data():
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

def update_google_sheets():
    # Read the scraped data
    df = pd.read_csv(output_csv)

    # Handle NaN values before writing to Google Sheets
    df = df.fillna('')  # Replace NaN values with empty strings (or use any other placeholder like 'N/A' or 0)

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

        # Write the processed data to the 'Contract Types' sheet
        sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name, start_cell="A2")
        logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
    except Exception as e:
        logger.error(f"Error updating Google Sheets: {e}")

def main(update_data=True,update_sheet=True):
    # Call scrape_data() to pull the data
    if update_data:
        scrape_data()

    # Update Google Sheets only if specified
    if update_sheet:
        update_google_sheets()

if __name__ == "__main__":
    # Call main() and pass True if you want to update Google Sheets, False otherwise
    #main(update_data=False,update_sheet=True)  # Change to False if you don't want to update Google Sheets
    main()
