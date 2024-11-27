import os
import sys

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to make sure modules can be imported
sys.path.append(base_dir)

# Now import your modules
import config
from utils.google_sheets_manager import GoogleSheetsManager
from utils.csv_handler import CSVHandler
from utils.data_fetcher import fetch_data, parse_html
from utils.text_formatter import make_player_key

import logging
from dotenv import load_dotenv
import pandas as pd

# Configure logging to track script execution and errors
logging.basicConfig(
    level=logging.INFO,  # Log all levels INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the start message with timestamp and timezone
logger.info("The script started successfully.")

# Load environment variables
load_dotenv()

# Retrieve environment variables
google_sheets_url = config.google_sheets_url
sheet_name = "Stats"
numeric_columns = "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP".split(",")

def main(year=2025):
    # Define the URL for data fetching
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Fetch the data using the new data_fetcher module
    response = fetch_data(url, headers)
    # Parse the HTML content and extract the required data
    df = parse_html(response)
    
    # Exclude 'League Average' rows to focus on player-specific data
    df = df[df["Player"] != "League Average"]
    # Check for rows with missing 'Player' and drop them (if any)
    df = df.dropna(subset=["Player"])

    # Add 'Player Key' column by applying the make_player_key function to the 'Player' column
    df["Player Key"] = df["Player"].apply(make_player_key)
    # Sort by 'Player Key' and 'Team' columns
    df = df.sort_values(by=["Player Key", "Team"])

    # Convert columns to numeric values and apply vectorized operations for efficient calculations
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    # Fill NaN values with 0 in one operation
    df.fillna(0, inplace=True)

    # Vectorized calculations for new columns
    df["FP"] = (
        df["PTS"] + df["TRB"] + df["AST"] + 
        df["STL"] + df["BLK"] - df["TOV"] - df["PF"]
    ).astype(int)  # Fantasy Points: PTS/REB/AST/STL/BLK +1, TO/PF/TF -1
    df["FPPG"] = (df["FP"] / df["G"]).round(1)  # Fantasy Points Per Game
    df["FPPM"] = (df["FP"] / df["MP"]).round(2)  # Fantasy Points Per Minute
    df["MPG"] = (df["MP"] / df["G"]).round(1)  # Minutes Per Game
    df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)  # Fantasy Point Rating = FPPG * FPPM = (FP ** 2) / (G * MP)

    # Use BASE_PATH from config.py for saving output
    output_csv = config.bbref_stats_path

    # Save to CSV using the new csv_handler module
    CSVHandler.write_csv(output_csv, df.values.tolist(), headers=df.columns.tolist())

    # Log progress and errors for monitoring script execution
    logger.info(f"Data successfully written to the file: {output_csv}")

    # Authenticate and update Google Sheets via google_sheets_manager
    try:
        timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
        sheets_manager = GoogleSheetsManager()
        sheets_manager.clear_data(sheet_name="Stats")
        sheets_manager.write_data([[f"Last updated {timestamp} by {config.service_account_email}"]], sheet_name="Stats", start_cell="A1")
        sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name="Stats", start_cell="A2")
        logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
    except Exception as e:
        logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main()
