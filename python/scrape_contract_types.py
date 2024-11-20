import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
import utils
import logging

# Set up logging for tracking errors and steps in data processing
logging.basicConfig(
    level=logging.INFO,  # Log all INFO level messages and above
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Function to scrape player data from the player's individual page
def scrape_player_data(player_link, player_key, player_name):
    try:
        # Send a GET request to the player's page and parse the HTML content
        page = requests.get(player_link)
        soup = BeautifulSoup(page.content, "html.parser")

        # CSS selector to find the "Signed Using" contract information
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)

        # Extract contract info
        signed_using_value = (
            signed_using_element.find_next_sibling().get_text().strip()
            if signed_using_element else None
        )

        # Format and clean the extracted contract data
        cleaned_value = utils.format_text(signed_using_value)

        return {
            "Player": player_name,
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": cleaned_value,
        }

    except Exception as e:
        # Log errors and return None for contract data if scraping fails
        logger.error(f"Error scraping data for player {player_name} ({player_key}): {e}")
        return {
            "Player": player_name,
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": None,
        }

def main():
    # Define paths and filenames
    input_dir = "python/data"
    input_file = "spotrac_salary.csv"
    input_csv = os.path.join(input_dir, input_file)

    output_dir = "python/data"
    output_file = "contract_types.csv"
    output_csv = os.path.join(output_dir, output_file)

    logger.info(f"Starting script to scrape player data from {input_csv}")

    try:
        # Load salary data from CSV
        salary_data = pd.read_csv(input_csv)
        logger.info(f"Successfully loaded salary data from {input_csv}")
    except Exception as e:
        logger.error(f"Failed to load salary data: {e}")
        exit()

    # Filter out inactive players or those with "Two-Way" contracts
    active_data = salary_data[(salary_data["2024-25"] != "Two-Way") & (salary_data["2024-25"] != "-")]

    # Extract unique player links and sort by player key
    unique_links = active_data.drop_duplicates(subset=["Player Link", "Player Key"]).sort_values(by="Player Key")["Player Link"].tolist()
    logger.info(f"Found {len(unique_links)} unique player links to scrape")

    # Initialize the output CSV with headers
    pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using"]).to_csv(output_csv, index=False, mode="w", encoding="utf-8")
    logger.info(f"Initialized new output CSV file: {output_csv}")

    # Loop through each unique player link and scrape the data
    for idx, link in enumerate(unique_links):
        player_key = active_data[active_data["Player Link"] == link]["Player Key"].values[0]
        player_name = active_data[active_data["Player Link"] == link]["Player"].values[0]

        # Scrape player's contract data
        scraped_row = scrape_player_data(link, player_key, player_name)

        # Append the scraped data to the output CSV file
        pd.DataFrame([scraped_row]).to_csv(output_csv, mode="a", header=False, index=False, encoding="utf-8")

        # Log progress
        logger.info(f"Processed {idx + 1}/{len(unique_links)} players ({((idx + 1) / len(unique_links)) * 100:.2f}%) - {player_name}")

    logger.info(f"Data saved to file: {output_csv}")

if __name__ == "__main__":
    main()
