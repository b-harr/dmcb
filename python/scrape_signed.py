import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Load the player salary data from a CSV file and filter out inactive players and Two-Way contracts
salary_data = pd.read_csv("salary_data.csv")
active_data = salary_data[(salary_data["2024-25"] != "Two-Way") & (salary_data["2024-25"] != "-")]

# Extract unique player links and Player Keys, then sort by Player Key
unique_links = active_data.drop_duplicates(subset=["Player Link", "Player Key"]).sort_values(by="Player Key")["Player Link"].tolist()

# Set of words to keep lowercase in title-cased text, often minor connecting words
minor_words = {"and", "or", "the", "in", "at", "for", "to", "by", "with", "a", "an", "of", "on"}

# If input text is None, return None.
# Capitalizes specific prefixes and applies title case to the rest of the text.
def format_signed(text):
    if text is None:
        return None
    
    # Split the text to manage capitalization and hyphenation of each word individually
    words = re.split(r"[-\s]", text)
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
    formatted = re.sub(r"(?<=\w)(?=\b(?:Non|Mid|Bi)-)", "-", formatted)
    
    return formatted

# Scrapes the 'Signed Using' contract details from each player's page
# and formats the result for consistency.
def scrape_player_data(player_link, player_key):
    try:
        page = requests.get(player_link)
        soup = BeautifulSoup(page.content, "html.parser")

        signed_using_selector = "#contracts > div > div > div.contract-wrapper.mb-5 > div.contract-details.row.m-0 > div:nth-child(5) > div.label"
        signed_using_element = soup.select_one(signed_using_selector)
        
        signed_using_value = signed_using_element.find_next_sibling().get_text().strip() if signed_using_element else None

        formatted_value = format_signed(signed_using_value)

        return {
            "Player Link": player_link,
            "Player Key": player_key,  # Include Player Key in the returned dictionary
            "Signed Using": signed_using_value,
            "Formatted Signed Using": formatted_value
        }
    except Exception as e:
        return {
            "Player Link": player_link,
            "Player Key": player_key,
            "Signed Using": None,
            "Formatted Signed Using": None
        }

# Define the output file path
output_file = "signed_data.csv"
pd.DataFrame(columns=["Player Link", "Player Key", "Signed Using", "Formatted Signed Using"]).to_csv(output_file, index=False, mode="w", encoding="utf-8", quoting=1)

# Scrape and write data incrementally with a simple progress indicator
for idx, link in enumerate(unique_links):
    player_key = active_data[active_data["Player Link"] == link]["Player Key"].values[0]
    scraped_row = scrape_player_data(link, player_key)
    pd.DataFrame([scraped_row]).to_csv(output_file, mode="a", header=False, index=False, encoding="utf-8", quoting=1)
    print(f"Processed {idx + 1}/{len(unique_links)} players ({((idx + 1) / len(unique_links)) * 100:.2f}%): {player_key}")

print("Scraping and saving signed contract data completed.")
