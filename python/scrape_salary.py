import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import unicodedata

# List of NBA teams to scrape salary data for
# Each entry corresponds to the team's Spotrac URL identifier
teams = [
    "atlanta-hawks", "brooklyn-nets", "boston-celtics", "charlotte-hornets",
    "cleveland-cavaliers", "chicago-bulls", "dallas-mavericks", "denver-nuggets",
    "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers",
    "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat",
    "milwaukee-bucks", "minnesota-timberwolves", "new-york-knicks",
    "new-orleans-pelicans", "oklahoma-city-thunder", "orlando-magic",
    "philadelphia-76ers", "phoenix-suns", "portland-trail-blazers",
    "san-antonio-spurs", "sacramento-kings", "toronto-raptors",
    "utah-jazz", "washington-wizards"
]

# Function to clean and generate a unique player key from the player's name
# Normalizes the name (e.g., removes accents), converts to lowercase, replaces spaces with hyphens,
# removes special characters, and strips suffixes (like "Jr.", "III").
def make_player_key(name):
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_text.lower()  # Convert to lowercase
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    cleaned_name = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name.strip())  # Remove common suffixes
    return cleaned_name

# Function to extract and clean the team name from the Spotrac URL
# Formats the team name from the URL (e.g., "san-antonio-spurs" -> "San Antonio Spurs")
def clean_team_name(url):
    team_key = url.split("/")[-2]  # Extracts the team identifier from the URL
    team_key_parts = team_key.split("-")  # Splits the identifier into components
    # Capitalizes each word, with special handling
    formatted_name = " ".join(
        part.upper() if part.lower() == "la"  # Capitalize "LA" specifically (e.g. "Los Angeles")
        else part.capitalize() if part.isalpha()  # Capitalize alphabetic parts only (e.g., "Spurs")
        else part  # Retain numeric parts as they are (e.g., "76ers")
        for part in team_key_parts
    )
    return formatted_name

# File path for saving the output CSV
output_file = "salary_data.csv"

# List to store all salary data collected during scraping
all_data = []

# Function to extract dynamic season headers from a team's salary table
# This ensures the script captures season columns dynamically
def extract_season_headers(teams):
    for team in teams:
        url = f"https://www.spotrac.com/nba/{team}/yearly"
        response = requests.get(url)
        if response.status_code == 200:  # Check if the request is successful
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.select_one("table")  # Locate the first table in the page
            if table:
                header_row = table.find("tr")  # Find the header row
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
                    # Filter headers matching the season format "YYYY-YY"
                    season_headers = [header for header in headers if re.match(r"^\d{4}-\d{2}$", header)]
                    if season_headers:  # Return headers if found
                        print(f"Season headers extracted from team: {clean_team_name(url)}")
                        return season_headers
    print("Failed to extract season headers. Please check the team URLs or table structure.")
    return []  # Return an empty list if no headers are found

# Extract headers dynamically from the list of teams
season_headers = extract_season_headers(teams)
if not season_headers:
    raise ValueError("Season headers could not be determined. Check table structure or team data.")

# Define CSV headers for the output file
headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + season_headers
# Create an empty CSV file with the defined headers
pd.DataFrame(columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# Loop through each team to scrape data
total_teams = len(teams)
for idx, team in enumerate(teams):
    url = f"https://www.spotrac.com/nba/{team}/yearly"  # Construct the team's URL
    team_name = clean_team_name(url)  # Extract and clean the team name
    response = requests.get(url)

    if response.status_code == 200:  # If the request is successful
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table")  # Locate the salary table
        
        if table:
            rows = table.find_all("tr")  # Extract all rows from the table
            for row in rows[1:]:  # Skip the header row
                cols = row.find_all("td")  # Extract all columns for the row
                player_name = ""
                player_link = ""
                position = ""
                age = ""
                salary_data = []

                if len(cols) > 0:
                    player_name_tag = cols[0].find("a")  # Find the player link in the first column
                    if player_name_tag:
                        player_name = player_name_tag.get_text(strip=True)
                        player_link = player_name_tag["href"]
                    player_key = make_player_key(player_name)  # Generate the player key
                else:
                    player_key = ""

                if len(cols) > 1:  # Extract the player's position
                    position = cols[1].get_text(strip=True)
                if len(cols) > 2:  # Extract the player's age
                    age = cols[2].get_text(strip=True)

                for col in cols[3:]:  # Extract salary data from remaining columns
                    cell_text = col.get_text(strip=True)
                    if "Two-Way" in cell_text:
                        salary_data.append("Two-Way")
                    elif "UFA" in cell_text:
                        salary_data.append("UFA")
                    elif "RFA" in cell_text:
                        salary_data.append("RFA")
                    else:  # Extract numeric salary values
                        salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)
                        salary_data.extend(salary_matches)

                # Combine all collected data into a single row
                salary_data = [player_name, player_link, player_key, team_name, url, position, age] + salary_data
                salary_data += [""] * (len(headers) - len(salary_data))  # Ensure row matches the header length

                if salary_data[0]:  # Only save data if player name exists
                    all_data.append(salary_data)
                    pd.DataFrame([salary_data], columns=headers).to_csv(output_file, index=False, mode="a", header=False, encoding="utf-8", quoting=1)

        print(f"Processed {idx + 1}/{total_teams} teams ({((idx + 1) / total_teams) * 100:.2f}%): {team_name}")

# Sort all data by the player key for consistency
sorted_data = sorted(all_data, key=lambda x: x[2].lower())
# Overwrite the CSV with sorted data
pd.DataFrame(sorted_data, columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

print("Sorting completed. Data has been saved in sorted order.")
