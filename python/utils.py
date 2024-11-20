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

# Function to extract and clean the team name from the Spotrac URL 
# e.g., "san-antonio-spurs" -> "San Antonio Spurs"
def clean_team_name(url):
    team_key = url.split("/")[-2]  # Extracts the team identifier from the URL
    team_key_parts = team_key.split("-")  # Splits the identifier into components
    # Capitalizes each word, with special handling
    cleaned_name = " ".join(
        part.upper() if part.lower() == "la"  # Capitalize "LA" specifically (e.g. "Los Angeles")
        else part.capitalize() if part.isalpha()  # Capitalize alphabetic parts only (e.g., "Hawks")
        else part  # Retain numeric parts as they are (e.g., "76ers")
        for part in team_key_parts
    )
    return cleaned_name
