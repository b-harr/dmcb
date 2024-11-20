import os
import requests
import random
import pandas as pd
from time import sleep
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import logging
import utils

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
creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
google_sheets_url = os.getenv("GOOGLE_SHEETS_URL")
sheet_name = os.getenv("SHEET_NAME", "Stats")  # Default to "Stats"
numeric_columns = os.getenv("NUMERIC_COLUMNS", "PTS,TRB,AST,STL,BLK,TOV,PF,G,MP").split(",")

# Ensure Google Sheets credentials and URL are provided
if not creds_path or not google_sheets_url:
    raise ValueError("Google Sheets credentials or URL is not properly set.")

# Handle external requests with retry logic to manage failures and ensure data retrieval
def fetch_data_with_retry(url, headers, retries=3, delay=2):
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response
            else:
                logger.warning(f"Failed attempt {i + 1}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
        sleep(delay + random.uniform(0, 1))  # Randomize delay to reduce server load
    logger.error("Max retries reached. Exiting.")
    exit()

def main():
    # Define the URL
    url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Fetch the data using retry logic
    response = fetch_data_with_retry(url, headers)

    # Parse the HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # Locate the stats table; exit if not found to prevent further errors
    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        logger.error("Table not found. Ensure the page structure has not changed.")
        exit()

    # Extract the table headers
    headers = [th.get_text() for th in table.find("thead").find_all("th")]
    headers = headers[1:]  # Remove the first blank column header

    # Extract the rows
    rows = table.find("tbody").find_all("tr")
    data = []
    for row in rows:
        # Skip rows without data (e.g., separator rows)
        if row.find("td"):
            row_data = [td.get_text() for td in row.find_all("td")]
            data.append(row_data)

    # Create a DataFrame
    df = pd.DataFrame(data, columns=headers)

    # Exclude 'League Average' rows to focus on player-specific data
    df = df[df["Player"] != "League Average"]

    # Check for rows with missing 'Player' and drop them (if any)
    df = df.dropna(subset=["Player"])

    # Add 'Player Key' column by applying the make_player_key function to the 'Player' column
    df["Player Key"] = df["Player"].apply(utils.make_player_key)

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

    # Save the output CSV file with a platform-independent path
    output_dir = "python/data"
    output_filename = "bbref_stats.csv"
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
    output_csv = os.path.join(output_dir, output_filename)

    # Save to CSV
    df.to_csv(output_csv, index=False)

    # Log progress and errors for monitoring script execution
    logger.info(f"Data successfully written to the file: {output_csv}")

    # Define API scope for Google Sheets to enable read/write operations
    scope = ["https://www.googleapis.com/auth/spreadsheets"]

    # Authenticate with Google Sheets API, clear the existing sheet, and write the updated data
    try:
        # Authenticate and access the spreadsheet
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(google_sheets_url)
        sheet = spreadsheet.worksheet(sheet_name)

        # Clear and update the sheet
        sheet.clear()
        data_to_write = [df.columns.tolist()] + df.values.tolist()
        sheet.update(data_to_write, "A1")

        # Log progress and errors for monitoring script execution
        logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
    except Exception as e:
        logger.error(f"Error updating Google Sheets: {e}")

# Ensure the script only runs when executed directly, not when imported
if __name__ == "__main__":
    main()
