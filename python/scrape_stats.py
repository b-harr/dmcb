import requests
import re
import unicodedata
import pandas as pd
import os
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pytz
import datetime

# Function to clean a player's name and generate a unique player key to join across sites
def make_player_key(name):
    """Normalize and clean player name for unique key generation."""
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_text.lower().strip()  # Convert to lowercase and remove trailing spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

# Function to fetch and parse NBA stats data from the provided URL
def fetch_data(url):
    """Fetch and parse the NBA data from the specified URL."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from URL: {e}")
        return None

    # Parse the HTML
    soup = BeautifulSoup(response.content, "html.parser")
    return soup

# Function to process the NBA player stats and perform calculations
def process_stats(soup):
    """Extract player stats from HTML and calculate additional statistics."""
    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        print("Table not found. Ensure the page structure has not changed.")
        return None

    headers = [th.get_text() for th in table.find("thead").find_all("th")]
    headers = headers[1:]  # Remove the first blank column header

    rows = table.find("tbody").find_all("tr")
    data = []
    for row in rows:
        # Skip rows without data (e.g., separator rows)
        if row.find("td"):
            row_data = [td.get_text() for td in row.find_all("td")]
            data.append(row_data)

    df = pd.DataFrame(data, columns=headers)

    # Filter out 'League Average' from the 'Player' column
    df = df[df["Player"] != "League Average"]

    # Add 'Player Key' column by applying the make_player_key function to the 'Player' column
    df["Player Key"] = df["Player"].apply(make_player_key)

    # Calculate new columns (Fantasy Points, FPPG, FPPM, MPG, FPR)
    df["FP"] = (
        df["PTS"].astype(float) + df["TRB"].astype(float) + df["AST"].astype(float) + 
        df["STL"].astype(float) + df["BLK"].astype(float) - df["TOV"].astype(float) - df["PF"].astype(float)
    ).astype(int)  # FP as integer
    df["FPPG"] = (df["FP"] / df["G"].astype(float)).round(1)  # FPPG formatted to 1 decimal
    df["FPPM"] = (df["FP"] / df["MP"].astype(float)).round(2)  # FPPM formatted to 2 decimals
    df["MPG"] = (df["MP"].astype(float) / df["G"].astype(float)).round(1)  # MPG formatted to 1 decimal
    df["FPR"] = ((df["FP"] ** 2) / (df["G"].astype(float) * df["MP"].astype(float))).round(1)  # FPPGPM formatted to 1 decimal

    # Sort by Player Key and Team columns
    df = df.sort_values(by=["Player Key", "Team"])

    return df

# Function to save the DataFrame to a CSV file
def save_to_csv(df, output_path):
    """Save the DataFrame to a CSV file at the specified path."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Create directories if they don't exist
    df.to_csv(output_path, index=False, quoting=1)
    print(f"Data saved to {output_path}")

# Function to get the current timestamp in the local timezone
def get_current_timestamp():
    """Get the current timestamp in the local timezone."""
    timezone = pytz.timezone("America/Chicago")
    current_time = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")
    return current_time

# Function to authenticate and update data to Google Sheets
def update_google_sheets(df, sheet_url, creds_file):
    """Authenticate and update the Google Sheet with the DataFrame."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
    except Exception as e:
        print(f"Error authenticating with Google Sheets: {e}")
        return

    try:
        # Open the Google Sheets file
        spreadsheet = client.open_by_url(sheet_url)
        sheet = spreadsheet.worksheet("Stats")  # Change "Stats" to the desired sheet name
        sheet.clear()  # Clear existing content

        # Prepare data for batch write (header + rows)
        data_to_write = [df.columns.tolist()] + df.values.tolist()

        # Update the Google Sheet
        sheet.update("A1", data_to_write)
        print(f"Data successfully written to the 'Stats' sheet")
    except Exception as e:
        print(f"Error updating Google Sheets: {e}")

# Main function to execute the script
def main():
    url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"
    output_csv = os.path.join("python", "data", "bbref_data.csv")
    sheet_url = "https://docs.google.com/spreadsheets/d/1NgAl7GSl3jfehz4Sb3SmR_k1-QtQFm55fBPb3QOGYYw"
    creds_file = "secrets/dmcb-442123-966817b53d6f.json"

    print("Starting script execution...")

    # Step 1: Fetch and parse the data
    soup = fetch_data(url)
    if not soup:
        print("Data fetch failed. Exiting script.")
        return

    # Step 2: Process the stats data
    df = process_stats(soup)
    if df is None:
        print("Data processing failed. Exiting script.")
        return

    # Step 3: Save to CSV
    save_to_csv(df, output_csv)

    # Step 4: Update Google Sheets
    update_google_sheets(df, sheet_url, creds_file)

    # Step 5: Print the current timestamp
    current_time = get_current_timestamp()
    print(f"Script completed successfully at {current_time}")

# Run the main function
if __name__ == "__main__":
    main()
