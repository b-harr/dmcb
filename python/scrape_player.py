import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_player_data(link):
    """
    Scrapes 'Signed Using' and 'Free Agent' contract information from a player's Spotrac page.
    
    Parameters:
        link (str): URL of the player's page to scrape.
        
    Returns:
        dict: Contains 'player_link', 'signed_using', and 'free_agent' values extracted from the page.
    """
    try:
        # Send GET request to the provided link and parse HTML content
        page = requests.get(link)
        soup = BeautifulSoup(page.content, "html.parser")

        # CSS selector for locating the 'Signed Using' contract label and its associated value
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)
        # Extract the value following the 'Signed Using' label
        signed_using_value = signed_using_element.find_next_sibling().get_text().strip() if signed_using_element else None

        # CSS selector for locating the 'Free Agent' contract label and its associated value
        free_agent_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(6) > div.label"
        free_agent_element = soup.select_one(free_agent_selector)
        # Extract the value following the 'Free Agent' label
        free_agent_value = free_agent_element.find_next_sibling().get_text().strip() if free_agent_element else None

        # Return scraped data in a dictionary format
        return {
            "player_link": link,
            "signed_using": signed_using_value,
            "free_agent": free_agent_value
        }
    except Exception as e:
        # Return None values if an error occurs during scraping
        return {
            "player_link": link,
            "signed_using": None,
            "free_agent": None
        }

# Load the initial player data from a CSV file (local file used here)
spotrac_data = pd.read_csv("spotrac_data.csv")

# Extract and sort unique player links for scraping
unique_links = sorted(spotrac_data['player_link'].unique())

# Scrape data for each player link and collect results in a list of dictionaries
scraped_data = [scrape_player_data(link) for link in unique_links]

# Convert the scraped data into a DataFrame for easy merging
scraped_df = pd.DataFrame(scraped_data)

# Merge original player data with scraped contract data on 'player_link'
combined_data = pd.merge(spotrac_data, scraped_df, on="player_link", how="left")

# Save the merged DataFrame to a new CSV file
combined_data.to_csv("combined_data.csv", index=False, quoting=1)
