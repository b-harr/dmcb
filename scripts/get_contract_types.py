import os
import sys
import logging
import pandas as pd

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Path to the directory containing input and output CSV files
input_dir = "data"
input_file = "spotrac_contracts.csv"

# Path for the output file where contract types will be saved
output_dir = "data"
output_file = "contract_types.csv"

# Ensure the output folder exists. If not, it will be created.
os.makedirs(output_dir, exist_ok=True)

# Define the full file paths for input and output CSV files
input_csv = os.path.join(input_dir, input_file)
output_csv = os.path.join(output_dir, output_file)

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,  # Log messages with level INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

# Import necessary utility functions for Google Sheets handling, scraping, and formatting
from utils.google_sheets_manager import GoogleSheetsManager
from utils.scrape_spotrac import scrape_player_contracts
from utils.text_formatter import make_title_case

def main(update_csv=False, update_sheets=True, sheet_name="Contract Types"):
    """
    Main function to scrape player contract data, update CSV, and update Google Sheets.

    Parameters:
    - update_csv (bool): Whether to scrape data and update the CSV file.
    - update_sheets (bool): Whether to update the Google Sheets with the scraped data.
    - sheet_name (str): The name of the sheet in Google Sheets where data will be written.
    """
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

    # Initialize the output CSV only if update_csv is True
    if update_csv:
        # Initialize the CSV file with headers if it's being updated
        pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using"]).to_csv(output_csv, index=False, mode="w", encoding="utf-8")
        logger.info(f"Initialized new output CSV file: {output_csv}")

        # Loop through each unique player link and scrape the data
        for idx, link in enumerate(unique_links):
            # Extract player key and name from the active data
            player_key = active_data[active_data["Player Link"] == link]["Player Key"].values[0]
            player_name = active_data[active_data["Player Link"] == link]["Player"].values[0]

            # Scrape the player's contract data using the link
            signed_using = scrape_player_contracts(link)
            signed_using = make_title_case(signed_using)

            # Construct the row to save into the output CSV
            scraped_row = {
                "Player": player_name,
                "Player Link": link,
                "Player Key": player_key,
                "Signed Using": signed_using
            }

            # Append the scraped data to the output CSV file
            pd.DataFrame([scraped_row]).to_csv(output_csv, mode="a", header=False, index=False, encoding="utf-8")

            # Log progress for every player processed
            logger.info(f"Processed {idx + 1}/{len(unique_links)} players ({((idx + 1) / len(unique_links)) * 100:.2f}%) - {player_name}")

    # If updating Google Sheets is enabled
    if update_sheets:
        try:
            # Load the processed data from the output CSV
            df = pd.read_csv(output_csv)

            # Handle NaN values before writing to Google Sheets (replace with empty strings)
            df = df.fillna('')

            # Generate a timestamp for logging and data tracking
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name=sheet_name)
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {sheets_manager.service_account_email} from {os.path.basename(__file__)}"]], sheet_name=sheet_name, start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data (CSV content) to the Google Sheets 'Contract Types' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")

        except Exception as e:
            # Log any errors encountered during the Sheets update process
            logger.error(f"Error updating Google Sheets: {e}")

# Run the script with both CSV and Sheets updates enabled
if __name__ == "__main__":
    main(update_csv=True, update_sheets=True)  # Pull data and update Google Sheets
    #main(update_csv=True, update_sheets=False)  # Pull data for comparison
    #main(update_csv=False, update_sheets=True)  # Update Google Sheets from CSV
