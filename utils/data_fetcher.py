import requests
from bs4 import BeautifulSoup
from time import sleep
import random
import logging
import pandas as pd

logger = logging.getLogger()

def fetch_data(url, headers, retries=3, delay=2):
    """
    Fetch data from the given URL with retry logic.

    Args:
        url (str): The URL to fetch data from.
        headers (dict): HTTP headers to include in the request.
        retries (int): Number of retry attempts if the request fails.
        delay (int): Delay between retry attempts in seconds.

    Returns:
        str: The content of the response if successful.
    """
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed attempt {i + 1}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
        sleep(delay + random.uniform(0, 1))  # Add a slight random delay to avoid rate limiting
    raise Exception("Max retries reached. Unable to fetch data.")

def parse_html(html_content):
    """
    Parse the HTML content and extract player stats into a pandas DataFrame.

    Args:
        html_content (str): The raw HTML content to parse.

    Returns:
        pd.DataFrame: A DataFrame containing the player stats data.
    """
    soup = BeautifulSoup(html_content, "html.parser")
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
            
            player_link = None
            team_link = None
            
            # Loop through all the links and check if they correspond to a player or a team
            for link in links:
                href = link.get("href")
                
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

# Now 'data' will contain the player stats along with their corresponding links.

# Main block for testing
if __name__ == "__main__":
    # Test fetch_data function
    print("Testing fetch_data function...")

    # Sample URL and headers for testing
    test_url = "https://www.basketball-reference.com/leagues/NBA_2025_totals.html"
    test_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Test fetching data from the URL (will actually make a network request)
    try:
        html_content = fetch_data(test_url, test_headers)
        print("fetch_data test passed!")
    except Exception as e:
        print(f"fetch_data test failed: {e}")

    # Test parse_html function (using mock HTML content from the previous request)
    print("\nTesting parse_html function...")
    try:
        df = parse_html(html_content)
        print("parse_html test passed!")
        print(df.head())  # Print the first few rows of the DataFrame
    except Exception as e:
        print(f"parse_html test failed: {e}")
