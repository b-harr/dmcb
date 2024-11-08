import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Load the player salary data from a CSV file and filter out inactive players and Two-Way contracts
salary_data = pd.read_csv("salary_data.csv")
active_data = salary_data[(salary_data['2024-25'] != "Two-Way") & (salary_data['2024-25'] != "-")]

# Extract unique player links from filtered data to avoid redundant scraping
unique_links = sorted(active_data['Player Link'].unique())

# Define a function to scrape contract details from each player's page
def scrape_player_data(player_link):
    try:
        # Send GET request to retrieve the player's page HTML content
        page = requests.get(player_link)
        soup = BeautifulSoup(page.content, "html.parser")

        # CSS selector for identifying the 'Signed Using' field in contract details
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)
        
        # Extract the contract type text following the 'Signed Using' label, if available
        signed_using_value = signed_using_element.find_next_sibling().get_text().strip() if signed_using_element else None

        # Return the scraped contract type and player link as a dictionary
        return {
            "player_link": player_link,
            "signed_using": signed_using_value
        }
    except Exception as e:
        # Handle exceptions by returning None for 'signed_using' if an error occurs
        return {
            "player_link": player_link,
            "signed_using": None
        }

# Apply the scraping function to each unique player link and store the results in a list of dictionaries
scraped_data = [scrape_player_data(link) for link in unique_links]

# Convert the list of dictionaries into a DataFrame for easier merging and further processing
signed_data = pd.DataFrame(scraped_data)

# Set of words to keep lowercase in title-cased text, often minor connecting words
minor_words = {"and", "or", "the", "in", "at", "for", "to", "by", "with", "a", "an", "of", "on"}

def format_signed(text):
    # Return None if the input text is None
    if text is None:
        return None
    
    # Split the text to manage capitalization and hyphenation of each word individually
    words = re.split(r'[-\s]', text)
    formatted_words = []
    
    for i, word in enumerate(words):
        # Capitalize words with prefixes "Non-", "Mid-", or "Bi-" and retain the hyphen
        if any(word.lower().startswith(prefix) for prefix in ("non", "mid", "bi")):
            formatted_words.append(word.capitalize())
        else:
            # Title-case the word unless it is in the minor_words set
            formatted_words.append(word if word.lower() in minor_words else word.capitalize())
    
    # Reassemble words with spaces; preserve hyphens only for specific prefixes
    formatted = " ".join(formatted_words)
    formatted = re.sub(r'(?<=\w)(?=\b(?:Non|Mid|Bi)-)', "-", formatted)
    
    return formatted

# Apply the formatting function to the 'signed_using' column in the DataFrame
signed_data['signed_using'] = signed_data['signed_using'].apply(format_signed)

# Rename columns for clarity and consistency
signed_data.rename(columns={"player_link": "Player Link", "signed_using": "Signed Using"}, inplace=True)

# Save the formatted and merged data to a new CSV file, with quoting to handle special characters
signed_data.to_csv("signed_data.csv", index=False, quoting=1)
