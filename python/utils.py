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
    formatted_text = " ".join(formatted_words)
    # Replace the capitalization for "Non-", "Mid-", "Bi-" if needed
    formatted_text = re.sub(r"(?<=\w)(?=\b(?:Non|Mid|Bi)-)", "-", formatted_text)
    # Remove space after "Non ", "Mid ", "Bi " and replace it with a hyphen
    formatted_text = re.sub(r"(Non|Mid|Bi)\s", r"\1-", formatted_text)
    # Special case: Handle "Sign and Trade" as a unique exception
    formatted_text = re.sub(r"Sign and Trade", "Sign-and-Trade", formatted_text)

    return formatted_text
