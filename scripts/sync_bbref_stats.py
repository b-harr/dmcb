import os
import sys
import logging
from dotenv import load_dotenv
import pandas as pd

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to make sure modules can be imported
sys.path.append(base_dir)

# Import custom modules for the script
import config
from utils.google_sheets_manager import GoogleSheetsManager
from utils.csv_handler import CSVHandler
from utils.data_fetcher import fetch_data, parse_html
from utils.text_formatter import make_player_key

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,  # Log messages with level INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

# Load environment variables from the .env file
load_dotenv()
logger.info("Environment variables loaded successfully.")

# Retrieve necessary configuration values from the config module
google_sheets_url = config.google_sheets_url
sheet_name = "Stats"  # Name of the sheet where data will be written
numeric_columns = "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP".split(",")  # Columns to be used for numerical calculations
logger.debug(f"Using numeric columns: {numeric_columns}")

def main(year=2025):
    """
    Main function to fetch, process, and store NBA player stats for the given year.
    It fetches data from Basketball-Reference, processes it, calculates fantasy points,
    and stores the result both in a CSV file and Google Sheets (only for the default year).
    """
    # Construct the URL for the requested year's player stats page on Basketball-Reference
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"
    logger.info(f"Fetching data from URL: {url}")
    
    # Set the request headers for fetching data
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Fetch the HTML data from the Basketball-Reference website
    try:
        response = fetch_data(url, headers)
        logger.info(f"Data fetched successfully from {url}.")
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return

    # Parse the HTML content to extract player stats into a DataFrame
    try:
        df = parse_html(response)
        logger.info("HTML parsed successfully into a DataFrame.")
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return

    # Exclude 'League Average' rows to focus on individual player stats
    df = df[df["Player"] != "League Average"]
    logger.info(f"Excluded 'League Average' rows. Data size is now {len(df)} rows.")

    # Check for and drop any rows with missing player names
    missing_players = df[df["Player"].isna()]
    if not missing_players.empty:
        logger.warning(f"Dropped {len(missing_players)} rows with missing player data.")
    df = df.dropna(subset=["Player"])

    # Add a 'Player Key' column by applying the make_player_key function to the 'Player' column
    df["Player Key"] = df["Player"].apply(make_player_key)
    logger.info("Added 'Player Key' column to DataFrame.")

    # Sort the DataFrame by 'Player Key' and 'Team' columns for organized output
    df = df.sort_values(by=["Player Key", "Team"])
    logger.info("Sorted DataFrame by 'Player Key' and 'Team'.")

    # Drop duplicates based on 'Player Key', keeping the first occurrence
    df = df.drop_duplicates(subset='Player Key', keep='first')
    logger.info("Removed individual teams when more than one.")

    # Convert specified numeric columns to proper numeric types for calculations
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
    logger.info(f"Converted numeric columns: {numeric_columns} to numeric types.")

    # Replace any NaN values with 0 across the DataFrame to prevent errors in calculations
    df.fillna(0, inplace=True)
    logger.info("Filled NaN values with 0.")

    # Perform vectorized calculations to compute fantasy points and related stats
    try:
        # Calculate Fantasy Points (FP) as a sum of positive stats and negative ones
        df["FP"] = (
            df["PTS"] + df["TRB"] + df["AST"] + 
            df["STL"] + df["BLK"] - df["TOV"] - df["PF"]
        ).astype(int)  # Fantasy Points: PTS/REB/AST/STL/BLK +1, TO/PF/TF -1
        df["FPPG"] = (df["FP"] / df["G"]).round(1)  # Fantasy Points Per Game
        df["FPPM"] = (df["FP"] / df["MP"]).round(2)  # Fantasy Points Per Minute
        df["MPG"] = (df["MP"] / df["G"]).round(1)  # Minutes Per Game
        df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)  # Fantasy Point Rating = FPPG * FPPM = (FP ** 2) / (G * MP)

        logger.info("Calculated new fantasy stats (FP, FPPG, FPPM, MPG, FPR).")
    except Exception as e:
        logger.error(f"Error during calculations: {e}")
        return

    # Define the file path where the processed data will be saved
    if year == 2025:  # Only sync to Google Sheets for the default year
        output_csv = config.bbref_stats_path
        logger.info(f"Saving data to CSV file: {output_csv}")
        # Save the processed data to a CSV file
        try:
            CSVHandler.write_csv(output_csv, df.values.tolist(), headers=df.columns.tolist())
            logger.info(f"Data successfully written to the CSV file: {output_csv}")
        except Exception as e:
            logger.error(f"Error saving data to CSV: {e}")
            return

        # Authenticate and update the Google Sheets with the processed data
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name="Stats")
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {config.service_account_email}"]], sheet_name="Stats", start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data to the 'Stats' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name="Stats", start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")
    
    else:
        # Generate a dynamic alternate file path using the year
        alternate_output_path = f"data/bbref_stats_{year}.csv"  # Path for alternate CSV output
        logger.info(f"Saving data to alternate CSV file: {alternate_output_path}")
        try:
            CSVHandler.write_csv(alternate_output_path, df.values.tolist(), headers=df.columns.tolist())
            logger.info(f"Data successfully written to alternate CSV file: {alternate_output_path}")
        except Exception as e:
            logger.error(f"Error saving data to alternate CSV: {e}")

if __name__ == "__main__":
    main()
    #main(year=2024)
    #main(year=2023)
