import requests
import re
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup
import pytz
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from time import sleep
import random
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the Google Sheets credentials file path and URL from environment variables
creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
google_sheets_url = os.getenv("GOOGLE_SHEETS_URL")

if not creds_path or not google_sheets_url:
    print("Google Sheets credentials or URL is not set in the environment variables.")
    exit()

# Replace with your local timezone
timezone = pytz.timezone("America/Chicago")

# Function to clean a player's name and generate a unique player key to join across sites
def make_player_key(name):
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_text.lower().strip()  # Convert to lowercase and remove trailing spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

# Retry logic for external requests
def fetch_data_with_retry(url, headers, retries=3, delay=2):
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response  # Successful request
            else:
                print(f"Failed attempt {i + 1}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Attempt {i + 1} failed: {e}")
        sleep(delay + random.uniform(0, 1))  # Randomize delay to avoid retrying in bursts
    print("Max retries reached. Exiting.")
    exit()

# Define the URL
url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Fetch the data using retry logic
response = fetch_data_with_retry(url, headers)

# Parse the HTML
soup = BeautifulSoup(response.content, "html.parser")

# Find the stats table
table = soup.find("table", {"id": "totals_stats"})
if not table:
    print("Table not found. Ensure the page structure has not changed.")
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

# Filter out 'League Average' from the 'Player' column
df = df[df["Player"] != "League Average"]

# Add 'Player Key' column by applying the make_player_key function to the 'Player' column
df["Player Key"] = df["Player"].apply(make_player_key)

# Convert numeric columns to proper types, coercing errors to NaN
numeric_columns = ["PTS", "TRB", "AST", "STL", "BLK", "TOV", "PF", "G", "MP"]
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Replace NaN values with 0 (optional, depending on the data)
df.fillna(0, inplace=True)

# Calculate the new columns
df["FP"] = (
    df["PTS"] + df["TRB"] + df["AST"] + 
    df["STL"] + df["BLK"] - df["TOV"] - df["PF"]
).astype(int)  # FP as integer
df["FPPG"] = (df["FP"] / df["G"]).round(1)  # FPPG formatted to 1 decimal
df["FPPM"] = (df["FP"] / df["MP"]).round(2)  # FPPM formatted to 2 decimals
df["MPG"] = (df["MP"] / df["G"]).round(1)  # MPG formatted to 1 decimal
df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)  # FPPGPM formatted to 1 decimal

# Sort by 'Player Key' column
df = df.sort_values(by=["Player Key", "Team"])

# Define file path using os.path.join for cross-platform compatibility
output_dir = "python/data"
output_filename = "bbref_data.csv"
os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
output_csv = os.path.join(output_dir, output_filename)

# Save to CSV
df.to_csv(output_csv, index=False, quoting=1)

# Get the current datetime in the local timezone
current_time = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")

# Print the completion message with timestamp and timezone
print(f"Data saved to {output_csv} at {current_time}")

# Define the scope for the Google Sheets API
scope = ["https://www.googleapis.com/auth/spreadsheets"]

# Authenticate with Google Sheets API using the path to the credentials stored in the environment variable
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)

# Open the Google Sheets file using the URL loaded from the environment variable
spreadsheet = client.open_by_url(google_sheets_url)

# Access the sheet by its name (e.g., "Stats")
sheet = spreadsheet.worksheet("Stats")  # Change "Stats" to the desired sheet name

# Clear existing content (optional)
sheet.clear()

# Prepare data for batch write (header + rows)
data_to_write = [df.columns.tolist()] + df.values.tolist()

# Batch write data to the sheet
sheet.update("A1", data_to_write)  # Start writing from cell A1

# Get the current datetime in the local timezone
current_time = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")

# Print the completion message with timestamp and timezone
print(f"Data successfully written to the 'Stats' sheet at {current_time}")
