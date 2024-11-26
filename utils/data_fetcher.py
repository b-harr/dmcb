import requests
from bs4 import BeautifulSoup

def fetch_data(url):
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        return soup
    except Exception as e:
        return None
