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

# Column headers for the final CSV file
headers = ["Player", "Player Link", "Player Key", "Team", "Team Link", "Position", "Age", "2024-25", "2025-26", "2026-27", 
           "2027-28", "2028-29", "2029-30", "2030-31"]

# Function to clean and generate a unique player key from the player's name
def make_player_key(name):
    # Normalize the name to remove non-ASCII characters (e.g., accents) and convert it to ASCII
    normalized_text = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    # Convert the name to lowercase to ensure uniformity
    cleaned_name = normalized_text.lower()
    # Replace spaces with hyphens to generate a URL-friendly player key
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)
    # Remove unwanted punctuation like apostrophes, periods, etc.
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)
    # Strip common suffixes (like Jr., Sr., etc.) from player names to avoid duplicates
    cleaned_name = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name.strip())
    
    return cleaned_name

# Function to extract and clean the team name from the Spotrac URL
def clean_team_name(url):
    team_key = url.split("/")[-2]  # Extract the team name part of the URL
    
    # Split the team name by hyphens and format each part accordingly
    team_key_parts = team_key.split("-")
    formatted_name = " ".join(
        part.upper() if part.lower() == "la"  # Special formatting for "LA" (e.g., Los Angeles)
        else part.capitalize() if part.isalpha()  # Capitalize alphabetic parts (e.g., "hawks" -> "Hawks")
        else part  # Retain numeric parts as they are (e.g., "76ers")
        for part in team_key_parts
    )
    return formatted_name

# Output file path where the data will be saved as CSV
output_file = "salary_data.csv"
# Initialize the CSV file with the headers, overwriting any previous file
pd.DataFrame(columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# List to store the scraped data for all players
all_data = []

total_teams = len(teams)
for idx, team in enumerate(teams):
    # Construct the URL for the current team's salary data page
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    # Clean and format the team name for display and CSV
    team_name = clean_team_name(url)

    # Send a GET request to retrieve the team's salary data page
    response = requests.get(url)
    if response.status_code == 200:  # Ensure the page was successfully retrieved
        soup = BeautifulSoup(response.text, "html.parser")  # Parse the HTML response using BeautifulSoup
        table = soup.select_one("table")  # Select the table containing salary data
        
        if table:  # If the table exists, proceed to scrape data
            rows = table.find_all("tr")  # Find all rows in the table
            for row in rows:
                cols = row.find_all("td")  # Find all columns (cells) in the row
                player_name = ""
                player_link = ""
                position = ""
                age = ""
                salary_data = []

                # Extract player data from the columns
                if len(cols) > 0:
                    player_name_tag = cols[0].find("a")
                    if player_name_tag:
                        player_name = player_name_tag.get_text(strip=True)  # Get the player’s name
                        player_link = player_name_tag["href"]  # Get the player's link
                    player_key = make_player_key(player_name)  # Generate a unique player key
                else:
                    player_key = ""

                # Extract additional player details like position and age
                if len(cols) > 1:
                    position = cols[1].get_text(strip=True)
                if len(cols) > 2:
                    age = cols[2].get_text(strip=True)

                # Extract salary information from the remaining columns
                for col in cols[3:]:
                    cell_text = col.get_text(strip=True)
                    # Detect contract type (e.g., Two-Way, UFA, RFA)
                    if "Two-Way" in cell_text:
                        salary_data.append("Two-Way")
                    elif "UFA" in cell_text:
                        salary_data.append("UFA")
                    elif "RFA" in cell_text:
                        salary_data.append("RFA")
                    else:
                        # Extract actual salary amounts (e.g., "$5,000,000")
                        salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)
                        salary_data.extend(salary_matches)

                # Combine all collected data into a list
                salary_data = [player_name, player_link, player_key, team_name, url, position, age] + salary_data
                # Fill any missing columns with empty values to match the header length
                salary_data += [""] * (len(headers) - len(salary_data))

                # Only append non-empty player data to the list and write to CSV
                if salary_data[0]:
                    all_data.append(salary_data)
                    
                    # Append the data to the CSV file incrementally to avoid data loss
                    pd.DataFrame([salary_data], columns=headers).to_csv(output_file, index=False, mode="a", header=False, encoding="utf-8", quoting=1)

        # Print progress for each team processed
        print(f"Processed {idx + 1}/{total_teams} teams ({((idx + 1) / total_teams) * 100:.2f}%): {team_name}")

# After scraping all teams, sort the data by player key for alphabetical order
sorted_data = sorted(all_data, key=lambda x: x[2].lower())
# Write the sorted data back to the CSV, overwriting the file with the ordered data
pd.DataFrame(sorted_data, columns=headers).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# Print a message indicating sorting and saving is complete
print("Sorting completed. Data has been saved in sorted order.")
