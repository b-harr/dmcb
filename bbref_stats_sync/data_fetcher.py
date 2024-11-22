import requests
from bs4 import BeautifulSoup
from time import sleep
import random
import logging
import pandas as pd

logger = logging.getLogger()

def fetch_data_with_retry(url, headers, retries=3, delay=2):
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
