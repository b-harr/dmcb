import requests
import re
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Function to clean a player's name and generate a unique player key to join across sites
def make_player_key(name):
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_text.lower().strip()  # Convert to lowercase and remove trailing spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

# Define the URL
url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"

# Send a GET request to the URL
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
response = requests.get(url, headers=headers)

# Check if the request was successful
if response.status_code != 200:
    print(f"Failed to fetch data: {response.status_code}")
    exit()

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

# Calculate the new columns
df["FP"] = (
    df["PTS"].astype(float) + df["TRB"].astype(float) + df["AST"].astype(float) + 
    df["STL"].astype(float) + df["BLK"].astype(float) - df["TOV"].astype(float) - df["PF"].astype(float)
).astype(int)  # FP as integer
df["FPPG"] = (df["FP"] / df["G"].astype(float)).round(1)  # FPPG formatted to 1 decimal
df["FPPM"] = (df["FP"] / df["MP"].astype(float)).round(2)  # FPPM formatted to 2 decimals
df["MPG"] = (df["MP"].astype(float) / df["G"].astype(float)).round(1)  # MPG formatted to 1 decimal
df["FPE"] = ((df["FP"] ** 2) / (df["G"].astype(float) * df["MP"].astype(float))).round(1)  # FPPGPM formatted to 1 decimal

# Sort by 'Player Key' column
df = df.sort_values(by="Player Key")

# Authenticate with Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("secrets/dmcb-442123-966817b53d6f.json", scope)
client = gspread.authorize(creds)

# Open the Google Sheets file by URL or title
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1NgAl7GSl3jfehz4Sb3SmR_k1-QtQFm55fBPb3QOGYYw")

# Access the sheet by its name (e.g., "Stats")
sheet = spreadsheet.worksheet("Stats")  # Change "Stats" to the desired sheet name

# Clear existing content (optional)
sheet.clear()

# Prepare data for batch write (header + rows)
data_to_write = [df.columns.tolist()] + df.values.tolist()

# Batch write data to the sheet
sheet.update("A1", data_to_write)  # Start writing from cell A1

# Get the current datetime in the local timezone
import pytz
import datetime
timezone = pytz.timezone("America/Chicago")  # Replace with your local timezone
current_time = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")

# Print the completion message with timestamp and timezone
print(f"Data successfully written to the 'Stats' sheet at {current_time}")
