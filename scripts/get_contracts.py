import os
import sys
import logging
import argparse
import re

# Set up logging for the script
log_file = os.path.join("logs", "get_contracts.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Define paths for the output directory and file
output_dir = "data"
output_file = "spotrac_contracts.csv"

# Ensure the output folder exists
os.makedirs(output_dir, exist_ok=True)

# Define the full path for the output CSV file
output_csv = os.path.join(output_dir, output_file)

# Import utility functions and modules
from utils.scrape_spotrac import scrape_all_teams
from utils.text_formatter import make_player_key, make_title_case
from utils.google_sheets_manager import GoogleSheetsManager

def main(update_csv=True, update_sheets=False, sheet_name="Contracts", data_range="A1:L541"):
    """
    Main function to scrape Spotrac data, process it, and optionally save it to a CSV file
    and/or update Google Sheets.

    Parameters:
        update_csv (bool): Whether to save the data to a CSV file.
        update_sheets (bool): Whether to update the data in Google Sheets.
        sheet_name (str): The name of the Google Sheets tab to update.
    """
    logging.info("Starting data scrape from Spotrac...")
    
    # Attempt to scrape data
    try:
        df = scrape_all_teams()
        if df is None or df.empty:
            raise ValueError("No data was returned from the scrape.")
    except Exception as e:
        logging.error(f"Data scrape failed: {e}")
        sys.exit(1)
    
    # Process the DataFrame if valid data is returned
    logging.info("Processing scraped data...")
    try:
        # Exclude rows where Player is "Incomplete Roster Charge"
        df = df[df["Player"] != "Incomplete Roster Charge"]

        # Add derived columns for Player Key and Team Link
        df["Player Key"] = df["Player"].apply(make_player_key)
        df["Team Link"] = df["Team"].apply(lambda team: f"https://www.spotrac.com/nba/{team}/yearly")
        
        # Format the Team column to Title Case
        df["Team"] = df["Team"].apply(make_title_case)
        
        # Sort by Player Key then Team for consistency
        df = df.sort_values(by=["Player Key", "Team"], ignore_index=True)
        
        # Dynamically reorder columns
        required_columns = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"]
        dynamic_columns = [col for col in df.columns if col.startswith("20")]
        column_order = required_columns + dynamic_columns
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        df = df[column_order]

        # --- Add Cap Holds for Kuminga and Grimes before CSV output ---
        import pandas as pd
        extra_rows = [
            [
                "Jonathan Kuminga",
                "https://www.spotrac.com/nba/player/_/id/74114/jonathan-kuminga",
                "jonathan-kuminga",
                "Golden State Warriors",
                "https://www.spotrac.com/nba/golden-state-warriors/yearly",
                "PF",
                22,
                "$22908921"
            ],
            [
                "Quentin Grimes",
                "https://www.spotrac.com/nba/player/_/id/74132/quentin-grimes",
                "quentin-grimes",
                "Philadelphia 76ers",
                "https://www.spotrac.com/nba/philadelphia-76ers/yearly",
                "SG",
                25,
                "$12890046"
            ]
        ]
        # Ensure extra_rows has the same number of columns as df
        while len(extra_rows[0]) < len(df.columns):
            for row in extra_rows:
                row.append("")
        extra_df = pd.DataFrame(extra_rows, columns=df.columns)
        df = pd.concat([df, extra_df], ignore_index=True)
        # --- End add rows ---

    except Exception as e:
        logging.error(f"Error during data processing: {e}")
        sys.exit(1)
    
    # Save the processed data to a CSV file
    if update_csv:
        try:
            df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")
            logging.info(f"Data successfully saved to {output_csv}")
        except Exception as e:
            logging.error(f"Failed to save data to CSV: {e}")
    
    # Update the Google Sheets document if requested
    if update_sheets:# Convert any column like '2025-26' to numeric if it has strings with $
        # Identify salary/year columns (those starting with '20', e.g., '2025-26')
        salary_cols = [col for col in df.columns if re.match(r"20\d{2}-\d{2}", col)]

        for col in salary_cols:
            # Remove $ and commas, convert numeric values to float, leave text as-is
            df[col + "_numeric"] = pd.to_numeric(df[col].replace(r'[\$,]', '', regex=True), errors='coerce')
            # Replace numeric values in the original column, leave non-numeric as text
            df[col] = df[col + "_numeric"].combine_first(df[col])
            # Drop temporary numeric helper column
            df.drop(columns=[col + "_numeric"], inplace=True)

        logging.info(f"Updating Google Sheets: {sheet_name}")
        try:
            # Generate a timestamp for logging and data tracking
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))

            # Initialize the Google Sheets manager and clear the target range
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_range(sheet_name=sheet_name, range_to_clear=data_range)

            # Write the processed data frame to the sheet starting from cell A1
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A1")
            logging.info("Google Sheets updated successfully.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"{timestamp}"]], sheet_name=sheet_name, start_cell="AC2")
            logging.info("Wrote timestamp to Google Sheets.")
        except Exception as e:
            logging.error(f"Failed to update Google Sheets: {e}")


# Main execution block
if __name__ == "__main__":
    logging.info(f"Script execution started: {__file__}")
    parser = argparse.ArgumentParser(description="Scrape, process, and export Spotrac NBA contract data.")

    # Mutually exclusive group for CSV
    csv_group = parser.add_mutually_exclusive_group()
    csv_group.add_argument(
        "--update-csv",
        dest="update_csv",
        action="store_true",
        help="Save processed data to CSV (default)."
    )
    csv_group.add_argument(
        "--no-update-csv",
        dest="update_csv",
        action="store_false",
        help="Do not save processed data to CSV."
    )
    parser.set_defaults(update_csv=True)

    # Mutually exclusive group for Google Sheets
    sheets_group = parser.add_mutually_exclusive_group()
    sheets_group.add_argument(
        "--update-sheets",
        dest="update_sheets",
        action="store_true",
        help="Update Google Sheets with processed data."
    )
    sheets_group.add_argument(
        "--no-update-sheets",
        dest="update_sheets",
        action="store_false",
        help="Do not update Google Sheets (default)."
    )
    parser.set_defaults(update_sheets=False)

    # Other arguments
    parser.add_argument(
        "--sheet",
        dest="sheet_name",
        type=str,
        default="Contracts",
        help="Google Sheets tab name to update."
    )
    parser.add_argument(
        "--range",
        dest="data_range",
        type=str,
        default="A1:L541",
        help="Range to clear in Google Sheets before writing."
    )

    args = parser.parse_args()

    main(
        update_csv=args.update_csv,
        update_sheets=args.update_sheets,
        sheet_name=args.sheet_name,
        data_range=args.data_range
    )
    logging.info(f"Script execution completed: {__file__}")
