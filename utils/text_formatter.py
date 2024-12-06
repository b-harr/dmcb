import unicodedata
import re

def make_player_key(name):
    """
    Cleans a player's name and generates a unique key for consistent cross-site merging.

    Args:
        name (str): The player's full name.

    Returns:
        str: A normalized, cleaned key for the player's name without suffixes.
    """
    normalized_name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")  # Remove accents
    cleaned_name = normalized_name.lower().strip()  # Convert to lowercase and trim spaces
    cleaned_name = re.sub(r"\s+", "-", cleaned_name)  # Replace spaces with hyphens
    cleaned_name = re.sub(r"[^\w-]", "", cleaned_name)  # Remove non-alphanumeric characters
    player_key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", cleaned_name)  # Remove common suffixes
    return player_key

def make_title_case(text):
    """
    Capitalizes specific prefixes and applies title case to the rest of the text.

    Args:
        text (str): The input text to format.

    Returns:
        str or None: The formatted text, or None if the input is None.
    """
    # List of minor words that should not be capitalized unless they are at the beginning or end
    minor_words = {"and", "or", "the", "in", "at", "for", "to", "by", "with", "a", "an", "of", "on", "vs"}
    hyphenated_words = {"non", "mid", "bi"}
    
    if text is None:
        return None

    # Split the text into words by spaces or hyphens
    words = re.split(r"[-\s]", text)
    formatted_words = []
    i = 0

    while i < len(words):
        word = words[i].lower()
        
        # Handle 'LA' specifically
        if word == "la":
            formatted_words.append("LA")
        # Handle exception words with hyphenation
        elif word in hyphenated_words and i < len(words) - 1:
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

# Example usage (commented out):
if __name__ == "__main__":
    # Test make_player_key
    print(make_player_key("LeBron James Jr."))
    print(make_player_key("José Álvarez III"))
    
    # Test format_text
    print(make_title_case("sign and trade deal"))
    print(make_title_case("LA Lakers vs non-stop"))
    print(make_title_case("Non taxpayer bi annual Mid Level Exception"))
