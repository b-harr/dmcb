import os
import sys
import logging
import pandas as pd

# Set the root project directory to 2 levels up from the current script location
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ensure the base directory is in the Python module search path
sys.path.append(base_dir)

# Output directory and file settings
output_dir = "data"
output_file = "bbref_stats.csv"

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Define the full file path for the output CSV file
output_csv = os.path.join(output_dir, output_file)

# Configure logging to track script execution and errors
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

logger.info("Script execution started.")

# Import required custom utilities
from utils.scrape_bbref import scrape_nba_totals
from utils.text_formatter import make_player_key
from utils.google_sheets_manager import GoogleSheetsManager

# Columns that require numeric conversion for calculations
numeric_columns = ["PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF", "G", "MP"]

def main(year=2025, update_csv=True, update_sheets=False, sheet_name="Stats"):
    """Main function to scrape NBA stats, process data, and optionally update CSV or Google Sheets.

    Args:
        year (int): The NBA season year for data extraction.
        update_csv (bool): Flag to control whether to save data to a CSV file.
        update_sheets (bool): Flag to control whether to update Google Sheets.
        sheet_name (str): The name of the Google Sheets tab to update.
    """
    # Scrape NBA stats data from Basketball-Reference
    df = scrape_nba_totals(year)

    # Remove aggregate rows (e.g., "League Average") and entries with missing player names
    df = df[df["Player"] != "League Average"].dropna(subset=["Player"])

    # Add a 'Player Key' column for unique player identification
    df["Player Key"] = df["Player"].apply(make_player_key)
    logger.info("Generated 'Player Key' column.")

    # Sort data for consistency and drop duplicates by 'Player Key'
    df = df.sort_values(by=["Player Key", "Team"]).drop_duplicates(subset="Player Key")
    logger.info("Sorted data and removed duplicate players.")

    # Convert relevant columns to numeric types and handle missing values
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    logger.info(f"Processed numeric columns: {numeric_columns}.")

    # Compute advanced fantasy metrics
    try:
        df["FP"] = (df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"]
                    - df["TOV"] - df["PF"]).astype(int)  # Fantasy Points: PTS/REB/AST/STL/BLK +1, TO/PF/TF -1
        df["FPPG"] = (df["FP"] / df["G"]).round(1)  # Fantasy Points Per Game
        df["FPPM"] = (df["FP"] / df["MP"]).round(2)  # Fantasy Points Per Minute
        df["MPG"] = (df["MP"] / df["G"]).round(1)  # Minutes Per Game
        df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)  # Fantasy Point Rating = FPPG * FPPM = (FP ** 2) / (G * MP)
        logger.info("Calculated fantasy metrics (FP, FPPG, FPPM, MPG, FPR).")
    except Exception as e:
        logger.error(f"Error during metric calculations: {e}")
        return

    # Save data to CSV
    if update_csv:
        try:
            target_csv = output_csv if year == 2025 else os.path.join("data/bbref_archive", f"NBA_{year}_totals.csv")
            os.makedirs(os.path.dirname(target_csv), exist_ok=True)
            df.to_csv(target_csv, index=False, encoding="utf-8")
            logger.info(f"Data saved to CSV: {target_csv}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            return

    # Update Google Sheets
    if update_sheets:
        try:
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name=sheet_name)
            logger.info(f"Cleared existing data in Google Sheets: {sheet_name}")

            # Add a timestamp to indicate when the sheet was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))
            sheets_manager.write_data([[f"Last updated {timestamp}"]], sheet_name=sheet_name, start_cell="A1")
            logger.info("Added timestamp to Google Sheets.")

            # Write the processed DataFrame to Google Sheets
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name=sheet_name, start_cell="A2")
            logger.info(f"Data successfully written to Google Sheets: {sheet_name}")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main(update_csv=True, update_sheets=True)
    #main(year=2024)
