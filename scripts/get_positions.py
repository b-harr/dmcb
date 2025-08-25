import os
import sys
import logging

# Dynamically determine the root project directory (two levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the project root directory to sys.path to enable imports of custom modules
sys.path.append(base_dir)

# Define paths for output data
output_dir = "data"
output_file = "sportsws_positions.csv"

# Ensure the output directory exists; create it if necessary
os.makedirs(output_dir, exist_ok=True)

# Define the full file path for the output CSV file
output_csv = os.path.join(output_dir, output_file)

# Configure logging to track script execution and log errors or important events
logging.basicConfig(
    level=logging.INFO,  # Log INFO and above (e.g., WARN, ERROR)
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start for tracking purposes
logger.info("The script started successfully.")

# Import custom utilities for data scraping, formatting, and Google Sheets management
from utils.scrape_sportsws import scrape_sportsws_positions
from utils.text_formatter import make_player_key
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Positions"):
    """
    Main function to process and manage player position data.
    
    Args:
        update_csv (bool): Whether to save processed data to a CSV file.
        update_sheets (bool): Whether to update the Google Sheets document.
        sheet_name (str): The name of the sheet to update in Google Sheets.
    """
    # Step 1: Scrape player position data from Sports.ws
    df = scrape_sportsws_positions()

    # Step 2: Add a unique identifier for each player based on their Sports.ws link
    df["Player Key"] = df["Player Link"].str.replace("https://sports.ws/nba/", "").apply(make_player_key)

    # Step 3: Sort the data for consistent output and readability
    df = df.sort_values(by="Player Key", ignore_index=True)

    # Step 4: Reorder columns for a clear, consistent structure
    column_order = ["Name", "Player Link", "Player Key", "Team", "Position"]
    df = df[column_order]

    # Save the processed data to a CSV file if requested
    if update_csv:
        df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")
        logger.info(f"Data saved to {output_csv}")

    # Update Google Sheets if requested
    if update_sheets:
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(
                logging.LogRecord("", 0, "", 0, "", [], None)  # Generate formatted timestamp
            )

            # Initialize the Google Sheets manager and clear the target sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name=sheet_name)
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to the top of the sheet
            sheets_manager.write_data(
                [[f"Last updated {timestamp} by {sheets_manager.service_account_email} from {os.path.basename(__file__)}"]],
                sheet_name=sheet_name,
                start_cell="A1"
            )
            logger.info("Timestamp added to Google Sheets.")

            # Write the processed data to the sheet starting from cell A2
            sheets_manager.write_data(
                [df.columns.tolist()] + df.values.tolist(),
                sheet_name=sheet_name,
                start_cell="A2"
            )
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            # Log any errors that occur during Google Sheets updates
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    # Execute the main function with default settings
    main(update_csv=True, update_sheets=False)
