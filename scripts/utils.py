import unicodedata
import re

# Clean a player's name and generate a unique key for consistent cross-site merging
def make_player_key(name):
    normalized_name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_name.lower().strip()  # Convert to lowercase and trim spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

# Capitalizes specific prefixes and applies title case to the rest of the text
def format_text(text):
    # List of minor words that should not be capitalized unless they are at the beginning or end
    minor_words = {"and", "or", "the", "in", "at", "for", "to", "by", "with", "a", "an", "of", "on"}
    exception_words = {"non", "mid", "bi"}
    
    # If the text is None, return None
    if text is None:
        return None

    # Split the text into words by spaces or hyphens
    words = re.split(r"[-\s]", text)
    
    # Initialize a list for formatted words
    formatted_words = []
    i = 0
    
    while i < len(words):
        word = words[i].lower()
        
        # Handle 'LA' specifically
        if word == "la":
            formatted_words.append("LA")
        # Handle exception words with hyphenation
        elif word in exception_words and i < len(words) - 1:
            formatted_words.append(f"{word.capitalize()}-{words[i + 1].capitalize()}")
            i += 1  # Skip the next word as it's already processed
        # Handle minor words
        elif word in minor_words:
            formatted_words.append(word if i != 0 and i != len(words) - 1 else word.capitalize())
        # Capitalize alphabetic words; retain numbers
        else:
            formatted_words.append(word.capitalize() if word.isalpha() else word)
        
        i += 1

    # Join the formatted words with spaces
    formatted_words = " ".join(formatted_words)
    # Special case: Replace "Sign and Trade" with "Sign-and-Trade"
    formatted_words = re.sub("Sign and Trade", "Sign-and-Trade", formatted_words)
    return formatted_words

import requests
from bs4 import BeautifulSoup
from time import sleep
import random
import logging
import pandas as pd
logger = logging.getLogger()

def fetch_data(url, headers, retries=3, delay=2):
    for i in range(retries):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed attempt {i + 1}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Attempt {i + 1} failed: {e}")
        sleep(delay + random.uniform(0, 1))
    raise Exception("Max retries reached. Unable to fetch data.")

def parse_html(html_content, config):
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", {"id": "totals_stats"})
    if not table:
        raise ValueError("Table not found. Ensure the page structure has not changed.")
    
    headers = [th.get_text() for th in table.find("thead").find_all("th")][1:]
    rows = table.find("tbody").find_all("tr")
    
    data = []
    for row in rows:
        if row.find("td"):
            row_data = [td.get_text() for td in row.find_all("td")]
            data.append(row_data)
    
    return pd.DataFrame(data, columns=headers)

import pandas as pd

def process_data(df, numeric_columns):
    df = df[df["Player"] != "League Average"].dropna(subset=["Player"])
    df["Player Key"] = df["Player"].apply(make_player_key)
    df = df.sort_values(by=["Player Key", "Team"])
    df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    
    df["FP"] = (df["PTS"] + df["TRB"] + df["AST"] + df["STL"] + df["BLK"] - df["TOV"] - df["PF"]).astype(int)
    df["FPPG"] = (df["FP"] / df["G"]).round(1)
    df["FPPM"] = (df["FP"] / df["MP"]).round(2)
    df["MPG"] = (df["MP"] / df["G"]).round(1)
    df["FPR"] = ((df["FP"] ** 2) / (df["G"] * df["MP"])).round(1)
    
    return df

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import logging

logger = logging.getLogger()

def update_google_sheet(df, config):
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(config["creds_path"], scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(config["google_sheets_url"])
    sheet = spreadsheet.worksheet(config["sheet_name"])
    
    sheet.clear()
    today = datetime.datetime.now().strftime("%-m/%-d/%Y %-I:%M %p")
    service_account_email = creds.service_account_email
    
    sheet.update([[f"Last updated {today} by {service_account_email}"]], "A1")
    data_to_write = [df.columns.tolist()] + df.values.tolist()
    sheet.update(data_to_write, "A2")
