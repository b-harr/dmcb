import os
import sys
import logging
import pandas as pd

# Get the root project directory (2 levels up from the current script)
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Append the base_dir to sys.path to ensure modules can be imported
sys.path.append(base_dir)

# Create the path for file
output_dir = "data"
output_file = "bbref_stats.csv"

# Ensure the output folder exists
os.makedirs(output_dir, exist_ok=True)

# Define the full file path for the CSV file
output_csv = os.path.join(output_dir, output_file)

# Configure logging to capture detailed script execution and errors
logging.basicConfig(
    level=logging.INFO,  # Log messages with level INFO and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Log the script start with a timestamp to track execution
logger.info("The script started successfully.")

from utils.scrape_bbref import scrape_nba_totals
from utils.text_formatter import make_player_key
from utils.google_sheets_manager import GoogleSheetsManager

numeric_columns = "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP".split(",")  # Columns to be used for numerical calculations

def main(year=2025, update_csv=True, update_sheets=False, sheet_name="Stats"):
    df = scrape_nba_totals(year)
    
    # Exclude 'League Average' rows to focus on individual player stats
    df = df[df["Player"] != "League Average"]

    # Check for and drop any rows with missing player names
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
    
    if update_csv == True:
        if year == 2025:  # Only sync to Google Sheets for the default year
            logger.info(f"Saving data to CSV file: {output_csv}")
            try:
                df.to_csv(output_csv, mode="w", index=False, encoding="utf-8")
                logger.info(f"Data successfully written to the CSV file: {output_csv}")
            except Exception as e:
                logger.error(f"Error saving data to CSV: {e}")
                return
            
        else:
            # Generate a dynamic alternate file path using the year
            archive_dir = "data/bbref_archive"
            archive_file = f"NBA_{year}_totals.csv"

            # Ensure the archive folder exists
            os.makedirs(archive_dir, exist_ok=True)

            # Define the path to the archive CSV
            archive_csv = os.path.join(archive_dir, archive_file)
            logger.info(f"Saving data to alternate CSV file: {archive_csv}")
            try:
                df.to_csv(archive_csv, mode="w", index=False, encoding="utf-8")
                logger.info(f"Data successfully written to alternate CSV file: {archive_csv}")
            except Exception as e:
                logger.error(f"Error saving data to alternate CSV: {e}")

    if update_sheets == True:
        # Authenticate and update the Google Sheets with the processed data
        try:
            # Get the current timestamp to indicate when the data was last updated
            timestamp = logging.Formatter('%(asctime)s').format(logging.LogRecord("", 0, "", 0, "", [], None))  # Get the current timestamp
            
            # Initialize Google Sheets manager and clear existing data in the sheet
            sheets_manager = GoogleSheetsManager()
            sheets_manager.clear_data(sheet_name="Stats")
            logger.info(f"Cleared existing data in Google Sheets '{sheet_name}'.")

            # Write the timestamp to Google Sheets
            sheets_manager.write_data([[f"Last updated {timestamp} by {sheets_manager.service_account_email}"]], sheet_name="Stats", start_cell="A1")
            logger.info("Wrote timestamp to Google Sheets.")

            # Write the processed data to the 'Stats' sheet
            sheets_manager.write_data([df.columns.tolist()] + df.values.tolist(), sheet_name="Stats", start_cell="A2")
            logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
        except Exception as e:
            logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main(update_sheets=True)
    #main(year=2024)
