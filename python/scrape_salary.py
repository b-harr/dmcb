import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import unicodedata

# List of teams
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

# Initialize the CSV header
headers = ['Player', 'Player Link', 'player-name', 'Team', 'Team Link', 'Position', 'Age', '2024-25', '2025-26', '2026-27', 
           '2027-28', '2028-29', '2029-30', '2030-31']
    
# Helper function to clean names
def clean_player_name(name):
    # Normalize to ASCII, replace hyphens with underscores, remove other punctuation, convert to lowercase, and replace spaces with underscores
    normalized_text = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    cleaned_name = re.sub(r'[^\w\s]', '', normalized_text).strip().lower().replace(' ', '-')
    return cleaned_name

def clean_team_name(url):
    # Remove the base URL and any trailing slashes from the team link
    path = url.replace("https://www.spotrac.com/nba/", "").strip("/")
    # Extract the team name segment from the path
    team_name = path.split("/")[0]
    
    # Split team name by hyphens to handle multi-part names, e.g., "san-antonio-spurs"
    team_name_parts = team_name.split("-")
    
    # Capitalize each part, with specific handling for "LA" and numeric parts like "76ers"
    formatted_name = " ".join(
        part.upper() if part.lower() == "la"  # Capitalize "LA" specifically
        else part.capitalize() if part.isalpha()  # Capitalize alphabetic parts only (e.g., "Bulls")
        else part  # Retain numeric parts as they are (e.g., "76ers")
        for part in team_name_parts
    )
    
    return formatted_name

# Initialize an empty list to store all the data
all_data = []

# Step 2: Iterate through each team
for team in teams:
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    team_name = clean_team_name(url)
    
    # Step 1: Fetch the page
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Step 2: Parse the page content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Step 3: Extract data
        data = []
        table = soup.select_one("table")  # Adjust selector to target the specific table
        if table:
            rows = table.find_all("tr")
            
            for row in rows:
                cols = row.find_all("td")
                player_name = ""
                player_link = ""
                team_link = url
                position = ""
                age = ""
                salary_data = []

                # Extract player name and link from the first column
                if len(cols) > 0:
                    player_name_tag = cols[0].find('a')
                    if player_name_tag:
                        player_name = player_name_tag.get_text(strip=True)
                        player_link = player_name_tag['href']
                    
                    # Clean the player name here
                    cleaned_player_name = clean_player_name(player_name)
                else:
                    player_name = cleaned_player_name = ""  # Ensure both are defined

                # Extract position from second column
                if len(cols) > 1:
                    position = cols[1].get_text(strip=True)

                # Extract age from third column (if available)
                if len(cols) > 2:
                    age = cols[2].get_text(strip=True)
                
                for col in cols[3:]:
                    cell_text = col.get_text(strip=True)
                    
                    # Check for keywords "Two-Way," "UFA," or "RFA"
                    if "Two-Way" in cell_text:
                        salary_data.append("Two-Way")
                    elif "UFA" in cell_text:
                        salary_data.append("UFA")
                    elif "RFA" in cell_text:
                        salary_data.append("RFA")
                    else:
                        # If no keywords are found, capture dollar amounts
                        salary_matches = re.findall(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', cell_text)
                        salary_data.extend(salary_matches)

                # Ensure the length of salary data matches the number of columns expected
                salary_data = [player_name, player_link, cleaned_player_name, team_name, team_link, position, age] + salary_data
                salary_data += [''] * (len(headers) - len(salary_data))  # Fill empty slots with ''
                if salary_data[0]:  # Only add rows where the player name exists
                    all_data.append(salary_data)

        # Convert to DataFrame
        df = pd.DataFrame(all_data, columns=headers)

        # Sort data by player and season
        df.sort_values(by=["player-name"], inplace=True)
        
        # Write to CSV file
        df.to_csv("salary_data.csv", index=False, mode='w', encoding='utf-8', quoting=1)

    else:
        print(f"Failed to retrieve the page for {team}, status code: {response.status_code}")
