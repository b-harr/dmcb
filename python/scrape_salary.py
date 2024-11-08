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

# Define column headers for the CSV output file
headers = ['Player', 'Player Link', 'player-name', 'Team', 'Team Link', 'Position', 'Age', '2024-25', '2025-26', '2026-27', 
           '2027-28', '2028-29', '2029-30', '2030-31']
    
# Helper function to clean player names for consistent formatting
def clean_player_name(name):
    # Normalize text to ASCII, remove special characters, convert to lowercase, and replace spaces with hyphens
    normalized_text = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    cleaned_name = re.sub(r'[^\w\s]', '', normalized_text).strip().lower().replace(' ', '-')
    return cleaned_name

# Function to extract and format team names from URLs
def clean_team_name(url):
    # Remove the base URL and any trailing slashes from the team URL to isolate the team name
    path = url.replace("https://www.spotrac.com/nba/", "").strip("/")
    team_name = path.split("/")[0]
    
    # Capitalize each part of the team name, handling "LA" and numeric parts specifically
    team_name_parts = team_name.split("-")
    formatted_name = " ".join(
        part.upper() if part.lower() == "la"  # Special formatting for "LA"
        else part.capitalize() if part.isalpha()  # Capitalize alphabetic parts
        else part  # Retain numeric parts as they are (e.g., "76ers")
        for part in team_name_parts
    )
    return formatted_name

# List to store collected data from all teams
all_data = []

# Loop through each team to scrape data from its salary page
for team in teams:
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    team_name = clean_team_name(url)
    
    # Fetch the webpage for the team's salary information
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the relevant table for salary data
        table = soup.select_one("table")  # Adjust selector to target the specific table if needed
        if table:
            rows = table.find_all("tr")
            
            # Iterate through each row in the table to extract player data
            for row in rows:
                cols = row.find_all("td")
                player_name = ""
                player_link = ""
                team_link = url
                position = ""
                age = ""
                salary_data = []

                # Extract player name and link from the first column, if available
                if len(cols) > 0:
                    player_name_tag = cols[0].find('a')
                    if player_name_tag:
                        player_name = player_name_tag.get_text(strip=True)
                        player_link = player_name_tag['href']
                    
                    # Clean the player name for consistent naming conventions
                    cleaned_player_name = clean_player_name(player_name)
                else:
                    player_name = cleaned_player_name = ""  # Ensure both are defined

                # Extract player position from the second column
                if len(cols) > 1:
                    position = cols[1].get_text(strip=True)

                # Extract player age from the third column, if available
                if len(cols) > 2:
                    age = cols[2].get_text(strip=True)
                
                # Extract salary data for each contract year from subsequent columns
                for col in cols[3:]:
                    cell_text = col.get_text(strip=True)
                    
                    # Check for specific salary statuses like "Two-Way," "UFA," or "RFA"
                    if "Two-Way" in cell_text:
                        salary_data.append("Two-Way")
                    elif "UFA" in cell_text:
                        salary_data.append("UFA")
                    elif "RFA" in cell_text:
                        salary_data.append("RFA")
                    else:
                        # Capture salary amounts formatted as dollar values
                        salary_matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', cell_text)
                        salary_data.extend(salary_matches)

                # Ensure the data has enough columns, filling with blanks as needed
                salary_data = [player_name, player_link, cleaned_player_name, team_name, team_link, position, age] + salary_data
                salary_data += [''] * (len(headers) - len(salary_data))  # Fill empty slots with blanks
                if salary_data[0]:  # Only add rows with a valid player name
                    all_data.append(salary_data)

        # Convert the collected data to a DataFrame
        df = pd.DataFrame(all_data, columns=headers)

        # Sort data alphabetically by player name for consistency
        df.sort_values(by=["player-name"], inplace=True)
        
        # Write the DataFrame to a CSV file
        df.to_csv("salary_data.csv", index=False, mode='w', encoding='utf-8', quoting=1)

    else:
        # Log failed requests for troubleshooting
        print(f"Failed to retrieve the page for {team}, status code: {response.status_code}")
