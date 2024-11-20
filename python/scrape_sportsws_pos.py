import os
import requests
from lxml import html
import pandas as pd
import re
import utils
import logging

# Set up logging for tracking errors and steps in data processing
logging.basicConfig(
    level=logging.INFO,  # Log all INFO level messages and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

def main():
    # Log the start message with timestamp and timezone
    logger.info("The script started successfully.")
    
    # Define the URL
    url = "https://sports.ws/nba/stats"
    
    # Send a GET request to the URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        logging.info(f"Fetching data from {url}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return
    
    # Parse the HTML using lxml
    logging.info("Parsing HTML content.")
    tree = html.fromstring(response.content)
    
    # Use XPath to extract player names and links
    players = tree.xpath("//td[1]//a")
    logging.info(f"Found {len(players)} players in the data.")
    
    # Extract data into a list of dictionaries
    player_data = []
    for player in players:
        name = player.text.strip() if player.text else ""
        link = "https://sports.ws" + player.get('href')
        key = re.sub("https://sports.ws/nba/", "", link)
        key = utils.make_player_key(key)
        tail = player.tail.strip() if player.tail else ""
        
        player_data.append({"Name": name, "Player Link": link, "Player Key": key, "Tail": tail})
    
    logging.info(f"Extracted data for {len(player_data)} players.")
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(player_data)
    
    # Split the 'Tail' column into 'Team' and 'Pos' columns
    logging.info("Splitting 'Tail' column into 'Team' and 'Pos'.")
    df[['Team', 'Pos']] = df['Tail'].str.extract(r',\s*(\w+),\s*(\w+)')
    
    # Drop the 'Tail' column if no longer needed
    df = df.drop(columns=['Tail'])
    
    # Filter rows where Name is blank
    logging.info("Filtering rows with blank or NaN 'Name'.")
    filtered_df = df[df["Name"].str.strip().ne(".")]  # Exclude blank/whitespace-only names
    filtered_df = filtered_df.dropna(subset=["Name"])  # Also drop rows where Name is NaN
    
    # Display the filtered DataFrame
    logging.info("Final filtered data is ready.")

    # Sort the DataFrame by 'Player Key'
    logging.info("Sorting data by 'Player Key'.")
    filtered_df = filtered_df.sort_values(by="Player Key")
    
    # Save to a new CSV file
    output_dir = "python/data"
    output_file = "sportsws_pos_data.csv"
    os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist
    output_csv = os.path.join(output_dir, output_file)
    
    filtered_df.to_csv(output_csv, index=False)
    logging.info(f"Filtered data saved to {output_file}.")

if __name__ == "__main__":
    main()
