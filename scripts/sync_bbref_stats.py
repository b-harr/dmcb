import os
import sys
import logging
from dotenv import load_dotenv
import pandas as pd

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define data folder path relative to the base directory
#data_dir = os.path.join(base_dir, 'data')

# Append the base_dir to sys.path to make sure modules can be imported
sys.path.append(base_dir)

# Now import your modules
import utils.google_sheets_manager
import utils.data_fetcher
import utils.csv_handler
import utils.text_formatter

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
google_sheets_url = "https://docs.google.com/spreadsheets/d/1NgAl7GSl3jfehz4Sb3SmR_k1-QtQFm55fBPb3QOGYYw"
sheet_name = "Stats"
numeric_columns = "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP".split(",")

def main():
    # Define the URL for data fetching
    url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Fetch the data using the new data_fetcher module
    response = utils.data_fetcher.fetch_data(url, headers)
    
    # Parse the HTML content and extract the required data
    df = utils.data_fetcher.parse_html(response)
    
    # Exclude 'League Average' rows to focus on player-specific data
    df = df[df["Player"] != "League Average"]

    # Check for rows with missing 'Player' and drop them (if any)
    df = df.dropna(subset=["Player"])

    # Add 'Player Key' column by applying the make_player_key function to the 'Player' column
    df["Player Key"] = df["Player"].apply(utils.text_formatter.make_player_key)

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
    output_dir = os.path.join(base_dir, "data")
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
    output_file = "bbref_stats.csv"
    output_csv = os.path.join(output_dir, output_file)

    # Verify value of `output_csv` is a string
    print(f"Output file path: {output_csv}")
    # Save to CSV using the new csv_handler module
    utils.csv_handler.CSVHandler.write_csv(output_csv, df.values.tolist(), headers=df.columns.tolist())

    # Log progress and errors for monitoring script execution
    logger.info(f"Data successfully written to the file: {output_csv}")

    # Authenticate and update Google Sheets via google_sheets_manager
    try:
        timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
        utils.google_sheets_manager.GoogleSheetsManager.clear_data(df, sheet_name="Stats")
        utils.google_sheets_manager.write_data([[f"Last updated {timestamp} by B-Har"]], "A1")
        utils.google_sheets_manager.write_data(df, sheet_name="Stats", start_cell="A2")
        logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
    except Exception as e:
        logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main()
