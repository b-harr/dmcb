import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import unicodedata

# List of NBA teams used for constructing URLs to scrape salary data
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

# Define column headers for the CSV output file (updated to reflect the changes)
headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age", "2024-25", "2025-26", "2026-27", 
           "2027-28", "2028-29", "2029-30", "2030-31"]

# Normalizes and cleans player names by removing non-alphanumeric characters,
# converting to lowercase, and inserting hyphens between words that should be combined.
def clean_player_name(name):
    # Normalize the text and remove non-ASCII characters
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    cleaned_name = re.sub(r"\s+", "-", normalized_text.strip())  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove any other unwanted characters
    return cleaned_name.lower()

# Removes common suffixes such as -sr, -jr, -ii, etc., from player names
# to ensure consistency in name formatting.
def remove_suffix(player_name):
    return re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", player_name)

# Extracts the team name from the URL and formats it by capitalizing each word
# and handling the special case of 'LA' for Los Angeles teams.
def clean_team_name(url):
    path = url.replace("https://www.spotrac.com/nba/", "").strip("/")
    team_name = path.split("/")[0]
    team_name_parts = team_name.split("-")
    formatted_name = " ".join(
        part.upper() if part.lower() == "la" 
        else part.capitalize() if part.isalpha() 
        else part for part in team_name_parts
    )
    return formatted_name

# Prepare the CSV file with headers
output_file = "salary_data.csv"
pd.DataFrame(columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# List to store collected data from all teams
all_data = []

# Loops through each team, scraping player salary data and appending it to the CSV file.
# Includes progress tracking for feedback during execution.
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
            for row in rows:
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
                    cleaned_player_name = clean_player_name(player_name)
                    # Apply the remove_suffix function here
                    cleaned_player_name_no_suffix = remove_suffix(cleaned_player_name)  # Cleaned name without suffix
                else:
                    cleaned_player_name = cleaned_player_name_no_suffix = ""

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

                # Add the cleaned player name without suffix to the data row
                salary_data = [player_name, player_link, cleaned_player_name_no_suffix, team_name, url, position, age] + salary_data
                salary_data += [""] * (len(headers) - len(salary_data))
                if salary_data[0]:
                    all_data.append(salary_data)
                    
                    # Append data to CSV incrementally
                    pd.DataFrame([salary_data], columns=headers).to_csv(output_file, index=False, mode="a", header=False, encoding="utf-8", quoting=1)

        # Print progress to the console with team name
        print(f"Processed {idx + 1}/{total_teams} teams ({((idx + 1) / total_teams) * 100:.2f}%): {url.split("/")[-2]}")

# Final sorting by player-name and saving to CSV
sorted_data = sorted(all_data, key=lambda x: x[2].lower())  # Sort by the 'player-name' column (index 2)
pd.DataFrame(sorted_data, columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# Sorting completion message
print("Sorting completed. Data has been saved in sorted order.")
