import os
import requests
from lxml import html
import pandas as pd
import re
import utils
import logging
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import datetime
import json

# Set up logging for tracking errors and steps in data processing
logging.basicConfig(
    level=logging.INFO,  # Log all INFO level messages and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Load environment variables
load_dotenv()

# Retrieve environment variables
creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
google_sheets_url = "https://docs.google.com/spreadsheets/d/1NgAl7GSl3jfehz4Sb3SmR_k1-QtQFm55fBPb3QOGYYw"
sheet_name = "Positions"

# Ensure Google Sheets credentials and URL are provided
if not creds_path or not google_sheets_url:
    raise ValueError("Google Sheets credentials or URL is not properly set.")

def main():
    # Log the start message with timestamp and timezone
    logger.info("The script started successfully.")
    
    # Load service account email
    try:
        with open(creds_path, 'r') as f:
            service_account_info = json.load(f)
            service_account_email = service_account_info.get("client_email", "Unknown Service Account")
    except Exception as e:
        logger.error(f"Error loading service account email: {e}")
        return

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
    logging.info("Splitting 'Tail' column into 'Team' and 'Position'.")
    df[['Team', 'Position']] = df['Tail'].str.extract(r',\s*([\w*]+),\s*(\w+)')
    
    # Drop the 'Tail' column if no longer needed
    df = df.drop(columns=['Tail'])
    
    # Filter rows where Name is blank
    logging.info("Filtering rows with blank or NaN 'Name'.")
    df = df[df["Name"].str.strip().ne(".")]  # Exclude blank/whitespace-only names
    df = df.dropna(subset=["Name"])  # Also drop rows where Name is NaN
    df = df.fillna("")
    
    # Display the filtered DataFrame
    logging.info("Final filtered data is ready.")

    # Sort the DataFrame by 'Player Key'
    logging.info("Sorting data by 'Player Key'.")
    df = df.sort_values(by="Player Key")
    
    # Save to a new CSV file
    output_dir = "python/data"
    output_file = "sportsws_pos_data.csv"
    os.makedirs(output_dir, exist_ok=True)  # Create directory if it doesn't exist
    output_csv = os.path.join(output_dir, output_file)
    
    df.to_csv(output_csv, index=False)
    logging.info(f"Data saved to {output_file}.")

    # Define API scope for Google Sheets to enable read/write operations
    scope = ["https://www.googleapis.com/auth/spreadsheets"]

    # Authenticate with Google Sheets API, clear the existing sheet, and write the updated data
    try:
        # Authenticate and access the spreadsheet
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(google_sheets_url)
        sheet = spreadsheet.worksheet(sheet_name)

        # Write the timestamp for automation
        sheet.clear()
        today = datetime.datetime.now().strftime("%-m/%-d/%Y %-I:%M %p")
        sheet.update([[f"Last updated {today} by {service_account_email}"]], "A1")

        # Write DataFrame to Google Sheets
        data_to_write = [df.columns.tolist()] + df.values.tolist()  # Include headers
        sheet.update(data_to_write, "A2")
        logger.info(f"Data successfully written to the '{sheet_name}' sheet.")
    except Exception as e:
        logger.error(f"Error updating Google Sheets: {e}")

if __name__ == "__main__":
    main()
