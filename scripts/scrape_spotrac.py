import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Function to scrape contract data for a single team from Spotrac
def scrape_team_contracts(team):
    # Construct the team's URL for Spotrac based on the team name
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    
    # Send a GET request to fetch the web page content
    response = requests.get(url)
    
    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        print(f"Failed to fetch data for {team} (Status code: {response.status_code})")
        return None
    
    # Parse the HTML content of the page using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Locate the contracts table in the HTML content
    table = soup.find("table", {"id": "table"})
    if table is None:
        print(f"No contracts table found for {team}")
        return None
    
    # Extract column headers (e.g., player names, salary years) from the table
    headers = [th.text.strip() for th in table.find_all("th")]
    
    # Identify headers corresponding to contract years (e.g., '2024', '2025', etc.)
    season_headers = [h for h in headers if h.startswith("20")]  # Filter for headers starting with "20"
    season_headers = season_headers[:5]  # Limit to the first 5 years of salary data (for 5 seasons)
    
    # Initialize an empty list to store player contract data
    data = []
    
    # Iterate through each row in the table's body (tbody) to extract player information
    for row in table.find("tbody").find_all("tr"):
        # Get all the cells (columns) for the current row
        cells = row.find_all("td")
        
        # Skip rows that don't contain enough data (likely non-player rows)
        if len(cells) < 2:
            continue
        
        # Extract the player's name and the link to their profile (if available)
        player_tag = row.find("a")
        player_name = player_tag.text.strip() if player_tag else "Unknown"
        player_link = player_tag["href"] if player_tag else None
        
        # Extract the player's position and age from the respective columns
        position = cells[1].text.strip()
        age = cells[2].text.strip()
        
        # Extract contract values (salaries, UFA, RFA, etc.) from the remaining columns
        contract_values = []
        for col in cells[3:]:
            cell_text = col.get_text(strip=True)
            
            # Check for special cases such as "Two-Way", "UFA", or "RFA" in the cell text
            if "Two-Way" in cell_text:
                contract_values.append("Two-Way")
            elif "UFA" in cell_text:
                contract_values.append("UFA")
            elif "RFA" in cell_text:
                contract_values.append("RFA")
            else:
                # Use regex to find salary values in the format "$1,000,000" or "$1M"
                salary_matches = re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?", cell_text)
                contract_values.extend([s.replace(",", "") for s in salary_matches])
        
        # Limit the contract values to the first 5 seasons (to match season headers)
        contract_values = contract_values[:5]
        
        # If there are fewer contract values than the number of seasons, pad with None
        while len(contract_values) < len(season_headers):
            contract_values.append(None)
        
        # Add the extracted data (player name, link, position, age, contract data) to the list
        data.append([player_name, player_link, position, age] + contract_values)
    
    # Define the column names for the DataFrame
    columns = ["Player", "Player Link", "Position", "Age"] + season_headers
    
    # Convert the collected data into a pandas DataFrame and return it
    return pd.DataFrame(data, columns=columns)

# Function to scrape contract data for all teams in the 'teams' list
def scrape_all_teams():
    # List of NBA teams to scrape contract data for (Spotrac-friendly URL format)
    teams = [
        "atlanta-hawks", "boston-celtics", "brooklyn-nets", "charlotte-hornets",
        "chicago-bulls", "cleveland-cavaliers", "dallas-mavericks", "denver-nuggets",
        "detroit-pistons", "golden-state-warriors", "houston-rockets", "indiana-pacers",
        "la-clippers", "los-angeles-lakers", "memphis-grizzlies", "miami-heat",
        "milwaukee-bucks", "minnesota-timberwolves", "new-orleans-pelicans",
        "new-york-knicks", "oklahoma-city-thunder", "orlando-magic", "philadelphia-76ers",
        "phoenix-suns", "portland-trail-blazers", "sacramento-kings", "san-antonio-spurs",
        "toronto-raptors", "utah-jazz", "washington-wizards"
    ]

    all_data = []  # List to store DataFrames for each team's contract data
    for team in teams:
        print(f"Scraping data for {team}...")
        team_data = scrape_team_contracts(team)  # Scrape contract data for the current team
        
        # If the team data was successfully retrieved, process and add it to the list
        if team_data is not None:
            team_data["Team"] = team  # Add a column for the team name
            all_data.append(team_data)
    
    # Combine all team DataFrames into one large DataFrame (if any data was successfully scraped)
    combined_data = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    return combined_data

# Main execution block
if __name__ == "__main__":   
    # Scrape contract data for all teams and store the result in a DataFrame
    contracts_df = scrape_all_teams()
    print(contracts_df.head())  # Print the first few rows of the DataFrame for verification
    
    # Save the combined contract data to a CSV file for future use
    #contracts_df.to_csv("data/contracts.csv", mode="w", index=False, encoding="utf-8")
    #print("Data saved to data/contracts.csv")  # Confirm that the data was saved
