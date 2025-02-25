import pandas as pd
import requests
from lxml import html

def scrape_sportsws_positions():
    # Define the URL
    url = "https://sports.ws/nba/stats"
    
    # Send a GET request to the URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    
    # Parse the HTML using lxml
    tree = html.fromstring(response.content)
    
    # Use XPath to extract player names and links
    players = tree.xpath("//td[1]//a")
    
    # Extract data into a list of dictionaries
    player_data = []
    for player in players:
        name = player.text.strip() if player.text else ""
        link = "https://sports.ws" + player.get('href')
        tail = player.tail.strip() if player.tail else ""
        
        player_data.append({"Name": name, "Player Link": link, "Tail": tail})
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(player_data)
    
    # Split the 'Tail' column into 'Team' and 'Pos' columns
    df[['Team', 'Position']] = df['Tail'].str.extract(r',\s*([\w*]+),\s*(\w+)')
    
    # Drop the 'Tail' column if no longer needed
    df = df.drop(columns=['Tail'])
    
    # Filter rows where Name is blank
    df = df[df["Name"].str.strip().ne(".")]  # Exclude blank/whitespace-only names
    df = df.dropna(subset=["Name"])  # Also drop rows where Name is NaN
    df = df.fillna("")

    # Sort the DataFrame by 'Player Link'
    return df.sort_values(by="Player Link")

if __name__ == "__main__":
    df = scrape_sportsws_positions()
    print(df)
