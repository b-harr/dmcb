import requests
import re
import unicodedata
import pandas as pd
from bs4 import BeautifulSoup
import pytz
from datetime import datetime

# Function to clean a player's name and generate a unique player key to join across sites
def make_player_key(name):
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Replace accents
    cleaned_name = normalized_text.lower().strip()  # Convert to lowercase and remove trailing spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

# Function to scrape data for a given year and save it to a year-specific file
def scrape_bbref_data(year, output_path="python/data/totals"):
    # Define the URL dynamically
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to fetch data for {year}: {response.status_code}")
        return

    # Parse the HTML
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the stats table
    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        print(f"Table not found for {year}. Ensure the page structure has not changed.")
        return

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

    # Sort by 'Player Key' column
    df = df.sort_values(by="Player Key")

    # Save to a year-specific CSV file in 'python/data/totals'
    output_csv = f"{output_path}/NBA_{year}_totals.csv"
    df.to_csv(output_csv, index=False, quoting=1)

    # Get the current datetime in the local timezone
    timezone = pytz.timezone("America/Chicago")  # Replace with your local timezone
    current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")

    # Print the completion message with timestamp and file location
    print(f"Data for {year} saved to {output_csv} at {current_time}")

# Example usage: Scrape data for multiple years
if __name__ == "__main__":
    for year in range(2020, 2025):  # Adjust the range as needed
        scrape_bbref_data(year)
