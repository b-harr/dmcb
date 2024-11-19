import requests
import re
import pandas as pd
from bs4 import BeautifulSoup

# Input CSV file containing the salary data
input_csv = "salary_data.csv"
# Read the salary data from the input file into a pandas DataFrame
salary_data = pd.read_csv(input_csv)

# Filter out inactive players or those with "Two-Way" contracts
active_data = salary_data[(salary_data["2024-25"] != "Two-Way") & (salary_data["2024-25"] != "-")]

# Extract unique player links and keys, and sort by player key for consistency
unique_links = active_data.drop_duplicates(subset=["Player Link", "Player Key"]).sort_values(by="Player Key")["Player Link"].tolist()

# List of minor words that should not be capitalized unless they are at the beginning of a phrase
minor_words = {"and", "or", "the", "in", "at", "for", "to", "by", "with", "a", "an", "of", "on"}

# Capitalizes specific prefixes and applies title case to the rest of the text
def format_signed(text):
    # If the text is None, return None
    if text is None:
        return None

    # Split the text into words by spaces or hyphens
    words = re.split(r"[-\s]", text)
    formatted_words = []
    
    # Capitalize words based on specific conditions
    for i, word in enumerate(words):
        # If the word starts with "non", "mid", or "bi", capitalize it (e.g., "Non-" becomes "Non")
        if any(word.lower().startswith(prefix) for prefix in ("non", "mid", "bi")):
            formatted_words.append(word.capitalize())
        # Capitalize all other words unless they are minor words
        else:
            formatted_words.append(word if word.lower() in minor_words else word.capitalize())
    
    # Join the formatted words into a single string
    formatted = " ".join(formatted_words)
    
    # Replace the capitalization for "Non-", "Mid-", "Bi-" if needed
    formatted = re.sub(r"(?<=\w)(?=\b(?:Non|Mid|Bi)-)", "-", formatted)
    
    # Remove space after "Non ", "Mid ", "Bi " and replace it with a hyphen
    formatted = re.sub(r"(Non|Mid|Bi)\s", r"\1-", formatted)
    
    # Special case: Handle "Sign and Trade" as a unique exception
    formatted = re.sub(r"Sign and Trade", "Sign-and-Trade", formatted)

    return formatted

# Function to scrape player data from the player's individual page
def scrape_player_data(player_link, player_key, player_name):
    try:
        # Send a GET request to the player's page
        page = requests.get(player_link)
        soup = BeautifulSoup(page.content, "html.parser")  # Parse the HTML content of the page

        # CSS selector to find the "Signed Using" contract information
        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        # Find the corresponding HTML element using the selector
        signed_using_element = soup.select_one(signed_using_selector)
        
        # Get the text of the next sibling element containing the actual contract information
        signed_using_value = signed_using_element.find_next_sibling().get_text().strip() if signed_using_element else None

        # Format the extracted contract data using the format_signed function
        cleaned_value = format_signed(signed_using_value)

        # Return a dictionary containing the player data with the cleaned "Signed Using" value
        return {
            "Player": player_name,
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": cleaned_value
        }
    except Exception as e:
        # If an error occurs (e.g., page structure changes), return None for contract data
        return {
            "Player": player_name,
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": None
        }

# Output file where the scraped data will be saved
output_csv = "python/data/signed_data.csv"
# Initialize the output CSV file with headers
pd.DataFrame(columns=["Player", "Player Link", "Player Key", "Signed Using"]).to_csv(output_csv, index=False, mode="w", encoding="utf-8", quoting=1)

# Loop through each unique player link and scrape the data
for idx, link in enumerate(unique_links):
    # Extract player key and player name from the active data DataFrame
    player_key = active_data[active_data["Player Link"] == link]["Player Key"].values[0]
    player_name = active_data[active_data["Player Link"] == link]["Player"].values[0]
    
    # Scrape the player's contract data using the scrape_player_data function
    scraped_row = scrape_player_data(link, player_key, player_name)
    # Append the scraped data to the output CSV file, replacing the "Signed Using" column with the cleaned data
    pd.DataFrame([scraped_row]).to_csv(output_csv, mode="a", header=False, index=False, encoding="utf-8", quoting=1)
    
    # Print progress as players are processed
    print(f"Processed {idx + 1}/{len(unique_links)} players ({((idx + 1) / len(unique_links)) * 100:.2f}%): {player_name}")

# Get the current datetime in the local timezone
import pytz
import datetime
timezone = pytz.timezone("America/Chicago")  # Replace with your local timezone
current_time = datetime.datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z%z")

# Print the completion message with timestamp and timezone
print(f"Data saved to {output_csv} at {current_time}")
