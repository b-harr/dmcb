import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import logging

# Set up logging for the script
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to scrape contract data for a single team from Spotrac
def scrape_team_contracts(team):
    # Construct the team's URL for Spotrac based on the team name
    url = f"https://www.spotrac.com/nba/{team}/yearly"
    
    # Send a GET request to fetch the web page content
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)

    
    # Check if the request was successful (status code 200)
    if response.status_code != 200:
        logging.error(f"Failed to fetch data for {team} (Status code: {response.status_code})")
        return None
    
    # Parse the HTML content of the page using BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Helper function to extract table data
    def extract_table(table, season_headers):
        data = []
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
        
        return data

    # Find both tables
    tables = []
    for table_id in ["dataTable-active", "dataTable-pending"]:
        table = soup.find("table", {"id": table_id})
        if table is not None:
            tables.append(table)

    if not tables:
        logging.warning(f"No contracts tables found for {team}")
        return None

    # Use headers from the first table found
    headers = [th.text.strip() for th in tables[0].find_all("th")]
    season_headers = [h for h in headers if h.startswith("20")]
    season_headers = season_headers[:5]

    # Extract data from all tables and combine
    all_data = []
    for table in tables:
        all_data.extend(extract_table(table, season_headers))

    columns = ["Player", "Player Link", "Position", "Age"] + season_headers
    return pd.DataFrame(all_data, columns=columns)

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
        logging.info(f"Scraping data for {team}...")
        team_data = scrape_team_contracts(team)  # Scrape contract data for the current team
        
        # If the team data was successfully retrieved, process and add it to the list
        if team_data is not None:
            team_data["Team"] = team  # Add a column for the team name
            all_data.append(team_data)
    
    # Combine all team DataFrames into one large DataFrame (if any data was successfully scraped)
    combined_data = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    return combined_data

# Function to scrape player data from the player's individual page
def scrape_player_contracts(url):
    # Send a GET request to fetch the web page content
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }

    try:
        # Send a GET request to the player's page and parse the HTML content
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")

        # CSS selector to find the "Signed Using" contract information
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)

        # Extract contract info
        signed_using_value = (
            signed_using_element.find_next_sibling().get_text().strip()
            if signed_using_element else None
        )

        # CSS selector to find the "Drafted" information
        drafted_selector = "#main > section > article > div.row.m-0.mt-0.pb-3 > div.col-md-6 > div > div:nth-child(1) > span"
        drafted_element = soup.select_one(drafted_selector)

        drafted_value = (
            drafted_element.get_text().strip()
            if drafted_element else None
        )

        return signed_using_value, drafted_value

    except Exception as e:
        return None, None

# Example usage
if __name__ == "__main__":
    # Scrape contract data for all teams and store the result in a DataFrame
    #contracts_df = scrape_all_teams()
    # Display the first few rows of the combined DataFrame
    #print(contracts_df.head())
    
    # Scrape contract data for a specific player (example)
    player_df = scrape_player_contracts("https://www.spotrac.com/nba/player/_/id/15356")
    # Display the scraped contract information for the player
    print(player_df)
