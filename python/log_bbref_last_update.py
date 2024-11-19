import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# URL of the Basketball Reference site for scraping
url = "https://www.basketball-reference.com"

# Send a GET request to the site to fetch the page content
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
response = requests.get(url, headers=headers)

# Check if the request was successful (status code 200); exit if not
if response.status_code != 200:
    print(f"Failed to fetch data: {response.status_code}")
    exit()

# Parse the HTML content using BeautifulSoup to extract the 'Last Updated' info
soup = BeautifulSoup(response.content, "html.parser")

# Find the site's 'Last Updated' date in the HTML DOM
social_section = soup.find("div", id="social")
if social_section:
    paragraphs = social_section.find_all("p")
    if len(paragraphs) > 1:
        # Extract 'Site Last Updated' from the second paragraph in the 'social' section
        site_updated = paragraphs[1].text.strip()
    else:
        print("No second paragraph found in #social.")
        exit()
else:
    print("Could not find #social section.")
    exit()

# Remove the label 'Site Last Updated:' and strip extra spaces
site_updated_text = site_updated.replace("Site Last Updated:", "").strip()

# Get the current timestamp when the script is executed
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Define the directory and file path for saving the log
log_dir = "python/data"
log_file = os.path.join(log_dir, "bbref_update_log.csv")

# Create the log directory if it doesn't exist
os.makedirs(log_dir, exist_ok=True)

# Create the log file with a header if it doesn't exist
log_entry = [site_updated_text, current_time]
header = ["Site Last Updated", "Checked At"]

# Check if the log file exists and create it with headers if not
if not os.path.exists(log_file):
    with open(log_file, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)

# Append the site's last updated date and the check time to the CSV log file
with open(log_file, "a", newline="") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(log_entry)

# Print the last updated date, current time, and log file path for confirmation
print(f"Site last updated: {site_updated_text}")
print(f"Checked at: {current_time}")
print(f"Log saved to {log_file}")
