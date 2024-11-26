import os
import sys

# Dynamically add the project root to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.data_fetcher import fetch_data

year = 2025
url = f"https://www.sports.ws/nba"
content = fetch_data(url)
print(content)
