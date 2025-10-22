import os
import sys
import logging
import pandas as pd

# Set the root project directory to 2 levels up from the current script location
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# Output directory and file settings
output_dir = "data"
output_file = "nba_stats.csv"
os.makedirs(output_dir, exist_ok=True)
output_csv = os.path.join(output_dir, output_file)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()
logger.info("Script execution started.")

# Import required utilities
from utils.scrape_nba import scrape_nba_totals
from utils.text_formatter import make_player_key
from utils.google_sheets_manager import GoogleSheetsManager

# Columns that require numeric conversion
numeric_columns = ["PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF", "G", "MP"]

def main(year=2026, update_csv=True, update_sheets=False, sheet_name="Stats"):
    """Scrape NBA stats, compute fantasy metrics, and export CSV/Google Sheets."""
    
    # Scrape raw NBA stats
    df = scrape_nba_totals(year)

    # Remove any aggregate rows and missing player names
    df = df[df["Player"] != "League Average"].dropna(subset=["Player"])

    # Generate Player Key
    df["Player Key"] = df["Player"].apply(make_player_key)

    # Add Player Link and Team Link
    df["Player Link"] = df["Player Key"].apply(lambda x: f"https://www.nba.com/player/{x}")
    df["Team Link"] = df["Team"].apply(lambda x: f"https://www.nba.com/team/{x}")

    # Convert numeric columns
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Round minutes to whole numbers
    df["MP"] = df["MP"].round(0).astype(int)

    # Compute fantasy metrics
    df["FP"] = (df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"]
                - df["TOV"] - df["PF"]).astype(int)
    df["FPPG"] = (df["FP"] / df["G"]).round(1)
    df["FPPM"] = (df["FP"] / df["MP"]).round(2)
    df["MPG"] = (df["MP"] / df["G"]).round(1)
    df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)

    # Reorder columns to match original CSV
    column_order = [
        "Player", "Age", "Team", "Pos", "G", "GS", "MP", "FG", "FGA", "FG%",
        "3P", "3PA", "3P%", "2P", "2PA", "2P%", "eFG%", "FT", "FTA", "FT%",
        "ORB", "DRB", "TRB", "AST", "STL", "BLK", "TOV", "PF", "PTS",
        "Trp-Dbl", "Awards", "Player Link", "Team Link", "Player Key",
        "FP", "FPPG", "FPPM", "MPG", "FPR"
    ]

    # Ensure all columns exist in df, fill missing with default 0 or empty string
    for col in column_order:
        if col not in df.columns:
            if col in ["Trp-Dbl", "Awards", "Age", "Pos", "GS", "FG","FGA","FG%",
                       "3P","3PA","3P%","2P","2PA","2P%","eFG%","FT","FTA","FT%",
                       "ORB","DRB"]:
                df[col] = ""
            else:
                df[col] = 0

    # Reorder columns to match original CSV
    df = df[column_order]

    # Sort data by Player Key
    df = df.sort_values(by="Player Key").reset_index(drop=True)
    logger.info("Data sorted by Player Key.")

    # Save to CSV
    if update_csv:
        try:
            target_csv = output_csv if year == 2026 else os.path.join("data/bbref_archive", f"NBA_{year}_totals.csv")
            os.makedirs(os.path.dirname(target_csv), exist_ok=True)
            df.to_csv(target_csv, index=False, encoding="utf-8")
            logger.info(f"Data saved to CSV: {target_csv}")
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
            return

    # Update Google Sheets
    if update_sheets:
        try:
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name=sheet_name)
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))
            sheets_manager.write_data(
                [[f"Last updated {timestamp} by {sheets_manager.service_account_email} from {os.path.basename(__file__)}"]],
                sheet_name=sheet_name,
                start_cell="A1"
            )

            # Clean NaN and Inf values before writing to Google Sheets
            logger.info("Cleaning data before writing to Google Sheets...")
            df = df.replace([float("inf"), float("-inf")], pd.NA).fillna("")

            # Safely write data to Google Sheets
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to Google Sheets: {sheet_name}")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape NBA stats and export to CSV or Google Sheets.")

    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="NBA season year (e.g., 2025 for 2024-25 season). Default is 2026."
    )

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
        default="Stats",
        help="Google Sheets tab name to update",
    )

    args = parser.parse_args()

    main(
        year=args.year,
        update_csv=args.update_csv,
        update_sheets=args.update_sheets,
        sheet_name=args.sheet_name
    )
