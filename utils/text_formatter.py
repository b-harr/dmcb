import unicodedata
import re


PLAYER_KEY_OVERRIDES = {
    "cam-thomas": "cameron-thomas",
    "oliviermaxence-prosper": "olivier-maxence-prosper",
    "herbert-jones": "herb-jones",
    "tristan-dasilva": "tristan-da-silva",
    #"yang-hansen": "hansen-yang",
}
CAPITALIZED_WORDS = {
    "la", "rfa", "ufa", "mle",
}
MINOR_WORDS = {
    "a", "an", "the", "and", "or",
    "in", "on", "of", "for", "to",
    "by", "with", "at", "vs",
}
HYPHENATED_WORDS = {
    "non", "mid", "bi", "re",
}


def make_player_key(name: str) -> str:
    # Remove accents and convert to lowercase
    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    name = name.lower().strip()

    # Normalize spaces and special characters
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^\w-]", "", name)

    # Remove common suffixes
    key = re.sub(r"-(sr|jr|ii|iii|iv|v|vi|vii)$", "", name)

    # Apply overrides if the cleaned name matches any known exceptions
    if key in PLAYER_KEY_OVERRIDES:
        return PLAYER_KEY_OVERRIDES[key]

    return key

def make_title_case(text: str) -> str:
    # Split the text into words by spaces or hyphens
    words = re.split(r"[-\s]", text)
    formatted_words = []
    i = 0

    # Iterate through each word and apply title case rules
    while i < len(words):
        word = words[i].lower()

        # Handle common abbreviations
        if word in CAPITALIZED_WORDS:
            formatted_words.append(word.upper())

        # Handle exception words with hyphenation
        elif word in HYPHENATED_WORDS and i < len(words) - 1:
            formatted_words.append(f"{word.capitalize()}-{words[i + 1].capitalize()}")
            # Skip the next word as it's already processed
            i += 1

        # Handle minor words
        elif word in MINOR_WORDS:
            formatted_words.append(word if i != 0 and i != len(words) - 1 else word.capitalize())

        # Capitalize alphabetic words; retain numbers
        else:
            formatted_words.append(word.capitalize() if word.isalpha() else word)

        # Move to the next word
        i += 1

    # Join the formatted words with spaces
    title_text = " ".join(formatted_words)
    # Special case: Replace "Sign and Trade" with "Sign-and-Trade"
    title_text = re.sub("Sign and Trade", "Sign-and-Trade", title_text)

    return title_text
