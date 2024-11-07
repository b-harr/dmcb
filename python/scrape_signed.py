import requests
from bs4 import BeautifulSoup
import pandas as pd

# Load the initial player data from a CSV file (local file used here)
salary_data = pd.read_csv("salary_data.csv")
active_data = salary_data[(salary_data['2024-25'] != "Two-Way") & (salary_data['2024-25'] != "-")]

# Sort data by player and season
#active_data.sort_values(by=["player-name"], inplace=True)

# Extract and sort unique player links for scraping
unique_links = sorted(active_data['Player Link'].unique())

def scrape_player_data(player_link):
    try:
        # Send GET request to the provided link and parse HTML content
        page = requests.get(player_link)
        soup = BeautifulSoup(page.content, "html.parser")

        # CSS selector for locating the 'Signed Using' contract label and its associated value
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)
        # Extract the value following the 'Signed Using' label
        signed_using_value = signed_using_element.find_next_sibling().get_text().strip() if signed_using_element else None

        # Return scraped data in a dictionary format
        return {
            "player_link": player_link,
            "signed_using": signed_using_value
        }
    except Exception as e:
        # Return None values if an error occurs during scraping
        return {
            "player_link": player_link,
            "signed_using": None
        }

# Scrape data for each player link and collect results in a list of dictionaries
scraped_data = [scrape_player_data(link) for link in unique_links]

# Convert the scraped data into a DataFrame for easy merging
signed_data = pd.DataFrame(scraped_data)

# Save the merged DataFrame to a new CSV file
signed_data.to_csv("signed_data.csv", index=False, quoting=1)
