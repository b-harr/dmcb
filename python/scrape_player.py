import requests
from bs4 import BeautifulSoup
import pandas as pd
#import time

def scrape_player_data(link):
    """
    Scrapes 'Signed Using' and 'Free Agent' values for a given player link.
    
    Parameters:
        link (str): The URL of the player's page to scrape.
        
    Returns:
        dict: A dictionary containing the player link, signed_using, and free_agent values.
    """
    try:
        # Fetch the page content
        page = requests.get(link)
        soup = BeautifulSoup(page.content, "html.parser")

        # Use CSS selectors to locate "Signed Using" and "Free Agent" values
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)
        signed_using_value = signed_using_element.find_next_sibling().get_text(strip=True) if signed_using_element else None

        free_agent_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(6) > div.label"
        free_agent_element = soup.select_one(free_agent_selector)
        free_agent_value = free_agent_element.find_next_sibling().get_text(strip=True) if free_agent_element else None

        # Return data in dictionary format
        return {
            "player_link": link,
            "signed_using": signed_using_value,
            "free_agent": free_agent_value
        }
    except Exception as e:
        #print(f"Error processing {link}: {e}")
        return {
            "player_link": link,
            "signed_using": None,
            "free_agent": None
        }

# Read data from the given CSV URL
#spotrac_data = pd.read_csv("https://raw.githubusercontent.com/b-harr/dmcb/refs/heads/main/python/spotrac_data.csv")
# Use the local file path instead of URL
spotrac_data = pd.read_csv("~/dmcb/python/spotrac_data.csv")

# Create a list of unique player_link values and sort it
unique_links = sorted(spotrac_data['player_link'].unique())
# Uncomment and edit the following line to test with a specific number of links
#unique_links = unique_links[:5]  # Example: using only the first 5 links for testing

# Loop through links and collect scraped data
scraped_data = [scrape_player_data(link) for link in unique_links]
# Loop through links with a delay
#scraped_data = []
#for link in unique_links:
#    scraped_data.append(scrape_player_data(link))
#    time.sleep(1)  # Adds a 1-second pause between requests

# Convert the scraped data into a DataFrame
scraped_df = pd.DataFrame(scraped_data)

# Merge the original spotrac_data with the new scraped data
combined_data = pd.merge(spotrac_data, scraped_df, on="player_link", how="left")

# Save the combined data to a new CSV
combined_data.to_csv("combined_data.csv", index=False, quoting=1)
