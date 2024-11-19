import os
import pytz
import datetime
import requests
import random
import unicodedata
import re
import pandas as pd
from time import sleep
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import logging

# Configure logging to track script execution and errors
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Set local timezone and retrieve the current datetime for logging
timezone = pytz.timezone("America/Chicago")

# Log the start message with timestamp and timezone
logger.info(f"Script started")

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

# Clean a player's name and generate a unique key for consistent cross-site merging
def make_player_key(name):
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_text.lower().strip()  # Convert to lowercase and trim spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

# Define the URL
url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

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
    df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"] - df["TOV"] - df["PF"]
).astype(int)
df["FPPG"] = (df["FP"] / df["G"]).round(1)
df["FPPM"] = (df["FP"] / df["MP"]).round(2)
df["MPG"] = (df["MP"] / df["G"]).round(1)
df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)

# Save the output CSV file with a platform-independent path
output_dir = "python/data"
output_filename = "bbref_data.csv"
os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
output_csv = os.path.join(output_dir, output_filename)

# Save to CSV
df.to_csv(output_csv, index=False)

# Set local timezone and retrieve the current datetime for logging
#current_time = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")

# Log progress and errors for monitoring script execution
logger.info(f"Data saved to {output_csv}")

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
    logger.info(f"Data successfully written to the '{sheet_name}' sheet")
except Exception as e:
    logger.error(f"Error updating Google Sheets: {e}")
