import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_nba_totals(year):
    url = f"https://www.basketball-reference.com/leagues/NBA_{year}_totals.html"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0 Safari/537.36"
        )
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # raises HTTPError if 403/404/etc.

    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.find("table", {"id": "totals_stats"})
    
    if not table:
        raise ValueError("Table not found. Ensure the page structure has not changed.")
    
    headers = [th.get_text() for th in table.find("thead").find_all("th")][1:]
    
    # Add extra columns for the player and team links
    headers.extend(["Player Link", "Team Link"])
    
    rows = table.find("tbody").find_all("tr")
    
    # Initialize an empty list to store the data
    data = []

    for row in rows:
        if row.find("td"):  # Skip rows that do not contain data
            row_data = [td.get_text() for td in row.find_all("td")]  # Get text from each 'td' element
            
            # Find all anchor ('a') tags in the row
            links = row.find_all("a")
            player_link, team_link = None, None
            
            # Loop through all the links and check if they correspond to a player or a team
            for link in links:
                href = link.get("href", "")
                
                # Check if the link is a player link (contains '/players/')
                if "/players/" in href:
                    player_link = "https://www.basketball-reference.com" + href
                    
                # Check if the link is a team link (contains '/teams/')
                elif "/teams/" in href:
                    team_link = "https://www.basketball-reference.com" + href
            
            # Add the player and team links to the row data
            row_data.append(player_link)
            row_data.append(team_link)
            
            # Append the row's data to the list
            data.append(row_data)
    
    # After processing all rows, create the DataFrame with the adjusted headers
    return pd.DataFrame(data, columns=headers)

if __name__ == "__main__":
    stats = scrape_nba_totals(year=2025)
    print(stats.head())
