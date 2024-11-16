import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import unicodedata

# List of NBA teams to scrape salary data for
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
def make_player_key(name):
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    cleaned_name = normalized_text.lower()
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)
    cleaned_name = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name.strip())
    return cleaned_name

# Function to extract and clean the team name from the Spotrac URL
def clean_team_name(url):
    team_key = url.split("/")[-2]
    team_key_parts = team_key.split("-")
    formatted_name = " ".join(
        part.upper() if part.lower() == "la" else part.capitalize() if part.isalpha() else part
        for part in team_key_parts
    )
    return formatted_name

# Output file path
output_file = "salary_data.csv"

# List to store all data
all_data = []

# Extract dynamic season headers from any team's table
def extract_season_headers(teams):
    for team in teams:
        url = f"https://www.spotrac.com/nba/{team}/yearly"
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.select_one("table")
            if table:
                header_row = table.find("tr")  # First row in the table
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
                    # Filter headers matching the season format "YYYY-YY"
                    season_headers = [header for header in headers if re.match(r"^\d{4}-\d{2}$", header)]
                    if season_headers:
                        print(f"Season headers extracted from team: {team}")
                        return season_headers
    print("Failed to extract season headers. Please check the team URLs or table structure.")
    return []  # Return an empty list if no headers are found

# Extract headers dynamically from the list of teams
season_headers = extract_season_headers(teams)
if not season_headers:
    raise ValueError("Season headers could not be determined. Check table structure or team data.")

# Define CSV headers
headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age"] + season_headers
pd.DataFrame(columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# Loop through each team
total_teams = len(teams)
for idx, team in enumerate(teams):
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    team_name = clean_team_name(url)
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table")
        
        if table:
            rows = table.find_all("tr")
            for row in rows[1:]:  # Skip header row
                cols = row.find_all("td")
                player_name = ""
                player_link = ""
                position = ""
                age = ""
                salary_data = []

                if len(cols) > 0:
                    player_name_tag = cols[0].find("a")
                    if player_name_tag:
                        player_name = player_name_tag.get_text(strip=True)
                        player_link = player_name_tag["href"]
                    player_key = make_player_key(player_name)
                else:
                    player_key = ""

                if len(cols) > 1:
                    position = cols[1].get_text(strip=True)
                if len(cols) > 2:
                    age = cols[2].get_text(strip=True)

                for col in cols[3:]:
                    cell_text = col.get_text(strip=True)
                    if "Two-Way" in cell_text:
                        salary_data.append("Two-Way")
                    elif "UFA" in cell_text:
                        salary_data.append("UFA")
                    elif "RFA" in cell_text:
                        salary_data.append("RFA")
                    else:
                        salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)
                        salary_data.extend(salary_matches)

                salary_data = [player_name, player_link, player_key, team_name, url, position, age] + salary_data
                salary_data += [""] * (len(headers) - len(salary_data))

                if salary_data[0]:
                    all_data.append(salary_data)
                    pd.DataFrame([salary_data], columns=headers).to_csv(output_file, index=False, mode="a", header=False, encoding="utf-8", quoting=1)

        print(f"Processed {idx + 1}/{total_teams} teams ({((idx + 1) / total_teams) * 100:.2f}%): {team_name}")

sorted_data = sorted(all_data, key=lambda x: x[2].lower())
pd.DataFrame(sorted_data, columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

print("Sorting completed. Data has been saved in sorted order.")
