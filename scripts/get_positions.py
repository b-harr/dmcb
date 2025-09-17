import os
import sys
import logging
import argparse

# Set up the project root directory for module imports
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# Output file configuration
output_dir = "data"
output_file = "sportsws_positions.csv"
os.makedirs(output_dir, exist_ok=True)
output_csv = os.path.join(output_dir, output_file)

# Configure logging for script execution
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()
logger.info("The script started successfully.")

# Import custom utilities
from utils.scrape_sportsws import scrape_sportsws_positions
from utils.text_formatter import make_player_key
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Positions"):
    """
    Scrape, process, and optionally export Sports.ws player position data.

    Args:
        update_csv (bool): If True, save processed data to CSV.
        update_sheets (bool): If True, update Google Sheets with processed data.
        sheet_name (str): Google Sheets tab name to update.
    """
    # Scrape player position data from Sports.ws
    df = scrape_sportsws_positions()

    # Generate a unique Player Key from the Sports.ws link
    df["Player Key"] = df["Player Link"].str.replace("https://sports.ws/nba/", "").apply(make_player_key)

    # Remove any rows where Player Key contains "placeholder" (case-insensitive)
    df = df[~df["Player Key"].str.contains("placeholder", case=False, na=False)].copy()

    # Sort the DataFrame by Player Key for consistency
    df = df.sort_values(by="Player Key", ignore_index=True)

    # Reorder columns and remove "Team" from output
    column_order = ["Name", "Player Link", "Player Key", "Position"]
    df = df[column_order]

    # Export to CSV if requested
    if update_csv:
        df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")
        logger.info(f"Data saved to {output_csv}")

    # Update Google Sheets if requested
    if update_sheets:
        try:
            # Generate a timestamp for the update
            timestamp = logging.Formatter('%(asctime)s').format(
                logging.LogRecord("", 0, "", 0, "", [], None)
            )

            # Initialize Google Sheets manager and clear the target sheet
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
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape and export Sports.ws player positions.")
    parser.add_argument("--update_csv", action="store_true", default=True, help="Save processed data to CSV. (default: True)")
    parser.add_argument("--update_sheets", action="store_true", default=False, help="Update Google Sheets with processed data. (default: False)")
    parser.add_argument("--sheet_name", type=str, default="Positions", help="Google Sheets tab name to update.")
    args = parser.parse_args()

    main(
        update_csv=args.update_csv,
        update_sheets=args.update_sheets,
        sheet_name=args.sheet_name
    )
