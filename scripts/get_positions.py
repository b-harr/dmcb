import os
import sys
import logging
import argparse
import pandas as pd

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


def merge_owner_from_google_sheets(df, sheet_name="Contracts"):
    """Merge owner values from the Google Sheets Contracts tab using Player Key."""
    try:
        sheets_manager = GoogleSheetsManager()
        raw_data = sheets_manager.read_data(sheet_name=sheet_name)
    except Exception as e:
        logger.warning(f"Could not read owner data from Google Sheets '{sheet_name}': {e}")
        return df

    if not raw_data:
        return df

    header = raw_data[0]
    rows = raw_data[1:] if len(raw_data) > 1 else []

    if len(header) <= 16:
        logger.warning("Google Sheets 'Contracts' tab does not contain the expected owner column (Q).")
        return df

    owner_df = pd.DataFrame(rows, columns=[str(col).strip() for col in header])
    owner_df = owner_df.iloc[:, [0, 1, 2, 16]].copy()
    owner_df.columns = ["Player", "Player Link", "Player Key", "Owner"]

    owner_df["Player Key"] = owner_df["Player Key"].astype(str).str.strip()
    owner_df = owner_df.dropna(subset=["Player Key"])
    owner_df = owner_df[owner_df["Player Key"] != ""]

    owner_lookup = {}
    for _, row in owner_df.iterrows():
        owner_lookup[row["Player Key"]] = row["Owner"]

    if df.empty:
        return df

    merged_df = df.copy()
    merged_df["Player Key"] = merged_df["Player Key"].astype(str).str.strip()
    merged_df["Owner"] = merged_df["Player Key"].map(owner_lookup)
    merged_df["Owner"] = merged_df["Owner"].replace({None: ""}).fillna("")

    other_columns = [col for col in merged_df.columns if col != "Owner"]
    return merged_df[other_columns + ["Owner"]]


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

    df = merge_owner_from_google_sheets(df, sheet_name="Contracts")

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
    parser = argparse.ArgumentParser(description="Process Spotrac contracts and classify contract types.")

    # Mutually exclusive group for CSV updating
    csv_group = parser.add_mutually_exclusive_group()
    csv_group.add_argument(
        "--update-csv",
        action="store_true",
        dest="update_csv",
        help="Regenerate CSV file (default)",
    )
    csv_group.add_argument(
        "--no-update-csv",
        action="store_false",
        dest="update_csv",
        help="Do not regenerate CSV, load existing instead",
    )
    parser.set_defaults(update_csv=True)

    # Mutually exclusive group for Sheets updating
    sheets_group = parser.add_mutually_exclusive_group()
    sheets_group.add_argument(
        "--update-sheets",
        action="store_true",
        dest="update_sheets",
        help="Update Google Sheets with results",
    )
    sheets_group.add_argument(
        "--no-update-sheets",
        action="store_false",
        dest="update_sheets",
        help="Do not update Google Sheets (default)",
    )
    parser.set_defaults(update_sheets=False)

    parser.add_argument(
        "--sheet",
        dest="sheet_name",
        type=str,
        default="Positions",
        help="Google Sheets tab name to update",
    )

    args = parser.parse_args()

    main(
        update_csv=args.update_csv,
        update_sheets=args.update_sheets,
        sheet_name=args.sheet_name
    )
